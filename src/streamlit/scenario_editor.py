from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.simulation import CenterScenario, SimulationOptions

SCENARIO_COLUMNS = [
    "center_id",
    "center_name",
    "center_lat",
    "center_lon",
    "shipping_cost",
    "baseline_order_count",
    "staffing_level",
    "fixed_cost",
]
EDITABLE_SCENARIO_COLUMNS = ["staffing_level", "fixed_cost"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_center_master_data(
    logistics_centers_path: Path | None = None,
    shipping_costs_path: Path | None = None,
) -> pd.DataFrame:
    root = project_root()
    logistics_path = logistics_centers_path or root / "data/03_seed/logistics_centers.csv"
    shipping_path = shipping_costs_path or root / "data/03_seed/shipping_costs.csv"

    logistics_centers = pd.read_csv(logistics_path).rename(columns=str.lower)
    shipping_costs = pd.read_csv(shipping_path).rename(columns=str.lower)

    center_master = logistics_centers.merge(
        shipping_costs[["center_id", "shipping_cost"]],
        on="center_id",
        how="left",
        validate="one_to_one",
    )
    center_master = center_master.rename(columns={"latitude": "center_lat", "longitude": "center_lon"})
    center_master["center_id"] = center_master["center_id"].astype(str)
    return center_master[["center_id", "center_name", "center_lat", "center_lon", "shipping_cost"]].sort_values(
        by=["center_name", "center_id"]
    )


def build_initial_scenario_frame(
    analysis_df: pd.DataFrame,
    options: SimulationOptions,
    logistics_centers_path: Path | None = None,
    shipping_costs_path: Path | None = None,
) -> pd.DataFrame:
    center_master = load_center_master_data(logistics_centers_path, shipping_costs_path)
    normalized_analysis_df = analysis_df.rename(columns=str.upper).copy()

    if "CENTER_NAME" in normalized_analysis_df.columns:
        order_counts = (
            normalized_analysis_df.groupby("CENTER_NAME", dropna=False)
            .size()
            .rename("baseline_order_count")
            .reset_index()
            .rename(columns={"CENTER_NAME": "center_name"})
        )
        center_master = center_master.merge(order_counts, on="center_name", how="left")
    else:
        center_master["baseline_order_count"] = 0

    center_master["baseline_order_count"] = center_master["baseline_order_count"].fillna(0).astype(int)
    center_master["staffing_level"] = (
        (center_master["baseline_order_count"] + options.orders_per_staff - 1) // options.orders_per_staff
    ).astype(int)
    center_master["fixed_cost"] = 0.0
    return center_master[SCENARIO_COLUMNS].copy()


def sanitize_scenario_frame(scenario_df: pd.DataFrame) -> pd.DataFrame:
    sanitized_df = scenario_df.copy()
    sanitized_df["center_id"] = sanitized_df["center_id"].astype(str)
    sanitized_df["center_name"] = sanitized_df["center_name"].astype(str)
    sanitized_df["center_lat"] = pd.to_numeric(sanitized_df["center_lat"], errors="coerce").fillna(0.0)
    sanitized_df["center_lon"] = pd.to_numeric(sanitized_df["center_lon"], errors="coerce").fillna(0.0)
    sanitized_df["shipping_cost"] = pd.to_numeric(sanitized_df["shipping_cost"], errors="coerce").fillna(1.0)
    sanitized_df["baseline_order_count"] = (
        pd.to_numeric(sanitized_df["baseline_order_count"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    )
    sanitized_df["staffing_level"] = (
        pd.to_numeric(sanitized_df["staffing_level"], errors="coerce").fillna(0).clip(lower=0).round().astype(int)
    )
    sanitized_df["fixed_cost"] = pd.to_numeric(sanitized_df["fixed_cost"], errors="coerce").fillna(0.0).clip(lower=0.0)
    return sanitized_df[SCENARIO_COLUMNS].sort_values(by=["center_name", "center_id"]).reset_index(drop=True)


def merge_scenario_frame(existing_df: pd.DataFrame, initial_df: pd.DataFrame) -> pd.DataFrame:
    editable_snapshot = existing_df[["center_id", *EDITABLE_SCENARIO_COLUMNS]].copy()
    editable_snapshot["center_id"] = editable_snapshot["center_id"].astype(str)

    merged_df = initial_df.drop(columns=EDITABLE_SCENARIO_COLUMNS).merge(
        editable_snapshot,
        on="center_id",
        how="left",
    )
    merged_df["staffing_level"] = merged_df["staffing_level"].fillna(initial_df["staffing_level"])
    merged_df["fixed_cost"] = merged_df["fixed_cost"].fillna(initial_df["fixed_cost"])
    return sanitize_scenario_frame(merged_df)


def build_center_scenarios(scenario_df: pd.DataFrame) -> list[CenterScenario]:
    sanitized_df = sanitize_scenario_frame(scenario_df)
    scenario_records = sanitized_df.to_dict(orient="records")
    return [
        CenterScenario(
            center_id=str(row["center_id"]),
            center_name=str(row["center_name"]),
            latitude=float(row["center_lat"]),
            longitude=float(row["center_lon"]),
            shipping_cost=float(row["shipping_cost"]),
            staffing_level=int(row["staffing_level"]),
            fixed_cost=float(row["fixed_cost"]),
        )
        for row in scenario_records
    ]
