# RUNBOOK

このドキュメントは、データパイプライン障害時の初動・復旧・再開を標準化する運用手順書です。

## 1. 目的と適用範囲

- 目的:
  - 障害発生時に、最短で安全に復旧する
  - 復旧判断を担当者依存にしない
  - Chaos Test で想定した破壊シナリオから再現可能に復帰する
- 適用範囲:
  - CI/CD: `.github/workflows/ci.yml`
  - Terraform: `terraform/`
  - Loader: `src/infrastructure/snowflake_loader.py`
  - dbt: `src/scripts/deploy/run_dbt.py`, `src/scripts/deploy/verify_dbt_view_rebuild.py`

運用原則:

- Terraform の prod 適用は CI 承認フローのみ許可 (ローカルでの prod 実行は禁止)
- 本番復旧は「原因切り分け -> dev で再現/検証 -> prod 再開」の順で実施
- 記録は PR または Issue に残し、`CONTRIBUTING.md` 5.3 の Chaos 報告要件を満たす

## 2. 障害初動フロー (T+0 ~ T+15 分)

1. 検知
   - GitHub Actions の失敗ジョブ名を確認 (`terraform-prod-apply`, `prod-loader-run`, `prod-dbt-run`, `prod-dbt-test`)
2. 影響判定
   - どのレイヤーで停止したかを分類 (Infra / Ingestion / Transformation / Test)
3. 封じ込め
   - 進行中ランをキャンセルして追加変更の波及を止める
4. 記録
   - Run ID、失敗ジョブ、エラー要約、影響範囲を Issue/PR に記録
5. 復旧方針決定
   - 本 RUNBOOK のシナリオ別手順に沿って実施

主要コマンド:

```bash
# 直近の CI ラン一覧
gh run list --workflow "CI Pipeline" --limit 10

# ラン詳細 (失敗ジョブとログ確認)
gh run view <RUN_ID> --log-failed

# 進行中ランの停止
gh run cancel <RUN_ID>

# artifact をローカル取得
gh run download <RUN_ID> -D artifacts_run_<RUN_ID>
```

## 3. 停止・再開チェックリスト

## 3.1 停止チェックリスト

1. 進行中の `main` ランを停止した
2. 失敗点が Terraform / Loader / dbt のどこかを特定した
3. 参照ログを取得した
   - `artifacts/terraform/prod-plan.log`
   - `artifacts/terraform/prod-apply.log`
   - `artifacts/data-pipeline/prod-loader.log`
   - `artifacts/data-pipeline/prod-dbt-run.log`
   - `artifacts/data-pipeline/prod-dbt-test.log`
4. 影響範囲 (未反映/部分反映/データ欠落の有無) を記録した

## 3.2 再開チェックリスト

1. dev で再現し、修正が妥当であることを確認した
2. PR CI が緑であることを確認した
3. `main` マージ後、`prod-approval-gate` 承認から自動継続することを確認した
4. 失敗ランの再実行が必要な場合は `rerun` した

```bash
# 失敗ジョブのみ再実行
gh run rerun <RUN_ID> --failed

# ラン全体を再実行
gh run rerun <RUN_ID>
```

## 4. シナリオ別復旧手順

## 4.1 シナリオA: terraform-prod-apply 失敗

典型症状:

- `terraform-prod-apply` が失敗
- `prod-apply.log` に認証/権限/状態競合 (`state lock`) が出る

復旧手順:

- 失敗ログを取得

```bash
gh run view <RUN_ID> --job terraform-prod-apply --log
```

- dev で同等操作を再現

```bash
TF_VAR_app_env=dev terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
TF_VAR_app_env=dev terraform -chdir=terraform plan -no-color
TF_VAR_app_env=dev terraform -chdir=terraform apply -auto-approve
```

- HCP Terraform のワークスペース状態を確認し、必要ならロック解除を実施
- 修正を PR に反映し、`terraform-prod-plan` が成功することを確認
- `main` へマージし、承認後に `terraform-prod-apply` を再実行

## 4.2 シナリオB: prod-loader-run 失敗

典型症状:

- `prod-loader-run` が失敗
- 鍵/環境変数不足、CSV 欠損、COPY 失敗で停止

復旧手順:

- 失敗ログを確認

```bash
gh run view <RUN_ID> --job prod-loader-run --log
```

- dev でローダー単体再現

```bash
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
```

- 必要なら入力再生成

```bash
uv run python src/scripts/data_gen/generate_large_data.py --number 100000 --geo-mode lite
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
```

- 修正 PR を通し、`main` マージ後にランを再開 (`gh run rerun`)

## 4.3 シナリオC: prod-dbt-run / prod-dbt-test 失敗

典型症状:

- `prod-dbt-run` または `prod-dbt-test` が失敗
- スキーマ不整合、モデル依存破綻、テスト失敗

復旧手順:

- 失敗ログと `run_results.json` を確認

```bash
gh run view <RUN_ID> --job prod-dbt-run --log
gh run view <RUN_ID> --job prod-dbt-test --log
gh run download <RUN_ID> -D artifacts_run_<RUN_ID>
```

- dev で対象モデルを限定して再現

```bash
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py debug
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run --select +fct_delivery_analysis
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test --select +fct_delivery_analysis
```

- 必要なら view 再構築検証を実行

```bash
APP_ENV=dev uv run python src/scripts/deploy/verify_dbt_view_rebuild.py
```

- 修正 PR を通し、`main` で `prod-dbt-run` -> `prod-dbt-test` の通過を確認

## 4.4 シナリオD: Chaos 想定の破壊 (View 消失 / 参照不能)

想定:

- 手動操作や誤変更で Silver/Gold の view が欠落

復旧手順:

- dev で rebuild 検証を実行

```bash
APP_ENV=dev uv run python src/scripts/deploy/verify_dbt_view_rebuild.py
```

- 必要なら対象モデルを再実行

```bash
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run --select +fct_delivery_analysis
```

- 手順を PR/Issue に記録し、`CONTRIBUTING.md` 5.3 の観測結果として残す

## 5. Backfill 戦略

Backfill は影響範囲に応じて 3 段階で実施する。

## 5.1 レベル1: dbt 再計算のみ

対象:

- Bronze は正常で、変換のみ再計算したい場合

```bash
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run --select +fct_delivery_analysis
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test --select +fct_delivery_analysis
```

## 5.2 レベル2: Loader 再投入 + dbt 再計算

対象:

- 入力欠損や COPY 失敗で Bronze の再投入が必要な場合

```bash
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test
```

## 5.3 レベル3: データ再生成を伴う Backfill

対象:

- 入力 CSV 自体に欠陥があり、再生成が必要な場合

```bash
uv run python src/scripts/data_gen/generate_large_data.py --number 100000 --geo-mode lite
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test
```

運用注意:

- Backfill 実行日時、対象範囲、件数差分を PR/Issue に記録する
- 本番反映は `main` マージ後の CI で行い、ローカル prod 実行はしない

## 6. 正常性確認チェックリスト

1. CI ジョブが以下の順で成功している
   - `terraform-prod-apply`
   - `prod-loader-run`
   - `prod-dbt-run`
   - `prod-dbt-test`
2. 失敗時 artifact と比較して、再実行後に同一エラーが再発していない
3. `run_results.json` に失敗モデル/失敗テストが残っていない
4. 影響範囲と復旧時刻 (MTTR) を記録した
5. 再発防止策 (監視、テスト、権限、手順改善) を 1 つ以上登録した

## 7. エスカレーション

- 以下の場合は単独で継続せず、レビュアーまたは運用責任者へ即時エスカレーション:
  - Terraform state 競合が継続し解除できない
  - 同一障害が 2 回以上連続で再発
  - 影響範囲が Gold 出力を超えて外部利用に波及

連携先ドキュメント:

- `docs/TESTING.md`
- `docs/ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `docs/DEPLOYMENT.md`
