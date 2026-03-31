# Terraform Bootstrap SQL

このフォルダには、通常の Terraform 実行前に一度だけ実行する
Snowflake 初期セットアップ用 SQL を配置しています。

## ファイル構成

- `sql/setup_snowflake_tf_dev.sql`: DEV 環境向けの初期セットアップ SQL
- `sql/setup_snowflake_tf_prod.sql`: PROD 環境向けの初期セットアップ SQL
- `sql/setup_snowflake_tf_template.sql`: 環境別 SQL の共通テンプレート

## 使い方

1. テンプレート（`sql/setup_snowflake_tf_template.sql`）を起点に環境別 SQL を更新してください。
2. 対象環境の Snowflake で、`ACCOUNTADMIN` ロールで実行してください。
3. 実行前に必須プレースホルダ（`EXPECTED_ACCOUNT`, `RUNNER_RSA_PUBLIC_KEY`, CIDR）を実値へ置き換えてください。`RUNNER_RSA_PUBLIC_KEY_2` は初回 bootstrap では任意です。
4. SQL 内の preflight checks で、未置換プレースホルダと誤アカウント実行はエラーで停止します。
5. 秘密情報（秘密鍵・認証情報）はコミットしないでください。
6. これらの SQL は日次運用用ではなく、初回セットアップ用です。

## 運用ポリシー

- Network policy は bootstrap 段階で Terraform 実行ユーザーへ適用し、所有権を `*_TF_ADMIN_ROLE` へ移譲します。
- PROD では `PROD_TF_ADMIN_ROLE` の `SYSADMIN` への継承はデフォルトで無効化し、必要時のみ期限付きで運用してください。
- Terraform 実行ユーザーは 2 スロット鍵運用に対応できますが、初回 bootstrap では `RSA_PUBLIC_KEY` のみ必須です。`RSA_PUBLIC_KEY_2` は将来の鍵ローテーション時に利用します。

## Bootstrap 後の必須作業

Bootstrap SQL 実行後は、以下のオブジェクトを Terraform state へ import してください。

- Databases: Bronze / Silver / Gold
- Schemas: RAW_DATA / CLEANSED / MARKETING_MART
- Network policy: `<ENV>_TERRAFORM_NETWORK_POLICY`

import ID 形式:

- `snowflake_database`: `<DATABASE_NAME>`
- `snowflake_schema`: `<DATABASE_NAME>.<SCHEMA_NAME>`
- `snowflake_network_policy`: `<NETWORK_POLICY_NAME>`
