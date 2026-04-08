import pandas as pd

from src.simulation import SimulationOptions
from src.streamlit.scenario_editor import (
    build_center_scenarios,
    build_initial_scenario_frame,
    merge_scenario_frame,
    sanitize_scenario_frame,
)


def test_build_initial_scenario_frame_loads_all_centers_from_seed_files(tmp_path):
    logistics_centers_path = tmp_path / "logistics_centers.csv"
    logistics_centers_path.write_text(
        "center_id,center_name,latitude,longitude\n1,Tokyo,35.68,139.76\n2,Osaka,34.69,135.50\n",
        encoding="utf-8",
    )
    shipping_costs_path = tmp_path / "shipping_costs.csv"
    shipping_costs_path.write_text(
        "center_id,center_name,shipping_cost\n1,Tokyo,1.5\n2,Osaka,1.2\n",
        encoding="utf-8",
    )
    analysis_df = pd.DataFrame({"CENTER_NAME": ["Tokyo", "Tokyo", "Osaka"]})

    scenario_df = build_initial_scenario_frame(
        analysis_df=analysis_df,
        options=SimulationOptions(orders_per_staff=2),
        logistics_centers_path=logistics_centers_path,
        shipping_costs_path=shipping_costs_path,
    )

    assert list(scenario_df["center_id"]) == ["1", "2"]
    assert list(scenario_df["center_name"]) == ["Tokyo", "Osaka"]
    assert list(scenario_df["baseline_order_count"]) == [2, 1]
    assert list(scenario_df["staffing_level"]) == [1, 1]
    assert list(scenario_df["fixed_cost"]) == [0.0, 0.0]


def test_sanitize_scenario_frame_clamps_invalid_values():
    dirty_df = pd.DataFrame(
        {
            "center_id": ["1"],
            "center_name": ["Tokyo"],
            "center_lat": [35.68],
            "center_lon": [139.76],
            "shipping_cost": [1.5],
            "baseline_order_count": [-4],
            "staffing_level": [-2.4],
            "fixed_cost": [-1000],
        }
    )

    sanitized_df = sanitize_scenario_frame(dirty_df)

    assert sanitized_df.loc[0, "baseline_order_count"] == 0
    assert sanitized_df.loc[0, "staffing_level"] == 0
    assert sanitized_df.loc[0, "fixed_cost"] == 0.0


def test_merge_scenario_frame_preserves_existing_editable_values():
    initial_df = pd.DataFrame(
        {
            "center_id": ["1", "2"],
            "center_name": ["Tokyo", "Osaka"],
            "center_lat": [35.68, 34.69],
            "center_lon": [139.76, 135.50],
            "shipping_cost": [1.5, 1.2],
            "baseline_order_count": [10, 20],
            "staffing_level": [1, 2],
            "fixed_cost": [0.0, 0.0],
        }
    )
    existing_df = initial_df.copy()
    existing_df.loc[0, "staffing_level"] = 7
    existing_df.loc[0, "fixed_cost"] = 350000.0

    merged_df = merge_scenario_frame(existing_df=existing_df, initial_df=initial_df)

    assert merged_df.loc[merged_df["center_id"] == "1", "staffing_level"].item() == 7
    assert merged_df.loc[merged_df["center_id"] == "1", "fixed_cost"].item() == 350000.0


def test_build_center_scenarios_converts_frame_to_domain_objects():
    scenario_df = pd.DataFrame(
        {
            "center_id": ["1"],
            "center_name": ["Tokyo"],
            "center_lat": [35.68],
            "center_lon": [139.76],
            "shipping_cost": [1.5],
            "baseline_order_count": [100],
            "staffing_level": [3],
            "fixed_cost": [250000.0],
        }
    )

    centers = build_center_scenarios(scenario_df)

    assert len(centers) == 1
    assert centers[0].center_id == "1"
    assert centers[0].staffing_level == 3
    assert centers[0].fixed_cost == 250000.0
