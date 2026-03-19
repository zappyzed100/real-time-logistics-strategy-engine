import argparse
import os

import pandas as pd
import numpy as np
from faker import Faker

from generate_random_location import build_generation_context, generate_random_locations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="受注・在庫データを生成する")
    parser.add_argument(
        "--number",
        "-n",
        type=int,
        default=10000,
        help="生成する受注件数 (default: 10000)",
    )
    return parser.parse_args()


def generate_orders(num_records=10000):
    fake = Faker("ja_JP")

    # 既存のマスターデータを読み込んでIDリストを取得
    products_df = pd.read_csv("data/03_seed/products.csv")
    product_ids = products_df["product_id"].tolist()

    names, cumulative, total, points_by_city = build_generation_context()
    locations = generate_random_locations(
        n=num_records,
        names=names,
        cumulative=cumulative,
        total=total,
        points_by_city=points_by_city,
    )

    orders = []
    for i in range(1, num_records + 1):
        lat = float(locations[i - 1]["lat"])
        lon = float(locations[i - 1]["lon"])

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
    products_df = pd.read_csv("data/03_seed/products.csv")
    centers_df = pd.read_csv("data/03_seed/logistics_centers.csv")

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
    args = parse_args()
    if args.number <= 0:
        raise ValueError("number は 1 以上を指定してください")

    os.makedirs("data/04_out", exist_ok=True)

    print(f"Generating {args.number:,} orders...")
    orders_df = generate_orders(args.number)
    orders_df.to_csv("data/04_out/orders.csv", index=False)

    print("Generating full inventory matrix...")
    inventory_df = generate_inventory()
    inventory_df.to_csv("data/04_out/inventory.csv", index=False)

    print("Done. Files saved to data/04_out/ directory.")


if __name__ == "__main__":
    main()
