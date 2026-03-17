import os
from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.snowpark.types import FloatType, PandasSeriesType
from src.udf.delivery_cost_calculator import calculate_delivery_cost_vec


def create_session():
    # 環境変数または直接指定で接続情報を取得
    load_dotenv()
    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }
    return Session.builder.configs(connection_parameters).create()


def deploy_udf(session: Session):
    print("Registering Vectorized UDF: CALCULATE_DELIVERY_COST...")

    # ローカルの src ディレクトリの絶対パスを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.abspath(os.path.join(current_dir, ".."))  # src フォルダを指す

    # Vectorized UDF として登録
    # input_types: [拠点緯度, 拠点経度, 顧客緯度, 顧客経度, 重量]
    # PandasSeriesType を使うことで、Snowflake側でバッチ処理が行われる
    session.udf.register(
        func=calculate_delivery_cost_vec,
        name="CALCULATE_DELIVERY_COST",
        input_types=[
            PandasSeriesType(FloatType()),
            PandasSeriesType(FloatType()),
            PandasSeriesType(FloatType()),
            PandasSeriesType(FloatType()),
            PandasSeriesType(FloatType()),
        ],
        return_type=PandasSeriesType(FloatType()),
        packages=["pandas", "numpy==2.4.2"],
        imports=[src_path],
        is_permanent=True,
        stage_location="@UDF_STAGE",  # 事前に作成したステージを指定
        replace=True,
    )
    print("UDF registration complete.")


if __name__ == "__main__":
    session = create_session()
    try:
        deploy_udf(session)
    finally:
        session.close()
