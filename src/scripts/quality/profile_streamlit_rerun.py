from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any

import pandas as pd
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key
from dotenv import load_dotenv
from snowflake.snowpark import Session

from src.simulation import SimulationOptions, prepare_static_simulation_data, simulate_assignments
from src.streamlit.scenario_editor import (
    apply_simulation_result_to_analysis,
    build_center_scenarios,
    build_center_summary_frame,
    build_initial_scenario_frame,
    build_order_candidates_from_frame,
    build_order_demands,
    sanitize_scenario_frame,
)
from src.utils.env_policy import assert_prod_access_allowed

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
PRECOMPUTED_CANDIDATE_TABLE = "FCT_DELIVERY_CANDIDATE_RANKINGS"
RERUN_ROUNDS = 10


class StepTimer:
    def __init__(self) -> None:
        self.records: list[tuple[str, float]] = []

    def measure(self, label: str, fn, *args, **kwargs):
        started_at = time.perf_counter()
        result = fn(*args, **kwargs)
        self.records.append((label, (time.perf_counter() - started_at) * 1000))
        return result


def _load_env_files() -> None:
    project_root = Path(__file__).resolve().parents[3]
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
    assert_prod_access_allowed(app_env, "profile_streamlit_rerun")
    return app_env.upper()


def create_session() -> Session:
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
    return Session.builder.configs(connection_options).create()


def get_analysis_data(session: Session) -> pd.DataFrame:
    return session.table(_required_env("STREAMLIT_ANALYSIS_TABLE")).select(*ANALYSIS_COLUMNS).to_pandas()


def get_precomputed_candidate_data(session: Session) -> pd.DataFrame:
    return (
        session.table(PRECOMPUTED_CANDIDATE_TABLE)
        .select(*PRECOMPUTED_CANDIDATE_COLUMNS)
        .sort("CENTER_ID", "CENTER_CANDIDATE_RANK", "ORDER_ID")
        .to_pandas()
    )


def build_order_plot_df(analysis_df: pd.DataFrame, simulation_result: Any) -> pd.DataFrame:
    filtered_df = apply_simulation_result_to_analysis(analysis_df, simulation_result)
    return filtered_df.drop_duplicates(subset=["ORDER_ID"]).copy()


def build_map_payload(order_plot_df: pd.DataFrame) -> str:
    plot_df = order_plot_df.dropna(
        subset=[
            "CUSTOMER_LAT",
            "CUSTOMER_LON",
            "SIMULATED_COST",
            "WEIGHT_KG",
            "ORDER_ID",
            "ASSIGNED_CENTER_NAME",
            "ASSIGNMENT_STATUS",
            "IS_UNASSIGNED",
        ]
    ).copy()
    cost = plot_df["SIMULATED_COST"].astype(float)
    v_min, v_max = cost.min(), cost.quantile(0.95)
    if v_max == v_min:
        v_max = v_min + 1
    norm_cost = ((cost - v_min) / (v_max - v_min)).clip(0, 1)
    low_band = norm_cost <= 0.5
    plot_df["COLOR_R"] = 0
    plot_df["COLOR_G"] = 0
    plot_df["COLOR_B"] = 0
    plot_df.loc[low_band, "COLOR_R"] = 30
    plot_df.loc[low_band, "COLOR_G"] = (140 + norm_cost[low_band] * 180).astype(int)
    plot_df.loc[low_band, "COLOR_B"] = (220 - norm_cost[low_band] * 220).astype(int)
    plot_df.loc[~low_band, "COLOR_R"] = ((norm_cost[~low_band] - 0.5) * 400 + 30).clip(0, 255).astype(int)
    plot_df.loc[~low_band, "COLOR_G"] = 230
    plot_df.loc[~low_band, "COLOR_B"] = 0
    plot_df.loc[plot_df["IS_UNASSIGNED"], ["COLOR_R", "COLOR_G", "COLOR_B"]] = [220, 38, 38]
    return json.dumps(json.loads(plot_df.to_json(orient="records")))


def summarize(records: list[tuple[str, float]]) -> None:
    grouped: dict[str, list[float]] = {}
    for label, elapsed_ms in records:
        grouped.setdefault(label, []).append(elapsed_ms)
    for label, samples in grouped.items():
        print(
            f"{label}: mean={statistics.mean(samples):.3f} ms "
            f"median={statistics.median(samples):.3f} ms min={min(samples):.3f} ms max={max(samples):.3f} ms"
        )


def main() -> int:
    _load_env_files()
    cold_timer = StepTimer()
    session = cold_timer.measure("create_session", create_session)
    try:
        analysis_df = cold_timer.measure("load_analysis_to_pandas", get_analysis_data, session)
        candidate_df = cold_timer.measure("load_candidates_to_pandas", get_precomputed_candidate_data, session)
    finally:
        session.close()

    analysis_df.columns = [str(col).upper() for col in analysis_df.columns]
    candidate_df.columns = [str(col).upper() for col in candidate_df.columns]

    options = SimulationOptions()
    initial_scenario_df = cold_timer.measure(
        "build_initial_scenario_frame", build_initial_scenario_frame, analysis_df, options
    )
    order_demands = cold_timer.measure("build_order_demands", build_order_demands, analysis_df)
    order_candidates = cold_timer.measure("build_order_candidates_from_frame", build_order_candidates_from_frame, candidate_df)
    configured_center_scenarios = cold_timer.measure("build_center_scenarios", build_center_scenarios, initial_scenario_df)
    prepared_static_data = cold_timer.measure(
        "prepare_static_simulation_data",
        prepare_static_simulation_data,
        order_demands,
        configured_center_scenarios,
        order_candidates,
    )
    simulation_result = cold_timer.measure(
        "simulate_assignments",
        simulate_assignments,
        order_demands,
        configured_center_scenarios,
        order_candidates,
        options,
        prepared_static_data,
    )
    cold_timer.measure("build_center_summary_frame", build_center_summary_frame, simulation_result)
    order_plot_df = cold_timer.measure("build_order_plot_df", build_order_plot_df, analysis_df, simulation_result)
    cold_timer.measure("build_map_payload", build_map_payload, order_plot_df)

    print("[cold_start]")
    summarize(cold_timer.records)

    rerun_timer = StepTimer()
    scenario_df = initial_scenario_df.copy()
    for round_index in range(RERUN_ROUNDS):
        updated_scenario_df = scenario_df.copy()
        current_fixed_cost = float(str(updated_scenario_df.at[0, "fixed_cost"]))
        updated_scenario_df.loc[0, "fixed_cost"] = current_fixed_cost + round_index + 1
        sanitized_scenario_df = rerun_timer.measure("sanitize_scenario_frame", sanitize_scenario_frame, updated_scenario_df)
        configured_center_scenarios = rerun_timer.measure(
            "build_center_scenarios", build_center_scenarios, sanitized_scenario_df
        )
        simulation_result = rerun_timer.measure(
            "simulate_assignments",
            simulate_assignments,
            order_demands,
            configured_center_scenarios,
            order_candidates,
            options,
            prepared_static_data,
        )
        rerun_timer.measure("build_center_summary_frame", build_center_summary_frame, simulation_result)
        order_plot_df = rerun_timer.measure("build_order_plot_df", build_order_plot_df, analysis_df, simulation_result)
        rerun_timer.measure("build_map_payload", build_map_payload, order_plot_df)

    print("[rerun_after_sidebar_change]")
    summarize(rerun_timer.records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
