# Terraform 運用ガイド

このディレクトリでは HCP Terraform (remote backend) を利用します。

## 基本方針

- [backend.hcl](backend.hcl) には organization のみを記載します。
- workspace 名は環境ごとの backend 設定ファイルで渡します。
- 環境切替のたびに `terraform init -reconfigure` を実行します。

理由: Terraform backend 設定では通常の入力変数を使った動的切替ができず、`workspaces.name` のようなネスト項目は CLI 引数で直接渡せないためです。

## 事前準備

1. Terraform Cloud にログイン

```powershell
terraform login
```

2. このディレクトリへ移動

```powershell
cd terraform
```

## DEV ワークスペースで実行

```powershell
terraform init -reconfigure -backend-config="backend.hcl" -backend-config="backend.dev.hcl"
terraform plan
```

## PROD ワークスペースで実行

```powershell
terraform init -reconfigure -backend-config="backend.hcl" -backend-config="backend.prod.hcl"
terraform plan
```

## Apply

```powershell
terraform apply
```

## 変数について

HCP Terraform はリモートで実行されるため、ローカルの `.tfvars` ファイルは使えません。  
対象ワークスペースの Variables ページで登録してください。

- URL: `https://app.terraform.io/app/<org>/<workspace>/settings/vars`
- 種別: **Terraform variable** を選択

| 変数名                           | Sensitive | 種別        | 内容 (例)                                                   |
|----------------------------------|-----------|-------------|-------------------------------------------------------------|
| snowflake_organization_name      | —         | Terraform   | SNOWFLAKE_ACCOUNTの前半分                                   |
| snowflake_account_name           | —         | Terraform   | SNOWFLAKE_ACCOUNTの後半分                                   |
| dev_loader_user_rsa_public_key   | ✅         | Terraform   | (作成するLoaderユーザーの公開鍵: PEM本文)                   |
| dev_dbt_user_rsa_public_key      | ✅         | Terraform   | (作成するdbtユーザーの公開鍵: PEM本文)                      |
| snowflake_user                   | —         | Terraform   | TF_PROVISIONER (Terraform実行用ユーザー)                    |
| snowflake_private_key            | ✅         | Terraform   | -----BEGIN RSA PRIVATE KEY----- ... (秘密鍵の中身)          |

登録後は `terraform plan` だけで実行できます（`init` の再実行は不要）。

`snowflake_private_key` は HCP の入力都合で改行が `\n` になる場合がありますが、コード側で改行復元して利用しています。
