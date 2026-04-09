from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import pandas as pd
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key
from dotenv import load_dotenv
from snowflake.snowpark import Session

from src.api.schemas import CenterSummaryRow, DashboardMetrics, DashboardResponse, ScenarioRow
from src.simulation import (
    OrderCandidate,
    OrderDemand,
    SimulationOptions,
    prepare_static_simulation_data,
    simulate_assignments,
)
from src.simulation.domain import StaticPreparedSimulationData
from src.streamlit.scenario_editor import (
    build_center_scenarios,
    build_center_summary_frame,
    build_initial_scenario_frame,
    build_order_candidates_from_frame,
    build_order_demands,
    sanitize_scenario_frame,
)
from src.utils.env_policy import assert_prod_access_allowed

PRECOMPUTED_CANDIDATE_TABLE = "FCT_DELIVERY_CANDIDATE_RANKINGS"
ANALYSIS_COLUMNS = [
    "ORDER_ID",
    "CENTER_NAME",
    "CUSTOMER_LAT",
    "CUSTOMER_LON",
    "WEIGHT_KG",
    "QUANTITY",
    "DELIVERY_COST",
]
PRECOMPUTED_CANDIDATE_COLUMNS = [
    "ORDER_ID",
    "CENTER_ID",
    "CENTER_NAME",
    "DISTANCE_KM",
    "DELIVERY_COST",
    "TOTAL_WEIGHT_KG",
    "CENTER_CANDIDATE_RANK",
    "ORDER_CANDIDATE_RANK",
]


@dataclass(frozen=True, slots=True)
class DashboardStaticData:
    analysis_df: pd.DataFrame
    candidate_df: pd.DataFrame
    simulation_options: SimulationOptions
    initial_scenario_df: pd.DataFrame
    order_demands: list[OrderDemand]
    order_candidates: list[OrderCandidate]


_prepared_static_cache: dict[tuple[tuple[str, str], ...], StaticPreparedSimulationData] = {}


def _load_env_files() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env.shared", override=False)
    load_dotenv(project_root / ".env", override=True)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"環境変数 {name} が未設定です")
    return value


def _target_env_prefix() -> str:
    app_env = (os.getenv("APP_ENV") or "dev").strip().lower() or "dev"
    if app_env not in {"dev", "prod"}:
        raise RuntimeError("環境変数 APP_ENV は dev または prod を指定してください")
    assert_prod_access_allowed(app_env, "fastapi")
    return app_env.upper()


def _create_session() -> Session:
    target_prefix = _target_env_prefix()
    pem = _required_env(f"{target_prefix}_STREAMLIT_USER_RSA_PRIVATE_KEY").replace("\\n", "\n")
    private_key_der = load_pem_private_key(pem.encode(), password=None).private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    connection_options: dict[str, Any] = {
        "account": _required_env("TF_VAR_SNOWFLAKE_ACCOUNT"),
        "user": _required_env(f"{target_prefix}_STREAMLIT_USER"),
        "role": _required_env(f"{target_prefix}_STREAMLIT_ROLE"),
        "warehouse": _required_env(f"{target_prefix}_STREAMLIT_WH"),
        "database": _required_env(f"{target_prefix}_GOLD_DB"),
        "schema": _required_env("SNOWFLAKE_GOLD_SCHEMA"),
        "private_key": private_key_der,
    }
    builder = cast(Any, Session.builder)
    return builder.configs(connection_options).create()


def _get_analysis_data(session: Session) -> pd.DataFrame:
    analysis_df = session.table(_required_env("STREAMLIT_ANALYSIS_TABLE")).select(*ANALYSIS_COLUMNS).to_pandas()
    analysis_df.columns = [str(col).upper() for col in analysis_df.columns]
    return analysis_df


def _get_precomputed_candidate_data(session: Session) -> pd.DataFrame:
    candidate_df = (
        session.table(PRECOMPUTED_CANDIDATE_TABLE)
        .select(*PRECOMPUTED_CANDIDATE_COLUMNS)
        .sort("CENTER_ID", "CENTER_CANDIDATE_RANK", "ORDER_ID")
        .to_pandas()
    )
    candidate_df.columns = [str(col).upper() for col in candidate_df.columns]
    return candidate_df


@lru_cache(maxsize=1)
def get_static_dashboard_data() -> DashboardStaticData:
    _load_env_files()
    session = _create_session()
    try:
        analysis_df = _get_analysis_data(session)
        candidate_df = _get_precomputed_candidate_data(session)
    finally:
        session.close()

    simulation_options = SimulationOptions()
    initial_scenario_df = build_initial_scenario_frame(analysis_df, simulation_options)
    order_demands = build_order_demands(analysis_df)
    order_candidates = build_order_candidates_from_frame(candidate_df)
    return DashboardStaticData(
        analysis_df=analysis_df,
        candidate_df=candidate_df,
        simulation_options=simulation_options,
        initial_scenario_df=initial_scenario_df,
        order_demands=order_demands,
        order_candidates=order_candidates,
    )


def _build_dashboard_response(scenario_df: pd.DataFrame) -> DashboardResponse:
    static_data = get_static_dashboard_data()
    sanitized_scenario_df = sanitize_scenario_frame(scenario_df)
    centers = build_center_scenarios(sanitized_scenario_df)
    center_signature = tuple((center.center_id, center.center_name) for center in centers)

    prepared_static_data = _prepared_static_cache.get(center_signature)
    if prepared_static_data is None:
        prepared_static_data = prepare_static_simulation_data(
            orders=static_data.order_demands,
            centers=centers,
            candidates=static_data.order_candidates,
        )
        _prepared_static_cache[center_signature] = prepared_static_data

    simulation_result = simulate_assignments(
        orders=static_data.order_demands,
        centers=centers,
        candidates=static_data.order_candidates,
        options=static_data.simulation_options,
        prepared_static_data=prepared_static_data,
    )
    center_summary_df = build_center_summary_frame(simulation_result).merge(
        sanitized_scenario_df[["center_name", "shipping_cost"]],
        on="center_name",
        how="left",
        validate="one_to_one",
    )

    total_cost = simulation_result.total_cost
    total_orders = len(simulation_result.assignments)
    avg_unit_cost = total_cost / total_orders if total_orders > 0 else 0.0

    return DashboardResponse(
        scenario_rows=[
            ScenarioRow(
                center_id=str(row["center_id"]),
                center_name=str(row["center_name"]),
                shipping_cost=float(row["shipping_cost"]),
                baseline_order_count=int(row["baseline_order_count"]),
                staffing_level=int(row["staffing_level"]),
                fixed_cost=float(row["fixed_cost"]),
            )
            for row in sanitized_scenario_df.to_dict(orient="records")
        ],
        center_summary_rows=[
            CenterSummaryRow(
                center_name=str(row["center_name"]),
                shipping_cost=float(row["shipping_cost"]),
                assigned_orders=int(row["assigned_orders"]),
                staffing_level=int(row["staffing_level"]),
                capacity=int(row["capacity"]),
                fixed_cost=float(row["fixed_cost"]),
                labor_cost=float(row["labor_cost"]),
                variable_cost=float(row["variable_cost"]),
                total_cost=float(row["total_cost"]),
            )
            for row in center_summary_df.to_dict(orient="records")
        ],
        metrics=DashboardMetrics(
            total_cost=total_cost,
            total_orders=total_orders,
            avg_unit_cost=avg_unit_cost,
            unassigned_order_count=simulation_result.unassigned_order_count,
            total_labor_cost=simulation_result.total_labor_cost,
            total_fixed_cost=simulation_result.total_fixed_cost,
        ),
    )


def get_dashboard_bootstrap() -> DashboardResponse:
    static_data = get_static_dashboard_data()
    return _build_dashboard_response(static_data.initial_scenario_df)


def simulate_dashboard(scenario_rows: list[ScenarioRow]) -> DashboardResponse:
    scenario_df = pd.DataFrame([row.model_dump() for row in scenario_rows])
    return _build_dashboard_response(scenario_df)
