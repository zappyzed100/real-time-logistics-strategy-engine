from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

DEFAULT_INPUT_PATH = Path("data/01_raw/estat/prefecture_population_density.csv")
DEFAULT_OUTPUT_PATH = Path("data/03_seed/shipping_costs.csv")
MIN_SHIPPING_COST = 1.0
MAX_SHIPPING_COST = 2.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="人口密度データから shipping_costs.csv を生成する")
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="入力元の人口密度 CSV パス",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="出力先の shipping_costs.csv パス",
    )
    return parser.parse_args()


def calculate_log_density(density: float) -> float:
    if density <= 0:
        raise ValueError(f"density must be positive: {density}")
    return math.log(density)


def scale_log_density_to_shipping_cost(
    log_density: float,
    min_log_density: float,
    max_log_density: float,
    min_shipping_cost: float = MIN_SHIPPING_COST,
    max_shipping_cost: float = MAX_SHIPPING_COST,
) -> float:
    if max_log_density == min_log_density:
        return round((min_shipping_cost + max_shipping_cost) / 2, 6)

    normalized = (log_density - min_log_density) / (max_log_density - min_log_density)
    shipping_cost = min_shipping_cost + normalized * (max_shipping_cost - min_shipping_cost)
    return round(shipping_cost, 6)


def generate_shipping_costs(input_path: Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    density_df = pd.read_csv(input_path)

    required_columns = {"center_id", "center_name", "density"}
    missing_columns = required_columns - set(density_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"入力CSVに必要な列がありません: {missing}")

    shipping_costs_df = density_df[["center_id", "center_name", "density"]].copy()
    shipping_costs_df["log_density"] = shipping_costs_df["density"].map(calculate_log_density)

    min_log_density = shipping_costs_df["log_density"].min()
    max_log_density = shipping_costs_df["log_density"].max()
    shipping_costs_df["shipping_cost"] = shipping_costs_df["log_density"].map(
        lambda value: scale_log_density_to_shipping_cost(
            value,
            min_log_density=min_log_density,
            max_log_density=max_log_density,
        )
    )

    return shipping_costs_df[["center_id", "center_name", "shipping_cost"]].sort_values("center_id").reset_index(drop=True)


def save_shipping_costs(df: pd.DataFrame, output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    shipping_costs_df = generate_shipping_costs(input_path=input_path)
    save_shipping_costs(shipping_costs_df, output_path=output_path)
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
