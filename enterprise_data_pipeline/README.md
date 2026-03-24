# enterprise_data_pipeline (dbt運用ガイド)

この README は、初めてこのリポジトリを見る人が「何を実装したのか」を理解し、ローカルから再現実行できるようにするための dbt 専用ガイドです。

## 1. この実装で何が変わったか

本プロジェクトの dbt は、以下を前提に動きます。

1. Snowflake の Medallion 構成
- Bronze: `DEV_BRONZE_DB.RAW_DATA` (生データ)
- Silver: `DEV_SILVER_DB.CLEANSED` (型変換・クレンジング)
- Gold: `DEV_GOLD_DB.MARKETING_MART` (分析用公開層)

2. 接続方式
- dbt の接続はパスワードではなく RSA 鍵認証を使用
- `.env` を直接 dbt が読むのではなく、`src/scripts/deploy/run_dbt.py` が `.env` を読んで dbt を起動

3. 配送コスト計算
- 以前の Python UDF 依存をやめ、Pure SQL に移行
- `models/intermediate/int_delivery_cost_candidates.sql` で Haversine 計算を実施
- `models/marts/fct_delivery_analysis.sql` で注文ごとに最安配送候補を選定

4. スキーマ名の安定化
- `macros/generate_schema_name.sql` で schema 名の連結挙動を固定
- `CLEANSED_CLEANSED` のような意図しないスキーマ生成を防止

## 2. ディレクトリの見方

- `dbt_project.yml`: モデルの materialization と DB/schema 配置
- `profiles.yml`: Snowflake 接続設定 (RSA 鍵認証)
- `models/staging/`: Bronze 取り込みテーブルを型安全に Silver 化
- `models/intermediate/`: ドメインロジック中間層
- `models/marts/`: ユースケース向け最終公開モデル
- `macros/generate_schema_name.sql`: schema 命名挙動の上書き

## 3. 事前準備

リポジトリルートで作業します。

### 3.1 Python 依存関係

```bash
uv sync
```

### 3.2 Terraform 側の反映

Snowflake ロール・DB・権限が未反映だと dbt 実行時に権限エラーになります。

```bash
cd terraform
terraform apply
cd ..
```

### 3.3 必須環境変数

`.env` には最低限以下を設定します。

- `SNOWFLAKE_ACCOUNT`
- `DEV_DBT_USER_RSA_PRIVATE_KEY` (PEM 本文、`\n` エスケープ可)

必要に応じて上書きできる変数。

- `SNOWFLAKE_DBT_USER` (既定: `DEV_DBT_USER`)
- `SNOWFLAKE_DBT_ROLE` (既定: `DEV_DBT_ROLE`)
- `SNOWFLAKE_DBT_WAREHOUSE` (既定: `DEV_DBT_WH`)
- `SNOWFLAKE_BRONZE_DATABASE` (既定: `DEV_BRONZE_DB`)
- `SNOWFLAKE_SILVER_DATABASE` (既定: `DEV_SILVER_DB`)
- `SNOWFLAKE_GOLD_DATABASE` (既定: `DEV_GOLD_DB`)

## 4. 最短実行手順

`.env` を読み込むため、dbt は必ずラッパー経由で実行します。

```bash
uv run python src/scripts/deploy/run_dbt.py debug
uv run python src/scripts/deploy/run_dbt.py parse
uv run python src/scripts/deploy/run_dbt.py run --select +int_delivery_cost_candidates +fct_delivery_analysis
uv run python src/scripts/deploy/run_dbt.py test
```

期待値。

- `run`: 5 モデル成功
- `test`: 10 テスト成功

## 5. モデル詳細

### 5.1 staging 層

対象ファイル。

- `models/staging/stg_orders.sql`
- `models/staging/stg_products.sql`
- `models/staging/stg_logistics_centers.sql`

主な役割。

- Bronze の STRING 列を `TRY_TO_*` で安全に型変換
- 変換失敗時のクエリ停止を避け、下流モデルの安定性を確保

### 5.2 intermediate 層

対象ファイル。

- `models/intermediate/int_delivery_cost_candidates.sql`

主な役割。

- 注文 × 物流拠点の候補組み合わせを生成
- Haversine で距離を算出し、配送コストを Pure SQL で計算

### 5.3 marts 層

対象ファイル。

- `models/marts/fct_delivery_analysis.sql`

主な役割。

- `int_delivery_cost_candidates` から注文ごとの最安候補を 1 件選択
- Gold 層の分析用ビューとして公開

## 6. よくあるエラーと対処

1. `Insufficient privileges to operate on database ...`
- 原因: Snowflake 権限未反映
- 対処: `terraform apply` を実行し、DB 権限 (`USAGE`, `CREATE SCHEMA`) を反映

2. `InvalidByte(0, 92)` など秘密鍵関連エラー
- 原因: `.env` の鍵改行が正規化されていない
- 対処: `run_dbt.py` 経由で実行する (手動で `dbt` を直実行しない)

3. `Object ... does not exist or not authorized`
- 原因: 上流モデル未作成で下流モデルだけ実行
- 対処: `--select +モデル名` で依存モデルも同時実行

## 7. 運用ルール

1. dbt 実行は常に `run_dbt.py` 経由
2. モデル追加時は `schema.yml` の test を同時に追加
3. SQL ロジック変更時は `run` と `test` を必ず再実行
4. DB/schema を変える変更は Terraform と dbt 設定を同時に見直す
