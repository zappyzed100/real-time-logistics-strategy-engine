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
| SNOWFLAKE_USER                   | (User Name)                      | env       | No        |
| SNOWFLAKE_ROLE                   | <DEV/PROD>_TF_ADMIN_ROLE         | terraform | No        |
| SNOWFLAKE_PRIVATE_KEY            | (Private Key)                    | terraform | Yes       |
| SNOWFLAKE_AUTHENTICATOR          | SNOWFLAKE_JWT                    | env       | No        |

Note:

- 各 Workspace では、その Workspace 用の値のみを登録してください（DEV Workspace なら `app_env=dev`、PROD Workspace なら `app_env=prod`）。
- `dev_*` / `prod_*` 形式の変数は後方互換のため引き続き利用可能ですが、新規設定では `loader_user_rsa_public_key` などの共通キー名を推奨します。
- Sensitive 設定した値は後から参照できません。元データは鍵管理システム等で安全に保管してください。
- `SNOWFLAKE_PRIVATE_KEY` は改行コードを含むマルチライン形式のデータであるため、HCP Terraform 上では Category: terraform として登録を推奨します。
- `SNOWFLAKE_PRIVATE_KEY` の改行コード（`\n`）は、コード側で自動復元されます。

### 0.4. Workspace 構成と環境変数

HCP Terraform のワークスペース名と Organization は `.env` で管理します。

```bash
# .env の例
HCP_TF_ORGANIZATION=zappyzed100
HCP_TF_WORKSPACE_DEV=dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms
HCP_TF_WORKSPACE_PROD=prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms
```

- `HCP_TF_ORGANIZATION`: HCP Terraform の Organization 名
- `HCP_TF_WORKSPACE_DEV`: DEV 環境のワークスペース名
- `HCP_TF_WORKSPACE_PROD`: PROD 環境のワークスペース名

実行時に `terraform/tf` ラッパースクリプトが自動的に読み込みます。

### 0.5. 実行フロー

1. HCP Terraform が秘密鍵を用いて認証トークン（JWT）を生成
2. Snowflake が登録済みの `DEV_TFRUNNER_USER` の公開鍵で検証
3. 認証後、`DEV_TF_ADMIN_ROLE` の権限で `main.tf` に定義された DB や Table が自動プロビジョニング

## 基本方針

- 実行環境切り替え: `/app/.env` の `APP_ENV`（`dev` / `prod`）を書き換えるだけで切り替える
- 実行コマンド: 原則 `./terraform/tf` ラッパーを使用する
- 変数管理: 実行変数は HCP Terraform の Workspace Variables で一元管理し、ローカルの `.tfvars` は使用しない

## 1. 実行手順

Docker コンテナ内で実行する場合も、初回は `terraform login` による認可が必要です。

### 1.1. DEV / PROD 共通手順

`terraform/tf` ラッパーを使うと、以下を自動化できます。

- `/app/.env` の自動読み込み
- `TF_VAR_app_env` の自動設定（`APP_ENV` 未設定時は `dev`）
- `init -reconfigure` の自動実行

```bash
# /app/.env の APP_ENV を dev / prod に書き換えてから実行
./terraform/tf plan

# apply も同様
./terraform/tf apply
```

明示的に `init` だけ実行したい場合:

```bash
./terraform/tf init
```

補足:

- `APP_ENV` をコマンド実行時に一時上書きしたい場合は `APP_ENV=prod ./terraform/tf plan` の形式も利用できます。
- ラッパーを使わずに `terraform` コマンドを直接実行する運用は推奨しません。

## 2. 設計判断（ADR）

### 2.1. `lifecycle.prevent_destroy = false` の採用

`modules/snowflake_env/main.tf` の主要リソースで、あえて削除保護を無効化しています。

理由:

- 開発・検証フェーズにおける「破壊と再作成」のサイクルを優先するため

運用方針:

- 構築完了後、本番環境で保護を強める場合は、Database/Schema/Role 等の重要リソースから順次 `true` へ変更を推奨

### 2.2. Network Policy の未適用理由

理由:

- HCP Terraform の実行元 IP アドレスが固定ではないため、安易な制限は接続断やロックアウトを招くリスクがある

運用方針:

- 接続元（実行環境）の構成が確定した段階で、別途 Network Policy の導入を検討する

