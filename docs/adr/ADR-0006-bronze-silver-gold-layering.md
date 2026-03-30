# ADR-0006: Bronze/Silver/Gold レイヤ分割でデータ品質段階を管理する

- Status: Accepted
- Date: 2026-03-30
- Deciders: data-platform team

## Context

単一のテーブル構成ではデータの品質段階が追跡しにくく、分析時のデータ信頼性が低下する。
またデータクレンジングロジックが分散すると保守性が落ちる。

## Decision

- Snowflake 内で 3 つのレイヤを分離する：
  - **Bronze** (`*_BRONZE_DB`): 生データ取り込み層
    - 外部ソースから PUT/COPY で受け入れたデータをそのまま格納
    - スキーマは STRING 型を多用して、入力形式の変動に耐える
  - **Silver** (`*_SILVER_DB`): データ品質・クレンジング層
    - Bronze から取得したデータの型変換・バリデーション・正規化を実施
    - dbt で実装し、テスト・ドキュメント化
  - **Gold** (`*_GOLD_DB`): ビジネスロジック・ マート層
    - Silver で整形されたデータを用い、ビジネス分析向けマート構築
    - ダッシュボード・可視化の直下 Tables として利用

## Consequences

- データ品質段階が明確になり、障害時の影響範囲特定が容易
- 段階ごとの SLA・テスト・ガバナンスルール設定が可能
- 3 層分のストレージ・コンピュート料金が発生
- ETL/ELT ロジックがレイヤ単位で分割され、責任分解が明確
- dbt モデル群が複数ディレクトリに分散するため、ドキュメント・整理が重要

## Implementation References

- `terraform/modules/snowflake_env/main.tf`
- `src/transform/models/staging/` (Bronze → Silver)
- `src/transform/models/intermediate/` (Silver → Gold 中間層)
- `src/transform/models/marts/` (Gold マート層)
- `terraform/README.md`
