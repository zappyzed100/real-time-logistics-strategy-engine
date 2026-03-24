-- 使用環境の指定
USE WAREHOUSE DEV_DBT_WH;
USE DATABASE DEV_SILVER_DB;
USE SCHEMA CLEANSED;

-- 0) 任意: 実行前にウォームアップしたい場合は同クエリを1回流す

-- 1) ベンチ対象クエリ（dbt の Pure SQL モデルをそのまま評価）
-- enterprise_data_pipeline/models/intermediate/int_delivery_cost_candidates.sql を
-- Silver の view として実行するため、dbt 本体と同じ SQL を測定できる。
SELECT
  ORDER_ID,
  DELIVERY_COST
FROM INT_DELIVERY_COST_CANDIDATES;

-- 2) 直前クエリIDを保存（ここは必ずベンチクエリ直後）
SET BENCH_QID = (SELECT LAST_QUERY_ID());

-- 3) いつもの確認クエリ（これは後で実行してOK）
SELECT * FROM DEV_GOLD_DB.MARKETING_MART.FCT_DELIVERY_ANALYSIS LIMIT 10;

-- 4) 実行時間とスループットを表示
SELECT
  ROUND(q.total_elapsed_time / 1000.0, 3) AS execution_time_sec,
  ROUND(q.rows_produced / NULLIF(q.total_elapsed_time / 1000.0, 0), 2) AS throughput_rps
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 100)) q
WHERE q.query_id = $BENCH_QID;