import json
import os

import pandas as pd
import pydeck as pdk
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)
from dotenv import load_dotenv
from snowflake.snowpark import Session

import streamlit as st

load_dotenv()

# ページ設定
st.set_page_config(page_title="Logistics KPI Dashboard", layout="wide")
st.title("🚚 Logistics KPI Dashboard")


# Snowpark Session
@st.cache_resource
def create_session():
    pem = os.environ["DEV_STREAMLIT_USER_RSA_PRIVATE_KEY"].replace("\\n", "\n")
    private_key_der = load_pem_private_key(pem.encode(), password=None).private_bytes(
        encoding=Encoding.DER,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    return Session.builder.configs(
        {
            "account": "CWNOMGN-AF62260",
            "user": "DEV_STREAMLIT_USER",
            "private_key": private_key_der,
            "role": "DEV_STREAMLIT_READ_ROLE",
            "warehouse": "DEV_STREAMLIT_WH",
            "database": "DEV_GOLD_DB",
            "schema": "MARKETING_MART",
        }
    ).create()


session = create_session()


@st.cache_data
def get_analysis_data():
    return session.table("FCT_DELIVERY_ANALYSIS").to_pandas()


df = get_analysis_data()
df.columns = [str(col).upper() for col in df.columns]

# 日付の前処理（フィルタリングの準備）
df["ORDERED_AT"] = pd.to_datetime(df["ORDERED_AT"])
df["ORDER_DATE"] = df["ORDERED_AT"].dt.date

# ---------------------------------------------------------
# 1. サイドバー: フィルタリング & シミュレーション設定（最優先で実行）
# ---------------------------------------------------------
st.sidebar.header("🔍 フィルタリングと設定")

# フィルタ項目
min_date, max_date = df["ORDER_DATE"].min(), df["ORDER_DATE"].max()
selected_dates = st.sidebar.date_input("分析期間", value=[min_date, max_date], min_value=min_date, max_value=max_date)
all_centers = sorted(df["CENTER_NAME"].unique())
selected_centers = st.sidebar.multiselect("配送拠点", options=all_centers, default=all_centers)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ コストシミュレーション")
weight_factor = st.sidebar.slider("重量コスト係数", 0.5, 2.0, 1.0, 0.1)
target_center = st.sidebar.selectbox("調整対象拠点", ["なし"] + all_centers)
base_adjustment = st.sidebar.number_input("拠点別コスト増減額 (円)", value=0)

# --- データフィルタリング & シミュレーション計算 ---
if len(selected_dates) == 2:
    start_date, end_date = selected_dates
    mask = (df["ORDER_DATE"] >= start_date) & (df["ORDER_DATE"] <= end_date)
    filtered_df = df.loc[mask].copy()
else:
    filtered_df = df.copy()

filtered_df = filtered_df[filtered_df["CENTER_NAME"].isin(selected_centers)]

# シミュレーションコストの算出（以降の表示はすべてこれを使用）
filtered_df["SIMULATED_COST"] = filtered_df["DELIVERY_COST"] * weight_factor
if target_center != "なし":
    filtered_df.loc[filtered_df["CENTER_NAME"] == target_center, "SIMULATED_COST"] += base_adjustment

# ---------------------------------------------------------
# 2. 主要 KPI の表示 (filtered_df を使用)
# ---------------------------------------------------------
st.subheader("Key Performance Indicators")
col1, col2, col3 = st.columns(3)

total_cost = filtered_df["SIMULATED_COST"].sum()
total_orders = len(filtered_df)
avg_unit_cost = total_cost / total_orders if total_orders > 0 else 0

with col1:
    # 係数が1以外のときに差分を表示する遊び心
    delta = f"{(weight_factor - 1) * 100:.1f}%" if weight_factor != 1.0 else None
    st.metric("総配送コスト", f"¥{total_cost:,.0f}", delta=delta, delta_color="inverse")
with col2:
    st.metric("総注文数", f"{total_orders:,.0f} 件")
with col3:
    st.metric("平均配送単価", f"¥{avg_unit_cost:,.1f}")

# --- 分析詳細 ---
st.subheader("分析詳細")
tab1, tab2 = st.tabs(["拠点別コスト集計", "拠点別データ一覧"])

warehouse_summary = (
    filtered_df.groupby("CENTER_NAME")
    .agg({"SIMULATED_COST": "sum", "ORDER_ID": "count"})
    .rename(columns={"ORDER_ID": "注文数"})
)

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
    plot_df = filtered_df.dropna(subset=map_cols).copy()
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

    r = pdk.Deck(
        layers=[customer_layer, center_layer],
        initial_view_state=view_state,
        tooltip={
            "html": (
                "<b>注文ID:</b> {ORDER_ID}<br>"
                "<b>配送拠点:</b> {CENTER_NAME}<br>"
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
