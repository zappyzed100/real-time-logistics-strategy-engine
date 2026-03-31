# ADR-0004: 環境差分は app_env と入力変数で吸収し命名を統制する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

dev/prod を別コードで管理すると、変更漏れとドリフトが発生しやすい。
一方、同一コードで環境切り替えを行う場合は、命名値と接続先の注入規約を厳格にする必要がある。

## Decision

- ルートの `terraform/main.tf` では `app_env` を基準に各リソース名を切り替える
- 非機密の Terraform 設定値は `terraform/common.auto.tfvars` に集約し、backend 選択は `backend.*.hcl` と実行コマンドで明示する
- 環境差分は変数で扱い、構成ファイルの重複分岐は作らない

## Consequences

- 単一コードベースで dev/prod の整合を取りやすい
- tfvars と backend ファイルが Terraform の正本になるため、`.env.shared` と責務が混ざらない
- レビュー時に「変数追加・改名」の影響が広がるため、変更時は ADR とドキュメントの同時更新が必要になる

## Implementation References

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/backend.dev.hcl`
- `terraform/backend.prod.hcl`
- `CONTRIBUTING.md`
