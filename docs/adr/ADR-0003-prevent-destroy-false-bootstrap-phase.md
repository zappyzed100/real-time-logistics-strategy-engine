# ADR-0003: Snowflake リソースの prevent_destroy を現段階で false とする

- Status: Superseded
- Date: 2026-03-30
- Deciders: data-platform team

Superseded by: ADR-0007

## Context

本プロジェクトは構築・検証フェーズであり、Snowflake リソースの再作成を伴う試行錯誤が継続している。
`prevent_destroy = true` を広範囲に適用すると、検証時の再構築速度が低下し、運用負荷が増える。

## Decision

- `terraform/modules/snowflake_env/main.tf` の主要リソースでは、現時点で `lifecycle.prevent_destroy = false` を採用する
- 破壊的変更を行う PR では、影響範囲・復旧手順・再有効化条件を必ず記載する
- 本番安定化フェーズで、重要リソースから段階的に `true` へ移行する方針を維持する

## Consequences

- 開発・検証時の反復速度を確保できる
- 誤削除リスクは残るため、レビューと承認ゲートで補完する必要がある
- 将来の運用フェーズ移行時に、保護設定の再評価タスクが必要になる

## Implementation References

- `terraform/modules/snowflake_env/main.tf`
- `terraform/README.md`
- `CONTRIBUTING.md`
