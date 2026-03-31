# Terraform 運用ガイド

本プロジェクトでは HCP Terraform (Remote Backend) を利用します。

## Provider 更新ポリシー

Snowflake provider は preview feature（`snowflake_table_resource` など）に依存しているため、
本番運用では **バージョン固定** と **段階的アップグレード検証** を必須とします。

- `terraform/providers.tf` の `snowflakedb/snowflake` は `= 2.13.0` で固定する
- 更新は「必要時のみ」実施し、通常運用での自動追従は行わない
- 更新時は次の順で検証する

```bash
# 1) providers.tf の version を更新
# 2) lock 更新（backend 接続なし）
terraform -chdir=terraform init -backend=false -upgrade

# 3) 構文/型の破壊的変更確認
terraform -chdir=terraform validate -no-color

# 4) DEV / PROD の plan を確認（CI 経由推奨）
TF_VAR_app_env=dev terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
TF_VAR_app_env=dev terraform -chdir=terraform plan -no-color
```

変更は PR でレビューし、`prod` は approval gate 後に apply します。

CI での定期検証:

- GitHub Actions `CI Pipeline` の `workflow_dispatch` で `run_provider_upgrade_check=true` を指定すると、
    `init -backend=false -upgrade` + `validate` を実行する検証ジョブが起動します。

## 0. Snowflake 認証基盤と初期セットアップ

### 0.1. セキュリティ設計：キーペア認証と権限分離

本プロジェクトでは、実務におけるセキュリティ・ベストプラクティスに基づき、パスワード認証を廃止し、**RSA キーペア（JWT）認証**を採用しています。また、**「初期構築（Bootstrap）」と「継続的運用（IaC）」** の境界を明確に分離しています。

- **環境分離**: DEV と PROD で実行ロール（Role）と接続ユーザー（User）を物理的に分離し、爆発半径（Blast Radius）を最小化
- **最小権限の原則（PoLP）**: HCP Terraform には `ACCOUNTADMIN` を使わせず、リソース管理に必要な権限（`CREATE DATABASE`, `MANAGE GRANTS` 等）のみを付与した専用ロールを使用

### 0.2. 初期セットアップ（Bootstrap）

HCP Terraform が Snowflake を操作するための「ドア」を作成する工程です。  
この作業は、Snowflake の管理者権限（`ACCOUNTADMIN`）を持つユーザーが**ワークシートで一度だけ**実行します。

#### ステップ 1：RSA キーペアの生成

ローカル環境で実行し、**環境ごとに別々の鍵ペア**を作成します。

```bash
# DEV 用
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_tf_key_dev.p8 -nocrypt
openssl rsa -in snowflake_tf_key_dev.p8 -pubout -out snowflake_tf_key_dev.pub

# PROD 用
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out snowflake_tf_key_prod.p8 -nocrypt
openssl rsa -in snowflake_tf_key_prod.p8 -pubout -out snowflake_tf_key_prod.pub
```

> 生成した `.p8` ファイルは鍵管理システム等で安全に保管し、リポジトリへはコミットしないでください。

#### ステップ 2：Snowflake での管理用リソース作成（SQL）

DEV・PROD それぞれの Snowflake ワークシートで、対応する SQL を `ACCOUNTADMIN` ロールで実行します。

このステップで扱う重要資産は **Role / User / Database / Schema** です。
（Warehouse はこのステップでは手動作成しません。Terraform/HCP 側で作成します。）

各 Schema は managed access を前提に作成します。
既存環境へ後追い適用する場合も、同梱の SQL に含まれる `ALTER SCHEMA ... ENABLE MANAGED ACCESS;` を実行してください。

実行する SQL は以下に分離して管理しています。

- DEV: `bootstrap/sql/setup_snowflake_tf_dev.sql`
- PROD: `bootstrap/sql/setup_snowflake_tf_prod.sql`

補足:

- 実行前に `./terraform/bootstrap/sync_bootstrap_sql_from_tfvars.sh` を実行し、`EXPECTED_ACCOUNT` / retention / CIDR を Terraform 正本値へ同期してください。
- SQL 冒頭の preflight ブロック内にある `runner_rsa_keys` 1行だけを実値へ置き換えてから実行してください（通常: `<PUBKEY1>`、ローテーション時: `<PUBKEY1>||<PUBKEY2>`）。
- Bootstrap SQL は「初回セットアップ用」です。日次運用で繰り返し実行するものではありません。

#### ステップ 3：Bootstrap 作成オブジェクトを Terraform state へ import

Bootstrap SQL で作成したオブジェクトは、初回のみ Terraform state へ取り込みます。

対象リソース:

- Database: Bronze / Silver / Gold
- Schema: RAW_DATA / CLEANSED / MARKETING_MART
- Network policy: `<ENV>_TERRAFORM_NETWORK_POLICY`

import ID 形式:

- `snowflake_database`: `<DATABASE_NAME>`
- `snowflake_schema`: `<DATABASE_NAME>.<SCHEMA_NAME>`
- `snowflake_network_policy`: `<NETWORK_POLICY_NAME>`

実行例（DEV）:

```bash
TF_VAR_app_env=dev terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_database.bronze_db' DEV_BRONZE_DB
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_database.silver_db' DEV_SILVER_DB
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_database.gold_db' DEV_GOLD_DB
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_schema.bronze_schema' DEV_BRONZE_DB.RAW_DATA
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_schema.silver_schema' DEV_SILVER_DB.CLEANSED
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_schema.gold_schema' DEV_GOLD_DB.MARKETING_MART
TF_VAR_app_env=dev terraform -chdir=terraform import 'module.snowflake_env.snowflake_network_policy.terraform_access_policy' DEV_TERRAFORM_NETWORK_POLICY
```

注意:

- Remote backend で sensitive 変数を使う構成では、`import {}` ブロック + remote apply の方が安定する場合があります。
- import 完了後は `terraform plan` で差分ゼロを確認してください。

補足:

- 通常運用では、Warehouse は手動作成せず Terraform/HCP 側で作成します。
- 例外として、過去運用で同名 Warehouse が既に存在する場合のみ、`GRANT OWNERSHIP ON WAREHOUSE ... TO ROLE <ENV>_TF_ADMIN_ROLE COPY CURRENT GRANTS;` を一度実行してから apply してください。

### 0.3. HCP Terraform 利用準備

#### ステップ 1: ワークスペースの準備

1. HCP Terraform の Organization を作成
2. 実行先となる Workspace を作成

- DEV: `dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`
- PROD: `prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`

#### ステップ 2: Team API Token の設定（`terraform login` は不要）

本プロジェクトでは、ローカル/CI ともに **Team API Token** を使用します。
`terraform login` でユーザートークンを保存する運用は採用しません。

注記（2026/03/27 時点）:

- Team API Token を利用する Team 管理機能は、HCP Terraform の課金プラン（Essentials 以上）が必要です。

`.env`（または CI Secrets）に以下のいずれかを設定してください。

- 推奨: `TF_TOKEN_app_terraform_io`
- 互換キー: `HCP_TERRAFORM_TOKEN`

Terraform CLI は `TF_TOKEN_app_terraform_io` を参照します。`HCP_TERRAFORM_TOKEN` を使う場合は、実行前に `TF_TOKEN_app_terraform_io` へエクスポートしてください。

#### ステップ 3: 変数の登録

上記で作成した秘密鍵とユーザー情報を、HCP Terraform の Workspace Variables に登録します。

Workspace 内の `Settings > Variables` から登録してください。

| Key                              | Value                            | Category  | Sensitive |
|----------------------------------|----------------------------------|-----------|-----------|
| app_env                          | dev（または prod）               | terraform | No        |
| loader_user_rsa_public_key       | (Public Key)                     | terraform | No        |
| dbt_user_rsa_public_key          | (Public Key)                     | terraform | No        |
| streamlit_user_rsa_public_key    | (Public Key)                     | terraform | No        |
| SNOWFLAKE_USER                   | (TerraformのUser Name)           | env       | No        |
| SNOWFLAKE_ROLE                   | <DEV/PROD>_TF_ADMIN_ROLE         | terraform | No        |
| SNOWFLAKE_PRIVATE_KEY            | (Private Key)                    | terraform | Yes       |

Note:

- 各 Workspace では、その Workspace 用の値のみを登録してください（DEV Workspace なら `app_env=dev`、PROD Workspace なら `app_env=prod`）。
- `dev_*` / `prod_*` 形式の変数は後方互換のため引き続き利用可能ですが、新規設定では `loader_user_rsa_public_key` などの共通キー名を推奨します。
- Sensitive 設定した値は後から参照できません。元データは鍵管理システム等で安全に保管してください。
- `SNOWFLAKE_PRIVATE_KEY` は改行コードを含むマルチライン形式のデータであるため、HCP Terraform 上では Category: terraform として登録を推奨します。
- `SNOWFLAKE_PRIVATE_KEY` の改行コード（`\n`）は、コード側で自動復元されます。
- Terraform Provider の接続先は `snowflake_organization_name` / `snowflake_account_name` を正本として使用します。
- `TF_VAR_SNOWFLAKE_ACCOUNT`（ORG-ACCOUNT 形式）は Terraform 変数への渡しと同時に Loader/dbt/Streamlit 共通の接続情報として使用します。

## 0.4. Workspace 構成と環境変数

HCP Terraform の接続先は backend 設定ファイル、Terraform の非機密設定値は `terraform/common.auto.tfvars` で管理し、秘密情報やローカル上書きは `.env` で管理します。

```bash
# terraform/backend.dev.hcl
organization = "zappyzed100"

workspaces {
    name = "dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms"
}
```

- `terraform/backend.dev.hcl`: DEV 環境の HCP Terraform backend 定義
- `terraform/backend.prod.hcl`: PROD 環境の HCP Terraform backend 定義
- `terraform/common.auto.tfvars`: 非機密の Terraform 共通設定
- `.env`: Team API Token やローカル用秘密鍵などの機密値

### 0.5. 実行フロー

1. HCP Terraform が秘密鍵を用いて認証トークン（JWT）を生成
2. Snowflake が登録済みの `DEV_TFRUNNER_USER` の公開鍵で検証
3. 認証後、`DEV_TF_ADMIN_ROLE` の権限で `main.tf` に定義された DB や Table が自動プロビジョニング

## 基本方針

- `APP_ENV` は権限ではなく行き先スイッチとして扱う
- Terraform 実行時は `TF_VAR_app_env` と `backend.*.hcl` を明示する
- prod apply は CI 実行（`environment: prod` 承認）経由に限定する
- 変数管理: 非機密の Terraform 設定は `terraform/common.auto.tfvars`、機密情報とローカル差分は `.env`、HCP 側の機密値は Workspace Variables で管理する

多層防御（必須）:

- 実行経路制御: prod 実行は CI のみ
- 資格情報制御: prod 秘密鍵はローカルに配布しない
- 権限制御: prod ロールは最小権限、開発者ロールは prod 不可
- 環境保護: CI の Environment 保護（承認必須・main 限定）
- 監査: prod 実行は CI ログで追跡可能にする

## 1. GitHub Environment 保護設定（本番環境アクセス制御）

本番環境（prod）への Terraform apply は、GitHub Environment による approval gate で制御します。  
多層防御戦略（コード側ガード + CI ジョブ制御 + GitHub Environment 承認）の最外層に位置します。

### 1.1. GitHub Environment `prod` の作成

Repository Settings で Environment を作成します。

**実行手順:**

1. GitHub Repository > Settings > Environments
2. "New environment" > Environment name に `prod` を入力
3. "Configure environment" をクリック

**参考リンク:** [GitHub Docs - Using environments for deployment](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)

### 1.2. Required reviewers の設定

Environment `prod` の保護ルール（Deployment protection rules）を設定します。

**設定項目:**

- **Environment name:** `prod`
- **Deployment branches:** `main` のみに制限
  - "Restrict deployments to specific branches" にチェック
  - Branch pattern: `main` を選択
- **Required reviewers:** 本番承認者を指定（最小 1 名以上）
  - "Require reviewers to approve deployments to this environment" にチェック
  - Require approval from: 承認者のGitHub アカウント or チームを選択

**参考リンク:** [GitHub Docs - Deployment protection rules](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment#required-reviewers)

### 1.3. CI/CD での enforcement

GitHub Actions の `terraform-prod-apply` ジョブが Environment `prod` を参照することで、以下が自動化・施行されます。

```yaml
jobs:
  terraform-prod-apply:
    environment: prod  # ← ここで実装
    runs-on: ubuntu-latest
    # 以降は artifact 取得 → apply 実行
```

**効果:**

- `main` ブランチへの commit 時、CI が Environment approval を要求
- 承認者の許可がなければ apply ジョブは実行されない
- 承認完了まで apply は「pending」状態で待機

### 1.4. 運用プロセス

本番環境への変更は以下の流れで進みます。

1. **開発:** ローカルで feature ブランチ作成 → コード修正 → テスト
2. **プレビュー:** PR 作成 → terraform-prod-plan ジョブが plan 結果を表示
3. **レビュー:** エンジニア + オペレーターが plan 内容を検討
4. **承認:** PR をマージ（`Create a merge commit` でマージコミット保持）
5. **approval gate:** CI が terraform-prod-apply ジョブで Environment 承認を要求
6. **実行:** Required reviewer が GitHub UI で承認 → apply 実行
7. **監査:** CI ログと GitHub Actions タブで実行履歴を確認可能

### 1.5. GitHub Actions ワークフロー詳細

`.github/workflows/ci.yml` に実装される Terraform ジョブの詳細です。

#### terraform-prod-plan ジョブ

**トリガー条件:**

- `pull_request` イベント（PR 作成・更新時）
- `push` イベント（main 反映時）
- `workflow_dispatch` イベント（手動実行、`run_prod_plan=true` 指定時）

**処理内容:**

```bash
terraform -chdir=terraform init -reconfigure -backend-config=backend.prod.hcl
terraform -chdir=terraform plan -no-color -out=../artifacts/terraform/prod.tfplan
```

**出力:**

- `artifacts/terraform/prod-plan.log` に plan 結果を保存
- `artifacts/terraform/prod.tfplan` に apply 用プランファイルを保存

**実行環境:**

- `TF_VAR_app_env=prod`
- Secrets: `HCP_TERRAFORM_TOKEN` 注入

#### terraform-prod-apply ジョブ

**トリガー条件:**

- `push to main` イベントのみ（PR では実行されない）
- 依存: `lint-and-test` ジョブが成功後
- **Environment gate**: `environment: prod` 参照（GitHub Environment approval 必須）

**処理内容:**

```bash
terraform -chdir=terraform init -reconfigure -backend-config=backend.prod.hcl
terraform -chdir=terraform apply -auto-approve ../artifacts/terraform/prod.tfplan
```

**処理フロー:**

1. CI ワークフロー準備完了後、`terraform-prod-apply` ジョブを開始
2. GitHub Environment approval チェック → 未承認の場合、ジョブは pending 状態で待機
3. Required reviewer による承認を待機
4. 承認完了後、自動的に apply 実行開始
5. apply 完了 → artifact に ログを保存
6. Commit comment で apply 結果を通知（✅ / ⚠️）

**出力:**

- `artifacts/terraform/prod-apply.log` に apply 完全ログを保存
- 成功/失敗に関わらず artifact 保存（`if: always()`）

**実行環境:**

- `TF_VAR_app_env=prod`
- Secrets: `HCP_TERRAFORM_TOKEN` 注入

**approval gate フロー図:**

```text
[Push to main]
    ↓
[lint-and-test: PASS]
    ↓
[terraform-prod-apply: PENDING]
    ↓
[GitHub: Awaiting approval from Required reviewers]
    ↓
[Reviewer: Approve in GitHub Actions tab]
    ↓
[terraform-prod-apply: RUNNING]
    ↓
[terraform -chdir=terraform apply -auto-approve ../artifacts/terraform/prod.tfplan]
    ↓
[Artifact save / Commit comment]
    ↓
[COMPLETE / FAILED]
```

### 1.6. トラブルシューティング

| 状況 | 原因 | 対応 |
|------|------|------|
| apply ジョブが pending のまま | 承認者の approval を待機中 | Environments タブで承認者の action を待つ |
| Environment 設定がない | prod Environment が未作成 | セクション 1.1 を参照して作成 |
| 承認者だが Approve ボタンが出ない | GitHub の permissions 不足 | Organization オーナーに確認を要求 |

### 1.7. 設定の変更管理

Environment `prod` の設定を変更した場合は、**Issue #139** に以下の内容をコメントしてください。

**記録フォーマット:**

```markdown
## Environment prod 設定変更履歴

### 変更日時: YYYY-MM-DD HH:MM JST
### 実施者: @username
### 変更内容:
- [ ] Deployment branch 制限: main のみ
- [ ] Required reviewers: 承認者数 N 名
- [ ] 承認者: @user1, @user2, ...

### 検証結果:
- [ ] terraform-prod-plan が PR で実行確認
- [ ] main マージ後に apply ジョブが pending 確認
- [ ] 承認者による approval で apply 実行確認
```

### 1.8. GitHub Secrets の設定と管理

CI/CD ワークフローで使用する秘密情報は、GitHub Repository Secrets として登録されます。  
以下の一覧に従って、すべて設定されていることを確認してください。

**Repository Secrets 設定一覧:**

| Secret Name | 用途 | 設定対象環境 | 設定方法 |
|-------------|------|-------------|---------|
| `HCP_TERRAFORM_TOKEN` | HCP Terraform 認可トークン | 全環境 | [HCP Terraform > Account Settings > API Tokens](https://app.terraform.io/app/settings/tokens) より発行 |
| `SNOWFLAKE_ACCOUNT` | Snowflake Account ID | 全環境 | Snowflake アカウント設定より確認 |
| `DEV_DBT_USER_RSA_PRIVATE_KEY` | DEV dbt 実行ユーザーの秘密鍵 | dev ワークスペース | terraform/README.md セクション 0.2 より生成 |
| `DEV_LOADER_USER_RSA_PRIVATE_KEY` | DEV Loader 実行ユーザーの秘密鍵 | dev ワークスペース | terraform/README.md セクション 0.2 より生成 |
| `DEV_STREAMLIT_USER_RSA_PRIVATE_KEY` | DEV Streamlit 実行ユーザーの秘密鍵 | dev ワークスペース | terraform/README.md セクション 0.2 より生成 |
| `PROD_DBT_USER_RSA_PRIVATE_KEY` | PROD dbt 実行ユーザーの秘密鍵 | prod ワークスペース | terraform/README.md セクション 0.2 より生成 |
| `PROD_LOADER_USER_RSA_PRIVATE_KEY` | PROD Loader 実行ユーザーの秘密鍵 | prod ワークスペース | terraform/README.md セクション 0.2 より生成 |
| `PROD_STREAMLIT_USER_RSA_PRIVATE_KEY` | PROD Streamlit 実行ユーザーの秘密鍵 | prod ワークスペース | terraform/README.md セクション 0.2 より生成 |

**設定手順:**

1. GitHub Repository > Settings > Secrets and variables > Actions
2. "New repository secret" をクリック
3. Name に上表の Secret 名を入力
4. Value に対応する秘密情報を貼り付け
5. "Add secret" で確定

**秘密鍵形式について:**

- 秘密鍵（`.p8` ファイル）の内容をそのまま Secrets に登録してください
- 改行コード（`\n`）はそのまま含めてください。CI ワークフロー側で自動復元されます
- PEM 形式の開始・終了行（`-----BEGIN PRIVATE KEY-----` / `-----END PRIVATE KEY-----`）も含める

**参考リンク:** [GitHub Docs - Using secrets in GitHub Actions](https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions)

## 2. 実行手順

Terraform CLI は `.env` または CI Secrets から
`TF_TOKEN_app_terraform_io`（互換: `HCP_TERRAFORM_TOKEN`）を読み込みます。
`terraform login` は不要です。

注意:

- `terraform init` は必ず `-backend-config=backend.dev.hcl` または `-backend-config=backend.prod.hcl` を明示してください。
- backend-config 未指定の直接実行は、ガード用 workspace（`__guard_do_not_use_without_backend_config__`）へ接続されます。

### 2.1. DEV / PROD 共通手順

- 実行前に `TF_VAR_app_env` と backend ファイルを明示します。

- `TF_VAR_app_env=dev|prod`
- `terraform init -reconfigure -backend-config=backend.<env>.hcl`

```bash
# DEV 例
TF_VAR_app_env=dev terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
TF_VAR_app_env=dev terraform -chdir=terraform plan

# apply も同様
TF_VAR_app_env=dev terraform -chdir=terraform apply
```

明示的に `init` だけ実行したい場合:

```bash
terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
```

補足:

- CI では `TF_VAR_app_env=prod` と `backend.prod.hcl` を利用します。
- prod apply は CI 承認フロー経由のみ許可します。

## 2.2. データパイプライン CD オーケストレーション（Loader + dbt）

Prod Terraform apply 成功後、自動的に snowflake_loader と dbt を実行する本番デプロイフローです。

**実行条件:**

- Terraform apply ジョブが成功した場合のみ実行
- `main` ブランチへのpush 時のみ実行
- すべてのジョブが同じ GitHub Environment `prod` の approval 配下で実行

**パイプライン構成:**

```text
[terraform-prod-apply: PASS]
    ↓
[prod-loader-run: RUNNING → PASS (データロード)]
    ↓
[prod-dbt-run: RUNNING → PASS (変換・処理)]
    ↓
[prod-dbt-test: RUNNING → PASS (品質検証)]
    ↓
[COMPLETE]
```

### prod-loader-run ジョブ

**目的:** 新規データを Bronze 層へロード

**実行コマンド:**

```bash
APP_ENV=prod python src/infrastructure/snowflake_loader.py
```

**出力:**

- `artifacts/data-pipeline/prod-loader.log` — ロード実行ログ

**依存関係:** `needs: [terraform-prod-apply]`

### prod-dbt-run ジョブ

**目的:** dbt を実行して Silver/Gold 層のモデルを構築

**実行コマンド:**

```bash
APP_ENV=prod dbt run
```

**出力:**

- `artifacts/data-pipeline/prod-dbt-run.log` — dbt run ログ
- `src/transform/target/run_results.json` — 実行結果メタデータ

**依存関係:** `needs: [prod-loader-run]`

### prod-dbt-test ジョブ

**目的:** dbt test を実行してデータ品質を検証

**実行コマンド:**

```bash
APP_ENV=prod dbt test
```

**出力:**

- `artifacts/data-pipeline/prod-dbt-test.log` — dbt test ログ
- `src/transform/target/run_results.json` — テスト結果メタデータ

**依存関係:** `needs: [prod-dbt-run]`

**実行ログの確認:**

- GitHub Actions > 対象 run > 各ジョブのログタブ
- または Run summary の Artifacts セクションからダウンロード

## 2.3. 復旧手順（運用者向け Runbook）

prod apply が失敗した場合、次の順で切り分けて復旧してください。

1. **Actions 実行履歴の確認**
    - 対象 run: `CI Pipeline` の `terraform-prod-apply`
    - `prod-apply.log` artifact をダウンロードしてエラー行を特定
2. **Environment 保護の確認**
    - `Settings > Environments > prod`
    - Deployment branches が `main` 限定か確認
    - Required reviewers が有効か確認
3. **Secrets の有効性確認**
    - `HCP_TERRAFORM_TOKEN` が CI 用 Team API Token であること
    - トークン失効時は再発行して Secrets を更新
4. **HCP Terraform 権限確認**
    - CI 用 Team が prod workspace で apply 可能であること
    - 開発者ロールに prod apply 権限が付与されていないこと
5. **再実行**
    - 必要に応じて main へ修正コミットをマージし、再度 approval 後に apply

**緊急時（break-glass）ポリシー:**

- 原則としてローカルから prod 変更は行わない
- 例外対応は Issue を起票し、実施者・理由・実行コマンド・結果を記録する
- 事後に CI 経路へ設定を戻し、Secrets と権限の棚卸しを実施する

## 2.4. トラブルシューティング（データパイプライン CD）

Loader / dbt ジョブが失敗した場合の切り分け手順です。

### prod-loader-run が失敗した場合

**確認項目:**

1. Actions ログで「Run prod snowflake loader」ステップを確認
   - Snowflake 接続エラー → セクション 1.8 で `PROD_LOADER_USER_RSA_PRIVATE_KEY` を再確認
   - データ形式エラー → `data/` ディレクトリのファイル形式を検証
   - 権限エラー → `PROD_LOADER_ROLE` の Snowflake 権限を確認

2. `prod-loader.log` artifact をダウンロード → 具体的なエラー行を特定

**再実行:**

- ローカル検証: `APP_ENV=prod python src/infrastructure/snowflake_loader.py`
- 修正後、main へ PR/merge しなおして CI 再実行

### prod-dbt-run が失敗した場合

**確認項目:**

1. Actions ログで「Run prod dbt run」ステップを確認
    - コンパイルエラー → dbt yamlの構文を確認（`src/transform/`）
    - Snowflake 権限エラー → `PROD_DBT_ROLE` の Schema/Table 権限を確認
    - 依存関係エラー → dbt DAG で参照モデルが存在するか確認

2. `prod-dbt-run.log` と `run_results.json` を確認

**再実行:**

- ローカル検証: `APP_ENV=prod dbt run`
- 修正後、main へ PR/merge しなおして CI 再実行

### prod-dbt-test が失敗した場合

**確認項目:**

1. Actions ログで「Run prod dbt test」ステップを確認
    - テスト失敗 → `src/transform/tests/` の要件を確認
    - depending_on テスト失敗 → upstream モデルのデータ品質を見直す

2. `prod-dbt-test.log` で fail した spec を確認

**対応:**

- テスト要件を見直す（厳しすぎないか確認）
- または upstream モデルのロジックを修正
- 修正後、main へ PR/merge しなおして CI 再実行

### いずれかのジョブが失敗した場合

#### 自動的に後続ステップは実行されません（needs 依存により）

失敗ジョブが fixed された後は、**再度本番環境から再実行**するために:

1. GitHub で最新の main commit を確認
2. Actions tab で対象 run を確認
3. ジョブが pending 状態なら approval を与えているか確認
4. 不要なら `Re-run failed jobs` ボタンで再実行

**注意:** 本番ロール・Snowflake オブジェクトの状態によっては、rebuild や recreate が必要な場合があります。Issue を起票して運用チームに相談してください。

## 3. 設計判断（ADR）

### 3.1. 削除保護と managed access の採用

`modules/snowflake_env/main.tf` の重要リソースでは、critical resource を常時保護しています。

方針:

- `prevent_destroy = true` は Bronze のデータテーブル（RAW 層）に限定して適用する
- Role / User / Network policy / Database / Schema / Warehouse / Stage / File format は設計変更時の再作成・移行を優先し、`prevent_destroy` は適用しない
- Network policy は bootstrap で作成後、Terraform に import して継続管理する

補足:

- 既存の functional role は維持しつつ、Terraform では data-layer access role をその下位にぶら下げて権限を階層化する
- `READ_ONLY_ROLE` / `READ_WRITE_ROLE` を中間ロールとして追加し、functional role と data-layer access role の責務を分離する
- schema object grant は `modules/snowflake_env/modules/schema_object_grants` モジュールに集約し、`permission_level` (`SELECT` / `ALL`) で制御する
- schema object grant は drift 抑制のため `grant_on_future=true` / `grant_on_all=false` を標準とする
- Terraform が管理するテーブルへの権限付与は、個別の `snowflake_grant_privileges_to_account_role` リソースで明示的に行う。`grant_on_all` (GRANT ON ALL TABLES IN SCHEMA) は apply 時点のスナップショット操作であり、dbt DDL 混在環境で state drift を引き起こすため使用しない
- テーブル削除を伴う変更は、保護解除を含む別 PR か、明示的な運用手順を前提に実施する
- managed access は schema 作成時点で有効化し、以降は Terraform 管理下で維持する

### 3.2. Network Policy 適用方針

方針:

- `modules/snowflake_env/main.tf` で `<ENV>_TERRAFORM_NETWORK_POLICY` を作成する
- 許可 CIDR は `terraform/common.auto.tfvars` 内の `DEV_NETWORK_POLICY_ALLOWED_IPS` / `PROD_NETWORK_POLICY_ALLOWED_IPS` で管理する
- Service users（loader/dbt/streamlit）には Terraform で network policy を適用する
- Terraform 実行ユーザー（`<ENV>_TFRUNNER_USER`）への適用は bootstrap SQL で管理する

環境別の許可 CIDR 方針:

| 環境 | 設定値 | 理由 |
|------|--------|------|
| DEV | `["0.0.0.0/0"]`（全許可） | 開発者のローカル IP が固定されないため IP 制限なし。HCP Terraform ランナーからの接続も同様に全許可 |
| PROD | GitHub Actions ランナーの固定 IP | CI 専用実行に限定し接続元を絞る |

運用上の注意:

- 許可 CIDR を設定しない場合、Terraform 側の network policy リソースは作成されない
- PROD の HCP Terraform 公開レンジ更新時は `PROD_NETWORK_POLICY_ALLOWED_IPS` と bootstrap SQL の双方を同時更新する
