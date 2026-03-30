# DECISIONS

このドキュメントは、本プロジェクトの重要な設計判断を ADR (Architecture Decision Record) として管理するための入口です。

## 1. 目的

- なぜその設計にしたのかを、実装と紐づけて追跡できるようにする
- 将来の変更時に、判断の前提とトレードオフを再利用できるようにする
- レビュー時に、実装差分だけでなく設計意図の確認を可能にする

## 2. ADR フォーマット

各 ADR は `docs/adr/` 配下に 1 ファイルずつ作成し、以下の形式を採用します。

### 2.1 必須ヘッダ

- `# ADR-XXXX: タイトル`
- `- Status: Proposed | Accepted | Superseded`
- `- Date: YYYY-MM-DD`
- `- Deciders: @team or role`

### 2.2 必須セクション

- `## Context`
- `## Decision`
- `## Consequences`
- `## Implementation References`

`Implementation References` には、該当実装ファイルのパスを必ず記載します。

## 3. 運用ルール

- 重要設計の変更を伴う PR では、同一 PR で ADR を追加または更新する
- 既存判断を変更する場合は、既存 ADR を上書きせず、新しい ADR を追加して `Superseded` を明記する
- 破壊的変更、権限モデル変更、実行経路変更 (ローカル可否や本番ガード) は ADR 対象とする

## 4. ADR 一覧

| ID | Title | Status | Date | File |
| --- | --- | --- | --- | --- |
| ADR-0001 | HCP Terraform Remote Backend を標準化する | Accepted | 2026-03-30 | `docs/adr/ADR-0001-hcp-terraform-remote-backend.md` |
| ADR-0002 | 本番 Terraform apply は CI 承認ゲート経由に限定する | Accepted | 2026-03-30 | `docs/adr/ADR-0002-prod-apply-via-ci-approval-gate.md` |
| ADR-0003 | Snowflake リソースの prevent_destroy を現段階で false とする | Accepted | 2026-03-30 | `docs/adr/ADR-0003-prevent-destroy-false-bootstrap-phase.md` |
| ADR-0004 | 環境差分は app_env と入力変数で吸収し命名を統制する | Accepted | 2026-03-30 | `docs/adr/ADR-0004-env-switch-and-naming-governance.md` |
| ADR-0005 | Snowflake を Data Platform として採用する | Accepted | 2026-03-30 | `docs/adr/ADR-0005-snowflake-data-platform-adoption.md` |
| ADR-0006 | Bronze/Silver/Gold レイヤ分割でデータ品質段階を管理する | Accepted | 2026-03-30 | `docs/adr/ADR-0006-bronze-silver-gold-layering.md` |
