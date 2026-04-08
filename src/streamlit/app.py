import json
import os
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

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
from src.simulation import SimulationOptions, prepare_static_simulation_data, simulate_assignments
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
from src.utils.env_policy import assert_prod_access_allowed


class ExperimentalInputVariant(TypedDict):
    column_widths: tuple[float, float, float, float]
    label_visibility: Literal["visible", "hidden", "collapsed"]
    fixed_cost_format: str | None


SELECTED_INPUT_VARIANT: ExperimentalInputVariant = {
    "column_widths": (0.95, 0.6, 1.35, 1.75),
    "label_visibility": "collapsed",
    "fixed_cost_format": None,
}

SIDEBAR_WIDTH_PX = 520


def _sidebar_style() -> str:
    return f"""
    <style>
    section[data-testid=\"stSidebar\"][aria-expanded=\"true\"] {{
        width: {SIDEBAR_WIDTH_PX}px !important;
        min-width: {SIDEBAR_WIDTH_PX}px !important;
    }}
    section[data-testid=\"stSidebar\"][aria-expanded=\"true\"] > div {{
        width: {SIDEBAR_WIDTH_PX}px !important;
        min-width: {SIDEBAR_WIDTH_PX}px !important;
    }}
    section[data-testid=\"stSidebar\"][aria-expanded=\"false\"] {{
        width: auto !important;
        min-width: 0 !important;
    }}
    section[data-testid=\"stSidebar\"][aria-expanded=\"false\"] > div {{
        width: auto !important;
        min-width: 0 !important;
    }}
    .scenario-header {{
        font-size: 0.72rem;
        font-weight: 800;
        color: #f8fafc;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-bottom: 0.2rem;
    }}
    .scenario-row-title {{
        font-weight: 700;
        font-size: 0.9rem;
    }}
    .scenario-row-shipping-cost {{
        color: #e2e8f0;
        font-size: 0.92rem;
        font-weight: 600;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"] input[type="number"] {{
        appearance: auto !important;
        -moz-appearance: auto !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="input"] input[type="number"]::-webkit-outer-spin-button,
    section[data-testid="stSidebar"] [data-baseweb="input"] input[type="number"]::-webkit-inner-spin-button {{
        -webkit-appearance: auto !important;
        appearance: auto !important;
        opacity: 1 !important;
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[data-testid="stNumberInput"] button,
    section[data-testid="stSidebar"] [data-baseweb="input"] button {{
        display: none !important;
    }}
    </style>
    """


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
st.markdown(_sidebar_style(), unsafe_allow_html=True)


# Snowpark Session
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
STATIC_SIMULATION_KEY = "static_simulation_data"
STATIC_SIMULATION_SIGNATURE_KEY = "static_simulation_center_signature"
DISPLAY_MODE_KEY = "display_mode"
MAP_SAMPLE_SIZE = 10000


@st.cache_data
def get_analysis_data() -> pd.DataFrame:
    return session.table(_required_env("STREAMLIT_ANALYSIS_TABLE")).select(*ANALYSIS_COLUMNS).to_pandas()


@st.cache_data
def get_precomputed_candidate_data() -> pd.DataFrame:
    return (
        session.table(PRECOMPUTED_CANDIDATE_TABLE)
        .select(*PRECOMPUTED_CANDIDATE_COLUMNS)
        .sort("CENTER_ID", "CENTER_CANDIDATE_RANK", "ORDER_ID")
        .to_pandas()
    )


@st.cache_data
def get_order_demands(analysis_df: pd.DataFrame) -> list[Any]:
    return build_order_demands(analysis_df)


@st.cache_data
def get_order_candidates(candidate_frame: pd.DataFrame) -> list[Any]:
    return build_order_candidates_from_frame(candidate_frame)


def build_order_plot_df(analysis_df: pd.DataFrame, simulation_result: Any) -> pd.DataFrame:
    filtered_df = apply_simulation_result_to_analysis(analysis_df, simulation_result)
    return filtered_df.drop_duplicates(subset=["ORDER_ID"]).copy()


def build_map_plot_df(order_plot_df: pd.DataFrame) -> pd.DataFrame:
    map_cols = [
        "CUSTOMER_LAT",
        "CUSTOMER_LON",
        "SIMULATED_COST",
        "WEIGHT_KG",
        "ORDER_ID",
        "ASSIGNED_CENTER_NAME",
        "ASSIGNMENT_STATUS",
        "IS_UNASSIGNED",
    ]
    plot_df = cast(Any, order_plot_df).dropna(subset=map_cols).copy()
    if len(plot_df) > MAP_SAMPLE_SIZE:
        plot_df = plot_df.sample(n=MAP_SAMPLE_SIZE, random_state=0).copy()
    return plot_df


def calculate_map_colors(plot_df: pd.DataFrame) -> pd.DataFrame:
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
    return plot_df


def sanitize_map_data(plot_df: pd.DataFrame) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(plot_df.to_json(orient="records")))


def apply_fullscreen_style() -> None:
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        div[data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }
        div[data-testid="stAppViewContainer"] .main .block-container {
            max-width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


df = get_analysis_data()
df.columns = [str(col).upper() for col in df.columns]
candidate_df = get_precomputed_candidate_data()
candidate_df.columns = [str(col).upper() for col in candidate_df.columns]

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
if DISPLAY_MODE_KEY not in st.session_state:
    st.session_state[DISPLAY_MODE_KEY] = "ダッシュボード"

scenario_df = st.session_state[SCENARIO_STATE_KEY].copy()
display_mode = str(st.session_state[DISPLAY_MODE_KEY])
is_fullscreen_mode = display_mode in {"注文別データ一覧", "地図"}
if is_fullscreen_mode:
    apply_fullscreen_style()
updated_rows: list[dict[str, object]] = []
with st.sidebar:
    st.subheader("拠点情報")
    st.caption("固定費は 100 万円単位です。")
    if is_fullscreen_mode:
        st.info("全画面表示中はシナリオ編集を無効化しています。")
    variant = SELECTED_INPUT_VARIANT
    header_columns = st.columns(list(variant["column_widths"]), gap="small")
    header_columns[0].markdown('<div class="scenario-header">拠点</div>', unsafe_allow_html=True)
    header_columns[1].markdown('<div class="scenario-header">配送係数</div>', unsafe_allow_html=True)
    header_columns[2].markdown('<div class="scenario-header">人員数</div>', unsafe_allow_html=True)
    header_columns[3].markdown('<div class="scenario-header">固定費<br>(100万円単位)</div>', unsafe_allow_html=True)
    for row in scenario_df.to_dict(orient="records"):
        center_id = str(row["center_id"])
        row_columns = st.columns(list(variant["column_widths"]), gap="small")
        row_columns[0].markdown(f'<div class="scenario-row-title">{row["center_name"]}</div>', unsafe_allow_html=True)
        row_columns[1].markdown(
            f'<div class="scenario-row-shipping-cost">{float(row["shipping_cost"]):.3f}</div>',
            unsafe_allow_html=True,
        )
        staffing_level = row_columns[2].number_input(
            "人員数",
            min_value=0,
            step=1,
            value=int(row["staffing_level"]),
            key=f"staffing_level_{center_id}",
            label_visibility=variant["label_visibility"],
            disabled=is_fullscreen_mode,
        )
        if variant["fixed_cost_format"] is None:
            fixed_cost = row_columns[3].number_input(
                "固定費",
                min_value=0,
                step=1_000_000,
                value=int(row["fixed_cost"]),
                key=f"fixed_cost_{center_id}",
                label_visibility=variant["label_visibility"],
                disabled=is_fullscreen_mode,
            )
        else:
            fixed_cost = row_columns[3].number_input(
                "固定費",
                min_value=0,
                step=1_000_000,
                value=int(row["fixed_cost"]),
                key=f"fixed_cost_{center_id}",
                label_visibility=variant["label_visibility"],
                format=variant["fixed_cost_format"],
                disabled=is_fullscreen_mode,
            )
        updated_rows.append(
            {
                **row,
                "staffing_level": staffing_level,
                "fixed_cost": fixed_cost,
            }
        )

st.session_state[SCENARIO_STATE_KEY] = sanitize_scenario_frame(pd.DataFrame(updated_rows))

configured_center_scenarios = build_center_scenarios(st.session_state[SCENARIO_STATE_KEY])
order_demands = get_order_demands(df)
order_candidates = get_order_candidates(candidate_df)
current_center_signature = tuple((center.center_id, center.center_name) for center in configured_center_scenarios)
if (
    STATIC_SIMULATION_KEY not in st.session_state
    or st.session_state.get(STATIC_SIMULATION_SIGNATURE_KEY) != current_center_signature
):
    st.session_state[STATIC_SIMULATION_KEY] = prepare_static_simulation_data(
        orders=order_demands,
        centers=configured_center_scenarios,
        candidates=order_candidates,
    )
    st.session_state[STATIC_SIMULATION_SIGNATURE_KEY] = current_center_signature
simulation_result = simulate_assignments(
    orders=order_demands,
    centers=configured_center_scenarios,
    candidates=order_candidates,
    options=simulation_options,
    prepared_static_data=st.session_state[STATIC_SIMULATION_KEY],
)
order_plot_df = build_order_plot_df(df, simulation_result)
center_summary_df = build_center_summary_frame(simulation_result)
center_plot_df = pd.DataFrame(
    [
        {
            "CENTER_NAME": center.center_name,
            "CENTER_LAT": center.latitude,
            "CENTER_LON": center.longitude,
            "STAFFING_LEVEL": center.staffing_level,
            "FIXED_COST": center.fixed_cost,
        }
        for center in configured_center_scenarios
    ]
)

display_mode = cast(
    str,
    st.radio(
        "表示モード",
        options=["ダッシュボード", "注文別データ一覧", "地図"],
        key=DISPLAY_MODE_KEY,
        horizontal=True,
    ),
)

if display_mode == "注文別データ一覧":
    st.subheader("注文別データ一覧")
    st.dataframe(
        order_plot_df[
            [
                "ORDER_ID",
                "ASSIGNED_CENTER_NAME",
                "ASSIGNMENT_STATUS",
                "FALLBACK_CENTER_NAME",
                "SIMULATED_COST",
                "SIMULATED_DISTANCE_KM",
                "WEIGHT_KG",
            ]
        ].style.format({"SIMULATED_COST": "¥{:,.0f}", "SIMULATED_DISTANCE_KM": "{:.1f} km"}),
        width="stretch",
        height=880,
    )
    st.stop()

if display_mode == "地図":
    st.subheader("配送エリア・コスト分布の地理的分析")
    st.caption(f"地図上は注文データを最大 {MAP_SAMPLE_SIZE:,} 件表示します。")

    map_cols = [
        "CUSTOMER_LAT",
        "CUSTOMER_LON",
        "SIMULATED_COST",
        "WEIGHT_KG",
        "ORDER_ID",
        "ASSIGNED_CENTER_NAME",
        "ASSIGNMENT_STATUS",
        "IS_UNASSIGNED",
    ]

    if all(col in order_plot_df.columns for col in map_cols):
        plot_df = build_map_plot_df(order_plot_df)

        customer_layer = pdk.Layer(
            "ScatterplotLayer",
            sanitize_map_data(calculate_map_colors(plot_df)),
            get_position=["CUSTOMER_LON", "CUSTOMER_LAT"],
            get_color="[COLOR_R, COLOR_G, COLOR_B, 140]",
            get_radius=3000,
            pickable=True,
        )

        center_layer = pdk.Layer(
            "ScatterplotLayer",
            sanitize_map_data(center_plot_df),
            get_position=["CENTER_LON", "CENTER_LAT"],
            get_color=[36, 62, 92, 220],
            get_radius=15000,
            pickable=True,
        )

        r = pdk.Deck(
            layers=[customer_layer, center_layer],
            initial_view_state=pdk.ViewState(latitude=36.0, longitude=138.0, zoom=5, pitch=45),
            tooltip={
                "html": (
                    "<b>注文ID:</b> {ORDER_ID}<br>"
                    "<b>担当拠点:</b> {ASSIGNED_CENTER_NAME}<br>"
                    "<b>割当状態:</b> {ASSIGNMENT_STATUS}<br>"
                    "<hr>"
                    "<b>重量:</b> {WEIGHT_KG} kg<br>"
                    "<b>配送コスト:</b> ¥{SIMULATED_COST}"
                ),
                "style": {"color": "white", "backgroundColor": "steelblue"},
            },
        )
        st.pydeck_chart(r)
    else:
        st.warning("地図表示に必要なカラムが不足しています。")
    st.stop()

overview_left, overview_right, overview_third, overview_fourth = st.columns(4)
with overview_left:
    st.metric("対象拠点数", f"{len(configured_center_scenarios)} 拠点")
with overview_right:
    st.metric("設定人員合計", f"{sum(center.staffing_level for center in configured_center_scenarios):,} 人")
with overview_third:
    st.metric("固定費合計", f"¥{sum(center.fixed_cost for center in configured_center_scenarios):,.0f}")
with overview_fourth:
    st.metric("人件費合計", f"¥{simulation_result.total_labor_cost:,.0f}")

st.subheader("Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

total_cost = simulation_result.total_cost
total_orders = len(simulation_result.assignments)
avg_unit_cost = total_cost / total_orders if total_orders > 0 else 0

with col1:
    st.metric("総コスト", f"¥{total_cost:,.0f}")
with col2:
    st.metric("総注文数", f"{total_orders:,.0f} 件")
with col3:
    st.metric("平均配送単価", f"¥{avg_unit_cost:,.1f}")
with col4:
    st.metric("未割当注文", f"{simulation_result.unassigned_order_count:,.0f} 件")

# --- 分析詳細 ---
st.subheader("分析詳細")
st.subheader("拠点別コスト集計")
if center_summary_df.empty:
    st.info("表示できる拠点サマリがありません。")
else:
    chart_df = center_summary_df.set_index("center_name")
    st.bar_chart(chart_df["total_cost"], width="stretch")
    st.dataframe(
        chart_df.rename(
            columns={
                "assigned_orders": "担当注文数",
                "staffing_level": "人員数",
                "capacity": "処理可能件数",
                "fixed_cost": "固定費",
                "labor_cost": "人件費",
                "variable_cost": "配送費",
                "total_cost": "総コスト",
            }
        ).style.format({"固定費": "¥{:,.0f}", "人件費": "¥{:,.0f}", "配送費": "¥{:,.0f}", "総コスト": "¥{:,.0f}"}),
        width="stretch",
    )
