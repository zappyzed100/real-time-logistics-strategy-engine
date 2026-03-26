import os

from dotenv import load_dotenv
from snowflake.snowpark import Session


def main():
    # .env から環境変数を読み込み
    load_dotenv()

    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }

    # セッションの作成
    print("Snowflakeに接続中...")
    session = Session.builder.configs(connection_parameters).create()

    try:
        # 疎通確認：products テーブルから1件取得
        df = session.table("products").limit(1)
        print("--- 取得データプレビュー ---")
        df.show()
        print("接続テスト成功：正常にデータを取得しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
