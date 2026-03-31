# ADR-0001: HCP Terraform Remote Backend を標準化する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

Snowflake 基盤リソースを複数メンバーで安全に運用するには、Terraform の状態管理をローカルに分散させず、一貫した実行基盤を持つ必要がある。
また、環境ごとにワークスペースを分離し、実行主体の認可情報を統制する必要がある。

## Decision

- Terraform の backend は HCP Terraform (Remote Backend) を標準とする
- 実行は Terraform CLI を標準経路とし、backend ファイルと環境変数で Organization / Workspace / Token を統一する
- `dev` / `prod` は HCP Terraform の別ワークスペースにマッピングする
- 現在の課金レベルは Essentials とし、Project 単位の Team 権限制御で Terraform 実行権限をチーム境界で管理する（Essentials 以上）

## Consequences

- 実行者ごとのローカル state 差異を回避できる
- backend 設定と認証注入の手順が一本化される（Free でも可）
- Project 単位の Team 権限制御により、権限管理の統制がしやすくなる（Essentials 以上）
- Workspace の Runs 画面で、実行履歴（実行者、起点、時刻、イベントタイムライン、plan/apply 出力）を確認できる（Free でも可）
- 本リポジトリは Terraform CLI + backend ファイルで HCP Terraform Remote Backend を利用し、CI 実行分を含む run 履歴を HCP Terraform 側で追跡する
- Terraform 全般で設定不備は plan/apply の失敗要因となる。加えて本構成では HCP Terraform の可用性、Organization / Workspace / Token 設定に依存するため、これらの不備時は plan/apply が停止する
- Essentials を解約して Free へ移行した場合、Project 単位の Team 権限制御は利用できなくなるため、権限設計の見直しが必要になる

## Implementation References

- `terraform/providers.tf`
- `terraform/backend.dev.hcl`
- `terraform/backend.prod.hcl`
- `terraform/README.md`
- `README.md`
