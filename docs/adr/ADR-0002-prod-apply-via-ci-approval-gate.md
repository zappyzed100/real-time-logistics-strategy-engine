# ADR-0002: 本番 Terraform apply は CI 承認ゲート経由に限定する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

本番環境への Terraform apply は影響範囲が大きく、個人端末からの直接実行では監査性と統制が不足する。
既存運用では GitHub Actions と Environment 承認を組み合わせたフローを整備している。

## Decision

- `APP_ENV=prod` の Terraform 実行は CI 実行時のみ許可する
- 本番 apply は GitHub Actions の `environment: prod` 承認ゲートを通過したジョブから実行する
- 承認ポイントはパイプライン内で 1 回に集約し、承認後は apply -> loader -> dbt run -> dbt test を自動継続する

## Consequences

- 本番変更の経路が一意化され、監査証跡が残る
- 手動オペレーションのばらつきが減る
- 緊急時にも CI 経路が前提となるため、GitHub 側設定と権限設計の維持が必要になる

## Implementation References

- `.github/workflows/ci.yml`
- `terraform/tf`
- `DEPLOYMENT.md`
- `terraform/README.md`
