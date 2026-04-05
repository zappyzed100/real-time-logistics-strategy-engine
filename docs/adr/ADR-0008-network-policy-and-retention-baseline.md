# ADR-0008: Snowflake の data retention を環境別に標準化し、network policy の適用範囲を限定する

- Status: Accepted
- Date: 2026-03-31
- Deciders: data-platform team

## Context

Snowflake への接続制御とデータ保持期間について、環境ごとの差分が明文化されておらず、手動運用に依存する余地があった。
特に DEV/PROD の保持期間差分と、network policy を適用できる経路の現実的な範囲は監査観点で明確化が必要だった。

## Decision

- Snowflake service users / Terraform 実行ユーザーに対して、IP allowlist 前提の network policy は標準運用に組み込まない
- 接続保護は JWT/RSA 鍵認証と GitHub Environment 承認フローで担保する
- `DATA_RETENTION_TIME_IN_DAYS` を DB 単位で DEV=7 / PROD=90 に固定する

## Consequences

- 保持期間の運用基準がコード化される
- 実現不能な IP 制限前提を IaC/ドキュメントから除去できる
- Storage Integration を未使用の間は、該当リソース保護は将来課題として残る

## Implementation References

- `terraform/modules/snowflake_env/main.tf`
- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
- `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
- `docs/GOVERNANCE.md`
- `GOVERNANCE.md`
