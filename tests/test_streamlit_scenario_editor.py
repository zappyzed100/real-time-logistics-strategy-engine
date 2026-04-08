from types import SimpleNamespace
from typing import cast

import pandas as pd

from src.simulation import OrderAssignment, SimulationOptions, SimulationResult
from src.streamlit.scenario_editor import (
    apply_simulation_result_to_analysis,
    build_center_scenarios,
    build_center_summary_frame,
    build_initial_scenario_frame,
    build_order_candidates_from_frame,
    build_order_demands,
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


def test_build_order_demands_converts_analysis_frame_to_domain_inputs():
    analysis_df = pd.DataFrame(
        {
            "ORDER_ID": [1],
            "CUSTOMER_LAT": [35.68],
            "CUSTOMER_LON": [139.76],
            "WEIGHT_KG": [2.5],
            "QUANTITY": [3],
        }
    )

    orders = build_order_demands(analysis_df)

    assert len(orders) == 1
    assert orders[0].order_id == "1"
    assert orders[0].total_weight_kg == 7.5


def test_build_order_candidates_from_frame_preserves_precomputed_ranks():
    candidate_df = pd.DataFrame(
        {
            "ORDER_ID": ["O2", "O1"],
            "CENTER_ID": ["13", "13"],
            "CENTER_NAME": ["東京", "東京"],
            "DISTANCE_KM": [5.0, 3.0],
            "DELIVERY_COST": [600.0, 500.0],
            "TOTAL_WEIGHT_KG": [2.0, 1.0],
            "CENTER_CANDIDATE_RANK": [2, 1],
            "ORDER_CANDIDATE_RANK": [1, 1],
        }
    )

    candidates = build_order_candidates_from_frame(candidate_df)

    assert [candidate.order_id for candidate in candidates] == ["O1", "O2"]
    assert candidates[0].center_candidate_rank == 1
    assert candidates[1].center_candidate_rank == 2


def test_apply_simulation_result_to_analysis_adds_assignment_columns():
    analysis_df = pd.DataFrame(
        {
            "ORDER_ID": [1],
            "CENTER_NAME": ["東京"],
            "CUSTOMER_LAT": [35.68],
            "CUSTOMER_LON": [139.76],
            "WEIGHT_KG": [1.0],
            "QUANTITY": [1],
        }
    )
    simulation_result = SimulationResult(
        assignments=(
            OrderAssignment(
                order_id="1",
                center_id=None,
                center_name=None,
                distance_km=12.3,
                delivery_cost=999.0,
                capacity_exceeded=True,
                is_unassigned=True,
                fallback_center_id="13",
                fallback_center_name="東京",
            ),
        ),
        center_summaries=(),
        total_fixed_cost=0.0,
        total_labor_cost=0.0,
        total_variable_cost=999.0,
        total_cost=999.0,
        unassigned_order_count=1,
        unassigned_total_cost=999.0,
    )

    result_df = apply_simulation_result_to_analysis(analysis_df, simulation_result)

    assert result_df.loc[0, "ASSIGNED_CENTER_NAME"] == "未割当"
    assert result_df.loc[0, "ASSIGNMENT_STATUS"] == "未割当"
    assert result_df.loc[0, "SIMULATED_COST"] == 999.0
    assert result_df.loc[0, "FALLBACK_CENTER_NAME"] == "東京"


def test_apply_simulation_result_to_analysis_accepts_legacy_assignment_without_is_unassigned():
    analysis_df = pd.DataFrame(
        {
            "ORDER_ID": [1],
            "CENTER_NAME": ["東京"],
            "CUSTOMER_LAT": [35.68],
            "CUSTOMER_LON": [139.76],
            "WEIGHT_KG": [1.0],
            "QUANTITY": [1],
        }
    )
    legacy_assignment = SimpleNamespace(
        order_id="1",
        center_id=None,
        center_name=None,
        distance_km=12.3,
        delivery_cost=999.0,
        capacity_exceeded=True,
        fallback_center_name="東京",
    )
    simulation_result = cast(SimulationResult, SimpleNamespace(assignments=(legacy_assignment,)))

    result_df = apply_simulation_result_to_analysis(analysis_df, simulation_result)

    assert result_df.loc[0, "ASSIGNMENT_STATUS"] == "未割当"
    assert bool(result_df.loc[0, "IS_UNASSIGNED"]) is True
    assert result_df.loc[0, "FALLBACK_CENTER_NAME"] == "東京"


def test_build_center_summary_frame_exposes_cost_breakdown():
    simulation_result = SimulationResult(
        assignments=(),
        center_summaries=(),
        total_fixed_cost=0.0,
        total_labor_cost=0.0,
        total_variable_cost=0.0,
        total_cost=0.0,
        unassigned_order_count=0,
        unassigned_total_cost=0.0,
    )

    summary_df = build_center_summary_frame(simulation_result)

    assert summary_df.empty


def test_build_center_summary_frame_accepts_legacy_summary_without_labor_cost():
    legacy_summary = SimpleNamespace(
        center_name="東京",
        assigned_orders=3,
        staffing_level=2,
        capacity=40,
        fixed_cost=1000000.0,
        variable_cost=2500.0,
        total_cost=1002500.0,
    )
    simulation_result = cast(SimulationResult, SimpleNamespace(center_summaries=(legacy_summary,)))

    summary_df = build_center_summary_frame(simulation_result)

    assert summary_df.loc[0, "center_name"] == "東京"
    assert summary_df.loc[0, "labor_cost"] == 0.0
    assert summary_df.loc[0, "total_cost"] == 1002500.0
