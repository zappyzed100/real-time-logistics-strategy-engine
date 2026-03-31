# DEPLOYMENT

このドキュメントは、DEV/PROD 環境への変更適用を再現可能にするための標準手順です。
Terraform（HCP Terraform）によるインフラ反映から、Loader/dbt によるデータ反映までを一貫して扱います。

## 1. 目的と適用範囲

- 目的:
  - 環境差分や依存関係漏れによるデプロイ失敗を防ぐ
  - 実行順序（Plan -> Apply -> Loader -> dbt run/test）を標準化する
  - 失敗時の切り分け・復旧導線を明確化する
- 適用範囲:
  - Terraform: `terraform/`, `terraform/tf`
  - CI/CD: `.github/workflows/ci.yml`
  - Data Pipeline: `src/infrastructure/snowflake_loader.py`, `src/scripts/deploy/run_dbt.py`

運用原則:

- ローカル実行は `APP_ENV=dev` 固定
- `APP_ENV=prod` は CI 実行でのみ許可
- 本番反映は `main` へのマージと `environment: prod` 承認を必須とする

## 2. 環境構成（Environment Strategy）

## 2.1 Workspace と役割

- DEV Workspace: `HCP_TF_WORKSPACE_DEV`
- PROD Workspace: `HCP_TF_WORKSPACE_PROD`
- 共通 Organization: `HCP_TF_ORGANIZATION`

`terraform/tf` は `APP_ENV` で行き先 Workspace を切り替えます。

- `APP_ENV=dev` -> DEV Workspace
- `APP_ENV=prod` -> PROD Workspace（CI のみ）

## 2.2 変数管理の責務

- `.env.shared`: 非機密の共通設定（Workspace 名、固定値）
- `.env`: 機密情報やローカル上書き
- HCP Terraform Variables: 実行時に必要な機密値（秘密鍵など）
- GitHub Secrets: CI から Terraform/Snowflake を呼ぶための機密情報

## 2.3 実行時に確認する最小項目

1. `APP_ENV` が意図した値か（dev/prod）
2. `HCP_TF_ORGANIZATION` / `HCP_TF_WORKSPACE_*` が設定済みか
3. Team API Token（`TF_TOKEN_app_terraform_io` または互換キー）が有効か

## 3. 標準デプロイフロー（CI/CD）

PR から本番反映までの標準フロー:

1. 開発ブランチで実装・ローカル検証
2. PR 作成
3. CI で `terraform-prod-plan` を確認
4. `main` へマージ
5. `prod-approval-gate` を承認
6. 自動継続:
   - `terraform-prod-apply`
   - `prod-loader-run`
   - `prod-dbt-run`
   - `prod-dbt-test`

### 3.1 トリガー条件（抜粋）

- `terraform-prod-plan`: `pull_request`, `push(main)`, `workflow_dispatch`
- `prod-approval-gate`: `push(main)` のみ
- `terraform-prod-apply` 以降: 承認後に順次実行

### 3.2 成果物（artifact）

- `artifacts/terraform/prod-plan.log`
- `artifacts/terraform/prod-apply.log`
- `artifacts/data-pipeline/prod-loader.log`
- `artifacts/data-pipeline/prod-dbt-run.log`
- `artifacts/data-pipeline/prod-dbt-test.log`
- `src/transform/target/run_results.json`（dbt run/test）

## 4. 手動デプロイ・初期構築手順

## 4.1 初期構築（Bootstrap）

初回のみ、Snowflake 側の基盤準備が必要です。詳細は `terraform/README.md` を正本とします。

実行の流れ:

1. RSA キーペアを生成（DEV/PROD 別）
2. Snowflake ワークシートで Bootstrap SQL を 1 回実行
   - `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
   - `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
3. HCP Terraform Workspace Variables を登録
4. GitHub Secrets を登録

## 4.2 DEV 手動反映（検証用）

```bash
# Terraform
APP_ENV=dev ./terraform/tf plan -no-color
APP_ENV=dev ./terraform/tf apply -auto-approve

# Data load + dbt
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test
```

## 4.3 PROD 手動実行について

- ローカルから `APP_ENV=prod` 実行はブロックされます
- PROD 反映は CI の承認フロー経由のみ許可されます

## 5. コンポーネント間の依存関係

## 5.1 依存関係の基本順序

1. RBAC/Role/User（実行主体）
2. Database/Schema/Warehouse
3. Storage integration / stage / file format
4. Table/View 定義
5. Loader（Bronze への投入）
6. dbt run/test（Silver/Gold 更新と検証）

## 5.2 Terraform 外操作が必要なケース

`snowflake_storage_integration` のように外部クラウド設定との信頼関係が必要な場合、
Terraform 側の作成後に、外部サービス（例: S3 側ポリシー）の反映を実施してください。

運用ルール:

- PR 本文に「Terraform 外の手動作業」を明記する
- 反映確認ログ（画面またはコマンド結果）を記録する

## 6. トラブルシューティング

## 6.1 ログ確認の優先順

1. GitHub Actions の失敗ジョブログ
2. artifact の plan/apply/loader/dbt ログ
3. `run_results.json`（dbt 失敗ノード）

確認コマンド:

```bash
gh run list --workflow "CI Pipeline" --limit 10
gh run view <RUN_ID> --log-failed
gh run download <RUN_ID> -D artifacts_run_<RUN_ID>
```

## 6.2 よくある失敗パターン

- `terraform-prod-plan` 失敗:
  - HCP Token / Organization / Workspace 設定不備
- `terraform-prod-apply` 失敗:
  - state lock 競合、権限不足、手動差分による drift
- `prod-loader-run` 失敗:
  - 鍵・環境変数不備、CSV 入力不備
- `prod-dbt-run/test` 失敗:
  - モデル依存破綻、スキーマ不整合、品質テスト失敗

## 7. ロールバック戦略

## 7.1 インフラ変更のロールバック

1. 失敗コミットを `main` で revert
2. PR 作成後に `terraform-prod-plan` 差分を確認
3. 承認後 `terraform-prod-apply` で復元

注記:

- Terraform state を直接編集する運用は原則禁止
- state 不整合時は原因を切り分け、必要な修正をコードへ反映して再適用

## 7.2 データ変更のロールバック/復旧

データ系は「バックアップから復元」より「再投入 + 再計算」を基本とします。

```bash
APP_ENV=dev uv run python src/infrastructure/snowflake_loader.py
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py run
APP_ENV=dev uv run python src/scripts/deploy/run_dbt.py test
```

詳細な障害対応は `docs/RUNBOOK.md` を参照してください。

## 8. 完了確認チェックリスト

1. Plan/Apply/Loader/dbt run/test がすべて成功
2. 失敗時 artifact が取得・参照できる
3. 依存する手動作業が PR に記録されている
4. 変更内容に応じて `docs/TESTING.md` / `docs/RUNBOOK.md` / ADR が更新されている

## 9. 関連ドキュメント

- `CONTRIBUTING.md`（開発規約・PR 作法）
- `docs/RUNBOOK.md`（障害対応と復旧手順）
- `docs/TESTING.md`（品質保証と Chaos 方針）
- `docs/ARCHITECTURE.md`（構成とデータフロー）
- `terraform/README.md`（Terraform と Bootstrap の正本）
