# データガバナンス定義書 (Data Governance Policy)

このドキュメントはルート参照用の正規エントリです。実装詳細は `docs/GOVERNANCE.md` を一次情報とし、ここでは方針を要約します。

## 1. アクセス制御方針 (Access Control Policy)

### RBAC (Role-Based Access Control)

本プロジェクトではロールベースアクセス制御を採用し、以下の階層で権限を管理します。

- ACCOUNTADMIN: システム全体管理（緊急時のみ）
- SYSADMIN: DB/WH 等の所有者ロール
- SECURITYADMIN: ユーザー・ロール管理
- `<ENV>_TF_ADMIN_ROLE`: Terraform 実行専用ロール
- `<ENV>_READ_ONLY_ROLE`, `<ENV>_READ_WRITE_ROLE`: 中間ポリシーロール
- `<ENV>_BRONZE_LOADER_RW_ROLE` などの data-layer access role

### 最小権限の原則 (Principle of Least Privilege)

- 実行主体には必要最小権限のみを付与する
- schema は managed access 前提で運用し、権限変更は Terraform 管理に統一する

## 2. データ保護方針 (Data Protection Policy)

### Time Travel (データ保持期間)

- PROD: `DATA_RETENTION_TIME_IN_DAYS = 90`
- DEV: `DATA_RETENTION_TIME_IN_DAYS = 7`

この設定は bootstrap SQL で DB ごとに適用します。

### 削除保護 (Destruction Protection)

`prevent_destroy = true` を critical resource に適用します。

- account role
- user
- warehouse
- bronze stage
- bronze raw tables
- file format

## 3. 命名規則 (Naming Conventions)

- Database: `{ENV}_{SYSTEM_NAME}_{LAYER}_DB`
- Schema: 大文字アンダースコア区切り
- Role: `{ENV}_{FUNCTION}_ROLE`

## 4. ネットワークセキュリティ

### 接続元制限 (Network Policy)

- Terraform モジュールで `<ENV>_TERRAFORM_NETWORK_POLICY` を定義し、service users に適用する
- bootstrap SQL で Terraform 実行ユーザー (`<ENV>_TFRUNNER_USER`) に network policy を適用する
- 許可 CIDR は HCP Terraform 公開レンジと社内固定IPを使用する

## 5. 実装参照

- `docs/GOVERNANCE.md`
- `terraform/modules/snowflake_env/main.tf`
- `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
- `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
