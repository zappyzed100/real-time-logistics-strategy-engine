-- 使用環境の指定
USE WAREHOUSE OPTIMIZER_WH;
USE DATABASE OPTIMIZER_DB;
USE SCHEMA PUBLIC;

-- 0) 任意: 実行前にウォームアップしたい場合は同クエリを1回流す

-- 1) ベンチ対象クエリ（Pure SQL）
SELECT
  o."ORDER_ID",
  (
    6371 * 2 * ASIN(
      SQRT(
        POWER(SIN(RADIANS((o."CUSTOMER_LAT" - lc."LATITUDE") / 2)), 2) +
        COS(RADIANS(lc."LATITUDE")) * COS(RADIANS(o."CUSTOMER_LAT")) *
        POWER(SIN(RADIANS((o."CUSTOMER_LON" - lc."LONGITUDE") / 2)), 2)
      )
    )
  ) * p."WEIGHT_KG" * 10.0 AS "DELIVERY_COST"
FROM "ORDERS" o
JOIN "PRODUCTS" p
  ON o."PRODUCT_ID" = p."PRODUCT_ID"
CROSS JOIN "LOGISTICS_CENTERS" lc;

-- 2) 直前クエリIDを保存（ここは必ずベンチクエリ直後）
SET BENCH_QID = (SELECT LAST_QUERY_ID());

-- 3) いつもの確認クエリ（これは後で実行してOK）
SELECT * FROM "OPTIMIZER_DB"."PUBLIC"."STG_ORDERS" LIMIT 10;

-- 4) 実行時間とスループットを表示
SELECT
  ROUND(q.total_elapsed_time / 1000.0, 3) AS execution_time_sec,
  ROUND(q.rows_produced / NULLIF(q.total_elapsed_time / 1000.0, 0), 2) AS throughput_rps
FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(RESULT_LIMIT => 100)) q
WHERE q.query_id = $BENCH_QID;