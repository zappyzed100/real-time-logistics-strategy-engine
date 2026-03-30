# ADR-0004: 環境差分は app_env と入力変数で吸収し命名を統制する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

dev/prod を別コードで管理すると、変更漏れとドリフトが発生しやすい。
一方、同一コードで環境切り替えを行う場合は、命名値と接続先の注入規約を厳格にする必要がある。

## Decision

- ルートの `terraform/main.tf` では `app_env` を基準に各リソース名を切り替える
- 命名値は `.env.shared` / `.env` に集約し、`terraform/tf` が `TF_VAR_*` と `*.auto.tfvars` を生成して注入する
- 環境差分は変数で扱い、構成ファイルの重複分岐は作らない

## Consequences

- 単一コードベースで dev/prod の整合を取りやすい
- 命名規則と環境変数セットの破損時に実行不能となるため、設定ファイルの管理品質が重要になる
- レビュー時に「変数追加・改名」の影響が広がるため、変更時は ADR とドキュメントの同時更新が必要になる

## Implementation References

- `terraform/main.tf`
- `terraform/variables.tf`
- `terraform/tf`
- `CONTRIBUTING.md`
