import json
import os
from pathlib import Path
from typing import Any, cast

import pandas as pd
import pydeck as pdk  # type: ignore[import-untyped]
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)
from dotenv import load_dotenv
from snowflake.snowpark import Session

import streamlit as st
from src.simulation import SimulationOptions
from src.streamlit.scenario_editor import (
    build_center_scenarios,
    build_initial_scenario_frame,
    merge_scenario_frame,
    sanitize_scenario_frame,
)
from src.utils.env_policy import assert_prod_access_allowed


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
    assert_prod_access_allowed(app_env, "streamlit")
    return app_env.upper()


_load_env_files()

# ページ設定
st.set_page_config(page_title="Logistics KPI Dashboard", layout="wide")
st.title("🚚 Logistics KPI Dashboard")
st.markdown(
    """
    <style>
    .scenario-row-title {
        font-weight: 700;
        font-size: 0.98rem;
    }
    .scenario-row-meta {
        color: #6b7280;
        font-size: 0.78rem;
    }
    .scenario-fixed-cost-unit {
        color: #6b7280;
        font-size: 0.74rem;
        margin-top: -0.3rem;
        margin-bottom: 0.1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Snowpark Session
@st.cache_resource
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
    builder = cast(Any, Session.builder)
    return builder.configs(connection_options).create()


session = create_session()


@st.cache_data
def get_analysis_data() -> pd.DataFrame:
    return session.table(_required_env("STREAMLIT_ANALYSIS_TABLE")).to_pandas()


df = get_analysis_data()
df.columns = [str(col).upper() for col in df.columns]

SCENARIO_STATE_KEY = "scenario_editor_df"
simulation_options = SimulationOptions()
initial_scenario_df = build_initial_scenario_frame(df, simulation_options)
if SCENARIO_STATE_KEY not in st.session_state:
    st.session_state[SCENARIO_STATE_KEY] = initial_scenario_df
else:
    st.session_state[SCENARIO_STATE_KEY] = merge_scenario_frame(
        existing_df=st.session_state[SCENARIO_STATE_KEY],
        initial_df=initial_scenario_df,
    )
filtered_df = df.copy()
filtered_df["SIMULATED_COST"] = filtered_df["DELIVERY_COST"]
scenario_df = st.session_state[SCENARIO_STATE_KEY].copy()
updated_rows: list[dict[str, object]] = []
with st.sidebar:
    st.subheader("拠点情報")
    st.caption("左上の矢印でサイドバーごと隠せます。人員数は 1 人単位、固定費は 100 万円単位です。")
    for row in scenario_df.to_dict(orient="records"):
        center_id = str(row["center_id"])
        st.markdown(f'<div class="scenario-row-title">{row["center_name"]}</div>', unsafe_allow_html=True)
        st.markdown(
            (
                '<div class="scenario-row-meta">'
                f"配送係数 {float(row['shipping_cost']):.3f}"
                " | "
                f"現状注文数 {int(row['baseline_order_count']):,}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        staffing_level = st.number_input(
            "人員数",
            min_value=0,
            step=1,
            value=int(row["staffing_level"]),
            key=f"staffing_level_{center_id}",
        )
        st.markdown('<div class="scenario-fixed-cost-unit">固定費は 100万円単位</div>', unsafe_allow_html=True)
        fixed_cost = st.number_input(
            "固定費",
            min_value=0,
            step=1_000_000,
            value=int(row["fixed_cost"]),
            key=f"fixed_cost_{center_id}",
            format="%d",
        )
        st.divider()
        updated_rows.append(
            {
                **row,
                "staffing_level": staffing_level,
                "fixed_cost": fixed_cost,
            }
        )

st.session_state[SCENARIO_STATE_KEY] = sanitize_scenario_frame(pd.DataFrame(updated_rows))

configured_center_scenarios = build_center_scenarios(st.session_state[SCENARIO_STATE_KEY])

overview_left, overview_right, overview_third = st.columns(3)
with overview_left:
    st.metric("対象拠点数", f"{len(configured_center_scenarios)} 拠点")
with overview_right:
    st.metric("設定人員合計", f"{sum(center.staffing_level for center in configured_center_scenarios):,} 人")
with overview_third:
    st.metric("固定費合計", f"¥{sum(center.fixed_cost for center in configured_center_scenarios):,.0f}")

# ---------------------------------------------------------
# 2. 主要 KPI の表示 (filtered_df を使用)
# ---------------------------------------------------------
st.subheader("Key Performance Indicators")
col1, col2, col3 = st.columns(3)

total_cost = filtered_df["SIMULATED_COST"].sum()
total_orders = len(filtered_df)
avg_unit_cost = total_cost / total_orders if total_orders > 0 else 0

with col1:
    st.metric("総配送コスト", f"¥{total_cost:,.0f}")
with col2:
    st.metric("総注文数", f"{total_orders:,.0f} 件")
with col3:
    st.metric("平均配送単価", f"¥{avg_unit_cost:,.1f}")

# --- 分析詳細 ---
st.subheader("分析詳細")
tab1, tab2 = st.tabs(["拠点別コスト集計", "拠点別データ一覧"])

warehouse_summary = filtered_df.groupby("CENTER_NAME").agg({"SIMULATED_COST": "sum", "ORDER_ID": "count"})
warehouse_summary = cast(Any, warehouse_summary).rename(columns={"ORDER_ID": "注文数"})

with tab1:
    st.bar_chart(warehouse_summary["SIMULATED_COST"], width="stretch")
with tab2:
    st.dataframe(
        warehouse_summary.style.format({"SIMULATED_COST": "¥{:,.0f}"}),
        width="stretch",
    )

# --- 4. 地理情報の可視化 (pydeck) ---
st.subheader("配送エリア・コスト分布の地理的分析")

map_cols = [
    "CUSTOMER_LAT",
    "CUSTOMER_LON",
    "CENTER_LAT",
    "CENTER_LON",
    "SIMULATED_COST",
    "WEIGHT_KG",
]

if all(col in filtered_df.columns for col in map_cols):
    plot_df = cast(Any, filtered_df).dropna(subset=map_cols).copy()
    center_df = plot_df[["CENTER_NAME", "CENTER_LAT", "CENTER_LON"]].drop_duplicates().copy()

    def calculate_colors(df_input):
        cost = df_input["SIMULATED_COST"]
        v_min, v_max = cost.min(), cost.quantile(0.95)
        if v_max == v_min:
            v_max = v_min + 1
        norm_cost = ((cost - v_min) / (v_max - v_min)).clip(0, 1)
        df_input["COLOR_R"], df_input["COLOR_G"], df_input["COLOR_B"] = (
            255,
            (255 * (1 - norm_cost)).astype(int),
            0,
        )
        return df_input

    def sanitize_data(df_input):
        return json.loads(df_input.to_json(orient="records"))

    customer_layer = pdk.Layer(
        "ScatterplotLayer",
        sanitize_data(calculate_colors(plot_df)),
        get_position=["CUSTOMER_LON", "CUSTOMER_LAT"],
        get_color="[COLOR_R, COLOR_G, COLOR_B, 140]",
        get_radius=3000,
        pickable=True,
    )

    center_layer = pdk.Layer(
        "ScatterplotLayer",
        sanitize_data(center_df),
        get_position=["CENTER_LON", "CENTER_LAT"],
        get_color=[0, 100, 255, 200],
        get_radius=15000,
        pickable=True,
    )

    view_state = pdk.ViewState(latitude=36.0, longitude=138.0, zoom=5, pitch=45)

    tooltip: Any = {
        "html": (
            "<b>注文ID:</b> {ORDER_ID}<br>"
            "<b>配送拠点:</b> {CENTER_NAME}<br>"
            "<hr>"
            "<b>重量:</b> {WEIGHT_KG} kg<br>"
            "<b>配送コスト:</b> ¥{SIMULATED_COST}"
        ),
        "style": {"color": "white", "backgroundColor": "steelblue"},
    }

    r = pdk.Deck(
        layers=[customer_layer, center_layer],
        initial_view_state=view_state,
        tooltip=tooltip,
    )
    st.pydeck_chart(r)
else:
    st.warning("地図表示に必要なカラムが不足しています。")
