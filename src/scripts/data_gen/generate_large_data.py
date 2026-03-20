import argparse
import csv
import os
from datetime import datetime

import pandas as pd
import numpy as np

from src.utils.geospatial import build_generation_context, generate_random_locations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="受注・在庫データを生成する")
    parser.add_argument(
        "--number",
        "-n",
        type=int,
        default=10000,
        help="生成する受注件数 (default: 10000)",
    )
    parser.add_argument(
        "--geo-mode",
        choices=["lite", "strict"],
        default="lite",
        help="位置生成に使う中間データの種別 (default: lite)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100000,
        help="orders.csv を分割生成するチャンクサイズ (default: 100000)",
    )
    return parser.parse_args()


def _generate_order_dates(num_records: int) -> list[str]:
    today = datetime.now().date().isoformat()
    seconds = np.random.randint(0, 24 * 60 * 60, size=num_records)

    return [
        f"{today} {sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"
        for sec in seconds
    ]


def write_orders_csv(num_records=10000, geo_mode="lite", chunk_size=100000):
    # 既存のマスターデータを読み込んでIDリストを取得
    products_df = pd.read_csv("data/03_seed/products.csv")
    product_ids = products_df["product_id"].to_numpy()

    names, cumulative, total, points_by_city = build_generation_context(geo_mode)

    output_path = "data/04_out/orders.csv"
    total_written = 0
    next_order_id = 1001

    with open(output_path, "w", encoding="utf-8", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "order_id",
                "product_id",
                "quantity",
                "customer_lat",
                "customer_lon",
                "order_date",
            ]
        )

        remaining = num_records
        while remaining > 0:
            current_chunk = min(chunk_size, remaining)

            locations = generate_random_locations(
                n=current_chunk,
                names=names,
                cumulative=cumulative,
                total=total,
                points_by_city=points_by_city,
            )

            chunk_product_ids = np.random.choice(product_ids, size=current_chunk)
            chunk_quantities = np.random.randint(1, 10, size=current_chunk)
            chunk_dates = _generate_order_dates(current_chunk)

            rows = []
            for i, location in enumerate(locations):
                rows.append(
                    [
                        next_order_id + i,
                        int(chunk_product_ids[i]),
                        int(chunk_quantities[i]),
                        float(location["lat"]),
                        float(location["lon"]),
                        chunk_dates[i],
                    ]
                )

            writer.writerows(rows)

            total_written += current_chunk
            next_order_id += current_chunk
            remaining -= current_chunk
            print(f"  orders progress: {total_written:,}/{num_records:,}")

    print(f"Orders CSV generated: {output_path} ({total_written:,} rows)")


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
    if args.chunk_size <= 0:
        raise ValueError("chunk-size は 1 以上を指定してください")

    os.makedirs("data/04_out", exist_ok=True)

    print(
        f"Generating {args.number:,} orders (geo-mode={args.geo_mode}, chunk-size={args.chunk_size:,})..."
    )
    write_orders_csv(args.number, geo_mode=args.geo_mode, chunk_size=args.chunk_size)

    print("Generating full inventory matrix...")
    inventory_df = generate_inventory()
    inventory_df.to_csv("data/04_out/inventory.csv", index=False)

    print("Done. Files saved to data/04_out/ directory.")


if __name__ == "__main__":
    main()
