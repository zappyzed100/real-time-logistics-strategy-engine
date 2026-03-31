# ADR-0007: Snowflake の権限モデルを managed access と削除保護へ移行する

- Status: Accepted
- Date: 2026-03-31
- Deciders: data-platform team

## Context

これまでの Terraform 運用では、Snowflake の主要リソースで `prevent_destroy = false` を維持し、functional role に直接オブジェクト権限を付与していた。
この構成は bootstrap フェーズでは有効だったが、本番運用を見据えると以下の課題がある。

- 環境を問わず critical resource の誤削除リスクを継続管理したい
- functional role に権限が集中し、責務境界と監査観点が曖昧になる
- managed access schema を前提にした grant 統制が明文化されていない

## Decision

- Bronze / Silver / Gold schema は bootstrap SQL で managed access を有効化する
- Terraform では `READ_ONLY_ROLE` / `READ_WRITE_ROLE` の中間ロールと data-layer access role を組み合わせた RBAC 階層を採用する
- schema object grant はサブモジュール化し、`permission_level` (`SELECT` / `ALL`) の変数で制御する
- `prevent_destroy = true` は Bronze raw tables に限定して適用する

## Consequences

- Bronze raw tables の誤削除耐性が向上する
- 権限付与の責務が access role に集約され、レビューしやすくなる
- managed access の導入により、schema owner を中心に grant を統制できる
- 既存環境へ適用する際は bootstrap SQL の再実行または差分適用が必要になる

## Implementation References

- `terraform/modules/snowflake_env/main.tf`
- `terraform/modules/snowflake_env/modules/schema_object_grants/main.tf`
- `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
- `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
- `terraform/README.md`
- `docs/GOVERNANCE.md`
