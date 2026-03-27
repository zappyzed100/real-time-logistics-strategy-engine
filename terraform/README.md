# Terraform 運用ガイド

本プロジェクトでは HCP Terraform (Remote Backend) を利用します。

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

実行する SQL は以下に分離して管理しています。

- DEV: `bootstrap/sql/setup_snowflake_tf_dev.sql`
- PROD: `bootstrap/sql/setup_snowflake_tf_prod.sql`

補足:

- SQL 内の公開鍵プレースホルダ（`<YOUR_DEV_RSA_PUBLIC_KEY_HERE>`, `<YOUR_PROD_RSA_PUBLIC_KEY_HERE>`）を実値に置き換えてから実行してください。
- Bootstrap SQL は「初回セットアップ用」です。日次運用で繰り返し実行するものではありません。

補足:

- 通常運用では、Warehouse は手動作成せず Terraform/HCP 側で作成します。
- 例外として、過去運用で同名 Warehouse が既に存在する場合のみ、`GRANT OWNERSHIP ON WAREHOUSE ... TO ROLE <ENV>_TF_ADMIN_ROLE COPY CURRENT GRANTS;` を一度実行してから apply してください。

### 0.3. HCP Terraform 利用準備

#### ステップ 1: ワークスペースの準備

1. HCP Terraform の Organization を作成
2. 実行先となる Workspace を作成

- DEV: `dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`
- PROD: `prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`

#### ステップ 2: CLI 認証

```bash
terraform login
```

#### ステップ 3: 変数の登録

上記で作成した秘密鍵とユーザー情報を、HCP Terraform の Workspace Variables に登録します。

Workspace 内の `Settings > Variables` から登録してください。

| Key                              | Value                            | Category  | Sensitive |
|----------------------------------|----------------------------------|-----------|-----------|
| loader_user_rsa_public_key       | (Public Key)                     | terraform | No        |
| dbt_user_rsa_public_key          | (Public Key)                     | terraform | No        |
| streamlit_user_rsa_public_key    | (Public Key)                     | terraform | No        |
| snowflake_organization_name      | (Account名の前半分)               | terraform | No        |
| snowflake_account_name           | (Account名の後半分)               | terraform | No        |
| SNOWFLAKE_USER                   | (TerraformのUser Name)           | env       | No        |
| SNOWFLAKE_ROLE                   | <DEV/PROD>_TF_ADMIN_ROLE         | terraform | No        |
| SNOWFLAKE_PRIVATE_KEY            | (Private Key)                    | terraform | Yes       |
| SNOWFLAKE_AUTHENTICATOR          | SNOWFLAKE_JWT                    | env       | No        |

Note:

- 各 Workspace では、その Workspace 用の値のみを登録してください（DEV Workspace なら `app_env=dev`、PROD Workspace なら `app_env=prod`）。
- `dev_*` / `prod_*` 形式の変数は後方互換のため引き続き利用可能ですが、新規設定では `loader_user_rsa_public_key` などの共通キー名を推奨します。
- Sensitive 設定した値は後から参照できません。元データは鍵管理システム等で安全に保管してください。
- `SNOWFLAKE_PRIVATE_KEY` は改行コードを含むマルチライン形式のデータであるため、HCP Terraform 上では Category: terraform として登録を推奨します。
- `SNOWFLAKE_PRIVATE_KEY` の改行コード（`\n`）は、コード側で自動復元されます。

## 0.4. Workspace 構成と環境変数

HCP Terraform のワークスペース名と Organization は `.env.shared` で管理し、秘密情報やローカル上書きは `.env` で管理します。

```bash
# .env.shared の例
HCP_TF_WORKSPACE_DEV=dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms
HCP_TF_WORKSPACE_PROD=prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms

DEV_TF_ADMIN_ROLE=DEV_TF_ADMIN_ROLE
PROD_TF_ADMIN_ROLE=PROD_TF_ADMIN_ROLE
```

- `HCP_TF_ORGANIZATION`: HCP Terraform の Organization 名
- `HCP_TF_WORKSPACE_DEV`: DEV 環境のワークスペース名
- `HCP_TF_WORKSPACE_PROD`: PROD 環境のワークスペース名

実行時に `terraform/tf` ラッパースクリプトが `.env.shared` を先に読み込み、その後 `.env` で同名キーを上書きします。

### 0.5. 実行フロー

1. HCP Terraform が秘密鍵を用いて認証トークン（JWT）を生成
2. Snowflake が登録済みの `DEV_TFRUNNER_USER` の公開鍵で検証
3. 認証後、`DEV_TF_ADMIN_ROLE` の権限で `main.tf` に定義された DB や Table が自動プロビジョニング

## 基本方針

- `APP_ENV` は権限ではなく行き先スイッチとして扱う
- ローカル実行は `APP_ENV` 未指定時に `dev` として実行
- `APP_ENV=prod` は CI 実行（`CI=true` または `GITHUB_ACTIONS=true`）でのみ許可
- 実行コマンド: 原則 `./terraform/tf` ラッパーを使用する
- 変数管理: 共通の非機密設定は `.env.shared`、機密情報とローカル差分は `.env`、HCP 側の機密値は Workspace Variables で管理する

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
- `workflow_dispatch` イベント（手動実行、`run_prod_plan=true` 指定時）

**処理内容:**
```bash
./terraform/tf plan -no-color
```

**出力:**
- `artifacts/terraform/prod-plan.log` に plan 結果を保存
- tfvars ファイルも一緒に artifact 化（runtime/app_env 情報）

**実行環境:**
- `APP_ENV=prod`（prod ワークスペース自動選択）
- `CI=true` / `GITHUB_ACTIONS=true`（環境ガード bypass）
- Secrets: `HCP_TERRAFORM_TOKEN`, `HCP_TF_ORGANIZATION` 注入

#### terraform-prod-apply ジョブ

**トリガー条件:**
- `push to main` イベントのみ（PR では実行されない）
- 依存: `lint-and-test` ジョブが成功後
- **Environment gate**: `environment: prod` 参照（GitHub Environment approval 必須）

**処理内容:**
```bash
./terraform/tf apply -auto-approve
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
- `APP_ENV=prod`
- `CI=true` / `GITHUB_ACTIONS=true`
- Secrets: `HCP_TERRAFORM_TOKEN`, `HCP_TF_ORGANIZATION` 注入

**approval gate フロー図:**

```
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
[./terraform/tf apply -auto-approve]
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

```
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
| `HCP_TF_ORGANIZATION` | HCP Terraform の Organization 名 | 全環境 | terraform/README.md セクション 0.3 参照 |
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

Docker コンテナ内で実行する場合も、初回は `terraform login` による認可が必要です。

### 2.1. DEV / PROD 共通手順

`terraform/tf` ラッパーを使うと、以下を自動化できます。

- `/app/.env.shared` → `/app/.env` の順で自動読み込み
- `TF_VAR_app_env` と Terraform 入力変数の自動設定
- `init -reconfigure` の自動実行

```bash
# ローカルは APP_ENV 未指定でも dev として実行
./terraform/tf plan

# apply も同様
./terraform/tf apply
```

明示的に `init` だけ実行したい場合:

```bash
./terraform/tf init
```

補足:

- CI では `APP_ENV=prod ./terraform/tf plan` / `apply` の形式を利用できます。
- ラッパーを使わずに `terraform` コマンドを直接実行する運用は推奨しません。

## 3. 設計判断（ADR）

### 3.1. `lifecycle.prevent_destroy = false` の採用

`modules/snowflake_env/main.tf` の主要リソースで、あえて削除保護を無効化しています。

理由:

- 開発・検証フェーズにおける「破壊と再作成」のサイクルを優先するため

運用方針:

- 構築完了後、本番環境で保護を強める場合は、Database/Schema/Role 等の重要リソースから順次 `true` へ変更を推奨

### 3.2. Network Policy の未適用理由

理由:

- HCP Terraform の実行元 IP アドレスが固定ではないため、安易な制限は接続断やロックアウトを招くリスクがある

運用方針:

- 接続元（実行環境）の構成が確定した段階で、別途 Network Policy の導入を検討する

