# Terraform 運用ガイド

本プロジェクトでは HCP Terraform (Remote Backend) を利用します。

## 基本方針

- Backend設定の分離: `backend.hcl`（共通）と `backend.<env>.hcl`（環境別）を組み合わせて使用する
- 環境切り替え: Workspace の切り替えは `terraform init -reconfigure` で行う
- 変数管理: 実行変数は HCP Terraform の Workspace Variables で一元管理し、ローカルの `.tfvars` は使用しない

## 1. HCP Terraform セットアップ

### 1.1. リソースの準備

1. HCP Terraform アカウントおよび Organization を作成
2. 実行先となる以下の標準 Workspace を作成

- DEV: `dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`
- PROD: `prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms`

### 1.2. 変数の登録

Workspace 内の `Settings` > `Variables` から登録してください。

| Key                              | Value                            | Category  | Sensitive |
|----------------------------------|----------------------------------|-----------|-----------|
| dev_loader_user_rsa_public_key   | (Public Key)                     | terraform | No        |
| dev_dbt_user_rsa_public_key      | (Public Key)                     | terraform | No        |
| dev_streamlit_user_rsa_public_key| (Public Key)                     | terraform | No        |
| snowflake_organization_name      | (Account名の前半分)               | terraform | No        |
| snowflake_account_name           | (Account名の後半分)               | terraform | No        |
| SNOWFLAKE_USER                   | (User Name)                      | env       | No        |
| SNOWFLAKE_PRIVATE_KEY            | (Private Key)                    | terraform | Yes       |
| SNOWFLAKE_AUTHENTICATOR          | SNOWFLAKE_JWT                    | env       | No        |

Note:

- Sensitive 設定した値は後から参照できません。元データは鍵管理システム等で安全に保管してください。
- `SNOWFLAKE_PRIVATE_KEY` はは改行コードを含むマルチライン形式のデータであるため、
HCP Terraform 上では Category: terraform として登録を推奨します。
- `SNOWFLAKE_PRIVATE_KEY` の改行コード（`\n`）は、コード側で自動復元されます。

### 1.3. CLI 認証

```bash
terraform login
```

## 2. Backend 設定ファイルの作成

HCP Terraform の backend 設定は変数が使えないため、以下の外部ファイルを作成して `init` 時に読み込みます。

共通設定: `backend.hcl`

```hcl
organization = "<your-hcp-organization>"
```

環境別設定: `backend.dev.hcl`

```hcl
workspaces {
  name = "dev-real-time-logistics-strategy-engine-distilled-mip-1m-01ms"
}
```

環境別設定: `backend.prod.hcl`

```hcl
workspaces {
  name = "prod-real-time-logistics-strategy-engine-distilled-mip-1m-01ms"
}
```

`.example` ファイルも用意しています。必要に応じてコピーして利用してください。

```bash
cp backend.hcl.example backend.hcl
cp backend.dev.hcl.example backend.dev.hcl
cp backend.prod.hcl.example backend.prod.hcl
```

## 3. 実行手順

Docker コンテナ内で実行する場合も、初回は `terraform login` による認可が必要です。

### 3.1. DEV 環境の操作

```bash
cd terraform
terraform init -reconfigure -backend-config="backend.hcl" -backend-config="backend.dev.hcl"
terraform plan
terraform apply
```

### 3.2. PROD 環境の操作

```bash
cd terraform
terraform init -reconfigure -backend-config="backend.hcl" -backend-config="backend.prod.hcl"
terraform plan
terraform apply
```

## 4. 設計判断（ADR）

### 4.1. `lifecycle.prevent_destroy = false` の採用

`modules/snowflake_env/main.tf` の主要リソースで、あえて削除保護を無効化しています。

理由:

- 開発・検証フェーズにおける「破壊と再作成」のサイクルを優先するため

運用方針:

- 構築完了後、本番環境で保護を強める場合は、Database/Schema/Role 等の重要リソースから順次 `true` へ変更を推奨

### 4.2. Network Policy の未適用理由

理由:

- HCP Terraform の実行元 IP アドレスが固定ではないため、安易な制限は接続断やロックアウトを招くリスクがある

運用方針:

- 接続元（実行環境）の構成が確定した段階で、別途 Network Policy の導入を検討する

