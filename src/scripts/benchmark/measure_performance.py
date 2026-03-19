import time
import os
from dotenv import load_dotenv
from snowflake.snowpark import Session
import snowflake.snowpark.functions as F


def run_benchmark():
    load_dotenv()
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }

    session = Session.builder.configs(connection_parameters).create()

    try:
        # 1. 大規模データの読み込み
        # ※#21で作成し、ロード済みの large_orders テーブルを想定
        df_orders = session.table("orders")
        df_centers = session.table("logistics_centers")
        df_products = session.table("products")

        # 2. データのジョイン（注文・商品・拠点を結合して計算に必要な値を揃える）
        # ここでは簡略化のため、特定の条件でジョイン
        df_joined = df_orders.join(df_products, "product_id").join(
            df_centers
        )  # カラム指定なしで join すると cross join 的に動作

        print(f"Total records to process: {df_joined.count()}")

        # 3. パフォーマンス計測開始
        start_time = time.time()

        # UDFの呼び出し（ベクトル演算）
        # UDFの呼び出し
        # F.col(' "COLUMN_NAME" ') の形式で、内側に二重引用符を含める
        df_result = df_joined.select(
            F.col('"ORDER_ID"'),
            F.call_udf(
                "CALCULATE_DELIVERY_COST",
                F.col('"LATITUDE"'),
                F.col('"LONGITUDE"'),
                F.col('"CUSTOMER_LAT"'),
                F.col('"CUSTOMER_LON"'),
                F.col('"WEIGHT_KG"'),
            ).alias("DELIVERY_COST"),
        )

        # 結果を評価（実際にアクションを起こして計算を走らせる）
        final_results = df_result.collect()

        end_time = time.time()

        duration = end_time - start_time
        print("--- Benchmark Results ---")
        print(f"Execution Time: {duration:.2f} seconds")
        print(f"Throughput: {len(final_results) / duration:.2f} records/sec")
        print("--------------------------")

    finally:
        session.close()


if __name__ == "__main__":
    run_benchmark()
