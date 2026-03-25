# Terraform Bootstrap SQL

このフォルダには、通常の Terraform 実行前に一度だけ実行する
Snowflake 初期セットアップ用 SQL を配置しています。

## ファイル構成

- `sql/setup_snowflake_tf_dev.sql`: DEV 環境向けの初期セットアップ SQL
- `sql/setup_snowflake_tf_prod.sql`: PROD 環境向けの初期セットアップ SQL

## 使い方

1. 対象環境の Snowflake で、`ACCOUNTADMIN` ロールで実行してください。
2. 実行前に RSA 公開鍵プレースホルダを実値へ置き換えてください。
3. 秘密情報（秘密鍵・認証情報）はコミットしないでください。
4. これらの SQL は日次運用用ではなく、初回セットアップ用です。
