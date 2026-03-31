# TESTING

このドキュメントは、本プロジェクトのデータ品質保証戦略と障害注入テスト (Chaos Engineering) の実施方針を定義します。

## 1. 目的と適用範囲

- データ品質をレイヤーごとに定量評価し、不正確なデータの流出を防ぐ
- 異常系で Fail Fast と検知経路が機能することを検証する
- 開発者が同じ基準でテストを追加・運用できる状態を作る

適用範囲:

- Python ローダー (`src/infrastructure/snowflake_loader.py`)
- dbt 変換 (`src/transform`)
- Terraform 構成 (`terraform/`)
- CI/CD 実行フロー (`.github/workflows/ci.yml`)

## 2. データ版テストピラミッド

| レベル | 主対象 | 目的 | 代表手法 | 実行タイミング |
| --- | --- | --- | --- | --- |
| Unit Test | Python, SQL ロジック | ロジック破綻の早期検知 | `pytest`, dbt model/test | ローカル / PR |
| Integration Test | Loader -> Snowflake, 権限連携 | コンポーネント結合の保証 | ローダー実行検証、dbt debug/rebuild | PR / main |
| Data Quality Test | Freshness, Volume, 分布 | データの信頼性保証 | dbt test, 件数監視, 異常分布検知 | main (本番系) |
| Chaos Test | 異常注入シナリオ | 検知・停止・復旧能力の検証 | 障害注入シナリオ実行 | 手動実行 |

## 3. レイヤー別品質保証戦略

## 3.1 Ingestion (Loader/Bronze)

主な観点:

- スキーマ整合: 必須カラムがロードされること
- 件数整合: 入力件数とロード件数の差分が許容範囲であること
- 失敗時停止: ローダー失敗で後続処理を継続しないこと

実施手段:

- `tests/test_snowflake_loader.py`
- CI の `prod-loader-run` ログ確認

## 3.2 Transformation (Silver/Gold)

主な観点:

- `not null`, `unique`, `accepted_values` などの契約検証
- 型変換と正規化ルールの破綻検知
- マート出力の参照整合

実施手段:

- `src/scripts/deploy/run_dbt.py test`
- `src/transform/target/run_results.json` の確認

## 3.3 Infrastructure / Security

主な観点:

- IaC の妥当性 (`fmt`, `validate`, `tflint`)
- 権限変更の影響範囲
- 本番適用前の plan 監査

実施手段:

- CI `terraform-prod-plan`
- CI `terraform-prod-apply` (approval gate 通過後)

## 4. データ品質指標 (DQI)

| 指標 | 目的 | 例示的なしきい値 | 失敗時アクション |
| --- | --- | --- | --- |
| Freshness | 遅延検知 | 更新間隔が想定 SLA 以内 | パイプライン停止、要因調査 |
| Volume | 異常件数検知 | 前日比/移動平均の逸脱を検知 | 取り込み元・抽出条件を確認 |
| Completeness | 欠損検知 | 必須カラム欠損率が閾値超過しない | 品質ゲートで fail |
| Uniqueness | 重複検知 | 主キー重複 0 件 | 重複データの隔離・修正 |
| Distribution | 分布逸脱検知 | 主要列分布が許容差内 | 異常データ混入調査 |

注記:

- しきい値は運用で調整し、変更時は PR で根拠を記録する
- 変更が設計判断に影響する場合は ADR 更新を検討する

## 5. Chaos Engineering 戦略

## 5.1 目的

- 未知の不整合 (スキーマ変更、異常値、権限欠落) への耐性を確認する
- 異常検知から通知・復旧までの時間と品質を測定する

## 5.2 シナリオ管理

- シナリオは `tests/chaos/` 配下で管理する方針とする
- シナリオは以下を必須項目とする:
  - 目的
  - 注入方法
  - 期待される検知/停止条件
  - 復旧手順
  - 実施結果

## 5.3 推奨シナリオ (初期セット)

1. スキーマドリフト注入
   - 入力 CSV に予期しない列追加/列欠落を発生させる
2. 異常値注入
   - 数値列に範囲外値や文字列を混入させる
3. 権限不足注入
   - ローダーまたは dbt 実行ロールの権限を限定して失敗を再現する
4. 入力欠損/空ファイル
   - ファイル未配置、0 byte ファイル、ヘッダ不整合を注入する

## 5.4 合否基準

- 期待したジョブで Fail Fast する
- 失敗理由がログから追跡できる
- 復旧手順で処理を正常復帰できる
- 影響範囲が Gold 出力まで波及しないことを確認できる

## 6. CI/CD 実行タイミング

## 6.1 Pull Request 時

- lint (python/yaml/shell/markdown/docker/toml/terraform)
- test (`pytest tests/`)
- dbt debug (dev/prod)
- dbt rebuild verify (dev)
- terraform prod plan

目的:

- 本番適用前に構文・静的品質・接続性・plan 差分を検証する

## 6.2 main マージ後

- prod approval gate
- terraform prod apply
- prod loader run
- prod dbt run
- prod dbt test

目的:

- 承認付きの本番経路で、インフラからデータ品質検証まで一貫実行する

## 6.3 手動実行が必要なテスト

- 大規模データを使う分布検証
- Chaos シナリオ一式
- 復旧時間 (MTTR) 計測を含む訓練

## 7. Observability とインシデント接続

主要観測点:

- GitHub Actions 実行ログ
- artifact:
  - terraform plan/apply ログ
  - loader ログ
  - dbt run/test ログ
  - `run_results.json`

運用ルール:

- テスト失敗時は Issue/PR に失敗ジョブとログ場所を記録する
- Chaos 実施時は `CONTRIBUTING.md` の 5.3 要件 (目的/注入方法/結果/フォローアップ) を満たす
- 初動・復旧手順は `docs/RUNBOOK.md` を参照する

## 8. 新規テスト追加の実装基準

追加前チェック:

- 何を壊したときに何を守るテストかを 1 文で説明できる
- 失敗時の期待挙動 (停止・通知・復旧) を定義している
- 実行コストと頻度 (PR/main/手動) を定義している

追加時の必須項目:

1. テスト対象と目的
2. 実行手順
3. 合否基準
4. 失敗時の調査導線 (ログ/artifact)
5. 必要ならドキュメント更新 (`TESTING.md`, `CONTRIBUTING.md`, ADR)

## 9. ガバナンス整合方針

- 現時点では `CONTRIBUTING.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `docs/DECISIONS.md`, `docs/DATA_CONTRACT.md`, `docs/GOVERNANCE.md` と整合させる
- 権限モデルや managed access を変更した場合は、本ドキュメントの品質ゲート/障害注入ルールも必要に応じて更新する
