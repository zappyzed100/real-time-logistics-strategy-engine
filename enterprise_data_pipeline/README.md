# enterprise_data_pipeline

この dbt project は Snowflake の Bronze/Silver/Gold 構成を前提にしています。

## 接続方法

`profiles.yml` は `.env` の RSA 秘密鍵を使って dbt ユーザーで接続します。

必要な主な環境変数:
- `SNOWFLAKE_ACCOUNT`
- `DEV_DBT_USER_RSA_PRIVATE_KEY`
- `SNOWFLAKE_DBT_USER` 省略時は `DEV_DBT_USER`
- `SNOWFLAKE_DBT_ROLE` 省略時は `DEV_DBT_ROLE`
- `SNOWFLAKE_DBT_WAREHOUSE` 省略時は `DEV_DBT_WH`
- `SNOWFLAKE_BRONZE_DATABASE` 省略時は `DEV_BRONZE_DB`
- `SNOWFLAKE_SILVER_DATABASE` 省略時は `DEV_SILVER_DB`
- `SNOWFLAKE_GOLD_DATABASE` 省略時は `DEV_GOLD_DB`

## 実行方法

`.env` を読み込んだうえで dbt を起動するため、以下のラッパー経由で実行します。

```bash
uv run python src/scripts/deploy/run_dbt.py debug
uv run python src/scripts/deploy/run_dbt.py run
uv run python src/scripts/deploy/run_dbt.py test
```

## モデル構成

- `models/staging`: Bronze `RAW_DATA` から Silver `CLEANSED` へ型変換
- `models/intermediate/int_delivery_cost_candidates.sql`: 配送コストの Pure SQL 計算
- `models/marts/fct_delivery_analysis.sql`: 注文ごとの最安配送候補を Gold `MARKETING_MART` に公開
