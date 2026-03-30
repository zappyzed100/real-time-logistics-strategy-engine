# ADR-0005: Snowflake を Data Platform として採用する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

本プロジェクトでは複数のデータソース（外部 API、ファイル等）を統合し、リアルタイムで分析・可視化する必要がある。
そのため、スケーラブルで保守しやすいデータ基盤を選定する必要がある。

## Decision

- Data Platform の基盤として Snowflake を採用する
- 理由：
  - マネージド SaaS で初期構築と運用負荷が低い
  - スケーラビリティ（ストレージと計算を独立スケール可能）
  - Data Sharing など企業向け機能が豊富
  - dbt, Python, SQL など複数のツール/言語に対応
  - クエリ最適化が優れており、分析パフォーマンスが高い

## Consequences

- Snowflake の利用料金が増加する（リソース利用に応じた従量課金）
- Snowflake 固有の設定・API・権限管理の学習が必要
- Terraform + Snowflake provider で IaC により環境構築・管理が統一される
- SQL 方言（特に拡張関数等）への適応が必要な場合がある

## Implementation References

- `terraform/bootstrap/sql/`
- `terraform/modules/snowflake_env/`
- `src/infrastructure/snowflake_loader.py`
- `terraform/README.md`
