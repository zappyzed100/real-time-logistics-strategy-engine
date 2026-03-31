# ADR-0008: Snowflake の network policy と data retention を環境別に標準化する

- Status: Accepted
- Date: 2026-03-31
- Deciders: data-platform team

## Context

Snowflake への接続元制御とデータ保持期間について、環境ごとの差分が明文化されておらず、手動運用に依存する余地があった。
特に Terraform 実行経路と service users の接続元制限、DEV/PROD の保持期間差分は監査観点で明確化が必要だった。

## Decision

- `<ENV>_TERRAFORM_NETWORK_POLICY` を Terraform モジュールで定義し、service users（loader/dbt/streamlit）へ適用する
- Terraform 実行ユーザー（`<ENV>_TFRUNNER_USER`）への network policy 適用は bootstrap SQL で管理する
- `DATA_RETENTION_TIME_IN_DAYS` を DB 単位で DEV=7 / PROD=90 に固定する
- 許可 CIDR は環境ごとに異なる方針とする:
  - **DEV**: `0.0.0.0/0`（全許可）— 開発者のローカル IP が固定されないため IP 制限を設けない
  - **PROD**: GitHub Actions ランナーの固定 IP のみ許可（`terraform/common.auto.tfvars` の `PROD_NETWORK_POLICY_ALLOWED_IPS` で管理）

## Consequences

- 許可 CIDR と保持期間の運用基準がコード化される
- 接続元制御の更新時に Terraform Variables と bootstrap SQL の同時更新が必要になる
- Storage Integration を未使用の間は、該当リソース保護は将来課題として残る

## Implementation References

- `terraform/modules/snowflake_env/main.tf`
- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
- `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
- `docs/GOVERNANCE.md`
- `GOVERNANCE.md`
