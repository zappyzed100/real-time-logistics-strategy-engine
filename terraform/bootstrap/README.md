# Terraform Bootstrap SQL

このフォルダには、通常の Terraform 実行前に一度だけ実行する
Snowflake 初期セットアップ用 SQL を配置しています。

## ファイル構成

- `sql/setup_snowflake_tf_dev.sql`: DEV 環境向けの初期セットアップ SQL
- `sql/setup_snowflake_tf_prod.sql`: PROD 環境向けの初期セットアップ SQL
- `sync_bootstrap_sql_from_tfvars.sh`: `terraform/common.auto.tfvars` から SQL 固定値を同期するスクリプト

## 使い方

1. Terraform の正本値を反映するため、`./terraform/bootstrap/sync_bootstrap_sql_from_tfvars.sh` を実行してください。
2. 対象環境の Snowflake で、`ACCOUNTADMIN` ロールで実行してください。
3. 実行前に、SQL 冒頭の DECLARE ブロック内にある `runner_rsa_key_1` に RSA 公開鍵を設定してください。鍵ローテーション時は `runner_rsa_key_2` にも設定します（初回は空文字のままで問題ありません）。
4. SQL 内の preflight checks で、未置換プレースホルダと誤アカウント実行はエラーで停止します。
5. 秘密情報（秘密鍵・認証情報）はコミットしないでください。
6. これらの SQL は日次運用用ではなく、初回セットアップ用です。

補足:

- `DATA_RETENTION_TIME_IN_DAYS` / `ALLOWED_IP_LIST` は `terraform/common.auto.tfvars` を正本として同期されます。

## 運用ポリシー

- ネットワークポリシーは bootstrap では作成せず、Terraform が直接作成・管理します（`DEV_TF_ADMIN_ROLE` に `CREATE NETWORK POLICY` が付与されているため）。
- `*_TFRUNNER_USER` にはネットワークポリシーを適用しません。JWT/RSA鍵ペア認証で保護しており、HCP Terraform ランナーは動的IPを使用するためIPによる制限は機能しません。
- ネットワークポリシーはサービスユーザー（loader / dbt / streamlit）に対して Terraform 管理下で適用されます。
- PROD では `PROD_TF_ADMIN_ROLE` の `SYSADMIN` への継承はデフォルトで無効化し、必要時のみ期限付きで運用してください。
- Terraform 実行ユーザーは 2 スロット鍵運用に対応できますが、初回 bootstrap では `RSA_PUBLIC_KEY` のみ必須です。`RSA_PUBLIC_KEY_2` は将来の鍵ローテーション時に利用します。

## Bootstrap 後の必須作業

Bootstrap SQL 実行後は、以下のオブジェクトを Terraform state へ import してください。

- Databases: Bronze / Silver / Gold
- Schemas: RAW_DATA / CLEANSED / MARKETING_MART

import ID 形式:

- `snowflake_database`: `<DATABASE_NAME>`
- `snowflake_schema`: `<DATABASE_NAME>.<SCHEMA_NAME>`
