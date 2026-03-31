# CONTRIBUTING

このドキュメントは、本プロジェクトで変更を安全かつ再現可能に進めるための標準ガイドです。
特に Terraform とデータパイプライン変更時の作法を統一し、レビューコストを下げることを目的とします。

## 1. 基本方針

- 開発フローは GitHub Flow を採用します。
- すべての変更は PR 経由で `main` に統合します。
- ローカル実行は `dev` 固定、`prod` 実行は CI 経由のみです。
- 認証は環境変数 + RSA 鍵を利用し、パスワード認証は利用しません。

## 2. ローカル開発環境セットアップ

## 2.1 必須ツールと推奨バージョン

- Docker / Docker Compose（コンテナ開発の標準実行環境）
- Git
- Python 3.11 以上（`pyproject.toml` の `requires-python` 準拠）
- uv（依存解決・実行）
- Terraform 1.6 以上（`terraform/providers.tf` の `required_version` 準拠）
- tflint 0.54 以上（CI/開発コンテナの利用バージョン準拠）
- Snowflake CLI 3.x 以上（初期セットアップや手動確認時に利用）

補足: 日常開発は Docker 実行を前提にしており、ホストに全ツールを直接導入しなくても進められます。

## 2.2 初期セットアップ

1. 環境変数ファイルを作成

    ```bash
    cp .env.example .env
    ```

2. `.env` に最低限の接続情報を設定

    - `SNOWFLAKE_ACCOUNT`
    - `DEV_LOADER_USER_RSA_PRIVATE_KEY`
    - `DEV_DBT_USER_RSA_PRIVATE_KEY`
    - `DEV_STREAMLIT_USER_RSA_PRIVATE_KEY`

3. 開発環境起動

    ```bash
    docker compose up --build
    ```

4. HCP Terraform / GitHub Actions の本番向け設定

    - 詳細手順は `terraform/README.md` を正本として参照してください。
    - 本ドキュメントでは重複記載せず、要点のみ扱います。

参照先:

- `terraform/README.md` セクション 0（Snowflake 認証基盤と初期セットアップ）
- `terraform/README.md` セクション 1（GitHub Environment 保護設定）

## 2.3 標準ローカル検証コマンド

変更前後で最低限以下を実行してください。

```bash
# 全チェック（ローカル直列）
/app/.venv/bin/python src/scripts/quality/check_code_quality.py

# 必要に応じた個別チェック
/app/.venv/bin/python src/scripts/quality/check_code_quality.py --only python
/app/.venv/bin/python src/scripts/quality/check_code_quality.py --only yaml
/app/.venv/bin/python src/scripts/quality/check_code_quality.py --only terraform
```

## 3. ブランチ戦略と PR の作法

## 3.1 GitHub Flow

1. `main` から作業ブランチを作成
2. 作業ブランチで実装・検証
3. PR を作成してレビュー
4. 承認後に `main` へマージ

推奨ブランチ名:

- `feat/<issue>-<summary>`
- `fix/<issue>-<summary>`
- `refactor/<issue>-<summary>`
- `docs/<issue>-<summary>`

## 3.2 コミット / PR タイトル規約

Conventional Commits を使用します。

- コミットメッセージは Conventional Commits の `type:` を先頭に置き、説明文は日本語で記述します。

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `refactor:` リファクタリング
- `test:` テスト
- `build:` ビルド関連
- `ci:` CI/CD
- `chore:` その他

## 3.3 PR に必須の記載

- 概要
- 影響範囲
- テスト結果（実行コマンドと結果）
- 必要に応じてスクリーンショット / ログ / artifact

PR 作成時は `.github/PULL_REQUEST_TEMPLATE.md` を使用してください。

## 4. Terraform 開発ルール

## 4.1 変更前提

- `terraform/tf` ラッパー経由の実行を基本とします。
- 本番適用は CI + `environment: prod` 承認ゲートを必須とします。

## 4.2 ローカル必須チェック

Terraform 関連変更では、最低限以下を通してください。

```bash
terraform -chdir=terraform fmt -check
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
tflint --chdir=terraform
```

## 4.3 モジュール化とディレクトリ基準

- 再利用される単位（環境共通のリソース集合）は `terraform/modules/` に切り出す
- ルートの `terraform/main.tf` にはオーケストレーションのみを置く
- モジュール内は `main.tf`, `variables.tf`, `outputs.tf`, `versions.tf` を基本構成とする

## 4.4 命名規則

- Terraform のローカル変数・変数名は `snake_case`
- リソース名は役割が判別できる短い接頭辞 + 用途名
- 環境差分は命名に埋め込むより、入力変数（`app_env` など）で制御する

## 5. データエンジニアリング規約

## 5.1 スキーマ変更時の更新フロー

スキーマやテーブル契約を変更した場合は、同一 PR で `DATA_CONTRACT.md` を更新します。
`DATA_CONTRACT.md` が未作成の場合は新規作成してください。

最低限記載する内容:

- 変更対象（テーブル/カラム）
- 互換性（後方互換の有無）
- リリース手順とロールバック方針

## 5.2 破壊的変更（DROP を伴う変更）の手順

- `DROP` / `REPLACE` / `lifecycle` 調整を伴う変更は PR で明示する
- なぜ破壊的変更が必要か、代替案比較を記載する
- 影響範囲と復旧手順（バックアップ/再作成手順）を記載する
- `prevent_destroy` 解除が必要な場合は「解除条件」と「再有効化タイミング」を PR に明記する

## 5.3 Chaos Test 実施時の報告

障害注入テストを行う場合、PR もしくは Issue に以下を必ず記録します。

- テスト目的（何を検証するか）
- 注入方法（どの障害をどう再現したか）
- 観測結果（検知・復旧・影響範囲）
- フォローアップ（恒久対策の要否）

## 5.4 設計判断 (ADR) の更新ルール

重要設計の変更を伴う場合、同一 PR で ADR を追加または更新してください。

ADR 対象の例:

- Terraform / Snowflake の権限モデル変更
- 本番実行経路・承認フロー変更
- 破壊的変更ポリシー（`prevent_destroy` など）の変更
- 環境切替や命名規則など、長期運用へ影響する規約変更

運用手順:

1. `docs/DECISIONS.md` の ADR 一覧を更新する
2. `docs/adr/ADR-XXXX-*.md` を追加または更新する
3. 既存判断を変更する場合は新規 ADR を作成し、旧 ADR を `Superseded` とする
4. PR 本文の影響範囲に、対象 ADR を明記する

## 6. CI/CD との整合

- CI は lint と test を並列実行します。
- Terraform 本番系は `main` push でのみ実行されます。
- `prod` への適用は承認ゲート通過後に継続されます。
- 実運用フローの詳細は `docs/DEPLOYMENT.md` と `terraform/README.md` を参照してください。

## 7. 相談とエスカレーション

以下に該当する場合は、単独判断でマージせずにレビュアーへ相談してください。

- 本番影響が読みにくい Terraform 変更
- dbt モデルの破壊的変更
- 認証方式や秘密情報管理に関わる変更
