import pandas as pd
import numpy as np
from faker import Faker
import os


def generate_orders(num_records=10000):
    fake = Faker("ja_JP")

    # 既存のマスターデータを読み込んでIDリストを取得
    products_df = pd.read_csv("data/products.csv")
    product_ids = products_df["product_id"].tolist()

    orders = []
    for i in range(1, num_records + 1):
        # 日本の範囲に絞って生成
        # latitude: 31.0 to 45.0, longitude: 130.0 to 145.0
        lat = float(fake.coordinate(center=38.0, radius=7.0))
        lon = float(fake.coordinate(center=137.0, radius=7.0))

        orders.append(
            {
                "order_id": i + 1000,
                "product_id": np.random.choice(product_ids),
                "quantity": np.random.randint(1, 10),
                "customer_lat": lat,
                "customer_lon": lon,
                "order_date": fake.date_between(start_date="-1y", end_date="today"),
            }
        )

    return pd.DataFrame(orders)


def generate_inventory():
    # 拠点と商品の全組み合わせに対して在庫を生成
    products_df = pd.read_csv("data/products.csv")
    centers_df = pd.read_csv("data/logistics_centers.csv")

    inventory = []
    for c_id in centers_df["center_id"]:
        for p_id in products_df["product_id"]:
            inventory.append(
                {
                    "center_id": c_id,
                    "product_id": p_id,
                    "stock_quantity": np.random.randint(10, 500),
                }
            )
    return pd.DataFrame(inventory)


def main():
    os.makedirs("data", exist_ok=True)

    print("Generating 10,000 orders...")
    orders_df = generate_orders(10000)
    orders_df.to_csv("data/large_orders.csv", index=False)

    print("Generating full inventory matrix...")
    inventory_df = generate_inventory()
    inventory_df.to_csv("data/large_inventory.csv", index=False)

    print("Done. Files saved to data/ directory.")


if __name__ == "__main__":
    main()
