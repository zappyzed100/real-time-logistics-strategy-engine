import streamlit as st
from snowflake.snowpark import Session
import pandas as pd
import pydeck as pdk
import json

# ページ設定
st.set_page_config(page_title="Logistics KPI Dashboard", layout="wide")

st.title("🚚 Logistics KPI Dashboard")


# Snowpark Session
@st.cache_resource
def create_session():
    return Session.builder.configs(st.secrets["connections"]["snowpark"]).create()


session = create_session()


# データ取得 (Gold層)
@st.cache_data
def get_analysis_data():
    # 全件取得してPandasへ変換（デモ規模を想定）
    return session.table("fct_delivery_analysis").to_pandas()


df = get_analysis_data()

# Snowflake/Pandas間で列名の大文字小文字が揺れることがあるため正規化
df.columns = [str(col).upper() for col in df.columns]

# --- 1. 主要 KPI の表示 ---
st.subheader("Key Performance Indicators")
col1, col2, col3 = st.columns(3)

# カラム名はすべて大文字で指定
total_cost = df["DELIVERY_COST"].sum()
total_orders = len(df)
avg_unit_cost = total_cost / total_orders if total_orders > 0 else 0

with col1:
    st.metric("総配送コスト", f"¥{total_cost:,.0f}")
with col2:
    st.metric("総注文数", f"{total_orders:,.0f} 件")
with col3:
    st.metric("平均配送単価", f"¥{avg_unit_cost:,.1f}")

# --- 2. コスト推移の可視化 ---
st.subheader("配送コスト推移")
# 'ORDERED_AT' を日単位に変換
df["ORDERED_AT"] = pd.to_datetime(df["ORDERED_AT"])
df["ORDER_DATE"] = df["ORDERED_AT"].dt.date  # 日付のみを抽出
df_daily_cost = df.groupby("ORDER_DATE")["DELIVERY_COST"].sum()
st.line_chart(df_daily_cost)

# --- 3. カテゴリ・拠点別集計 ---
st.subheader("分析詳細")
tab1, tab2 = st.tabs(["商品カテゴリ別", "配送拠点別"])

with tab1:
    # CENTER_NAME（配送拠点）で集計
    warehouse_summary = (
        df.groupby("CENTER_NAME")
        .agg({"DELIVERY_COST": "sum", "ORDER_ID": "count"})
        .rename(columns={"ORDER_ID": "注文数"})
    )
    st.bar_chart(warehouse_summary["DELIVERY_COST"])

with tab2:
    st.dataframe(
        warehouse_summary.style.format({"DELIVERY_COST": "¥{:,.0f}"}),
        use_container_width=True,
    )

# --- 4. 地理情報の可視化 (pydeck) ---
st.subheader("配送エリア・コスト分布の地理的分析")

# ツールチップに表示したいデバッグ用カラムを追加
debug_cols = ["WEIGHT_KG", "DELIVERY_COST"]  # もし距離カラムがあれば追加してください
map_cols = ["CUSTOMER_LAT", "CUSTOMER_LON", "CENTER_LAT", "CENTER_LON"] + debug_cols

if all(col in df.columns for col in map_cols):
    plot_df = df.dropna(subset=map_cols).copy()

    # 1. 拠点データの抽出
    center_df = (
        plot_df[["CENTER_NAME", "CENTER_LAT", "CENTER_LON"]].drop_duplicates().copy()
    )

    # 2. 顧客プロットの色計算
    def calculate_colors(df_input):
        cost = df_input["DELIVERY_COST"]
        v_min = cost.min()
        v_max = cost.quantile(0.95)
        if v_max == v_min:
            v_max = v_min + 1

        norm_cost = ((cost - v_min) / (v_max - v_min)).clip(0, 1)

        df_input["COLOR_R"] = 255
        df_input["COLOR_G"] = (255 * (1 - norm_cost)).astype(int)
        df_input["COLOR_B"] = 0
        return df_input

    # --- 強制シリアライズ関数 ---
    def sanitize_data(df_input):
        return json.loads(df_input.to_json(orient="records"))

    # 3. 顧客レイヤー
    customer_layer = pdk.Layer(
        "ScatterplotLayer",
        sanitize_data(calculate_colors(plot_df)),
        get_position=["CUSTOMER_LON", "CUSTOMER_LAT"],
        get_color="[COLOR_R, COLOR_G, COLOR_B, 140]",
        get_radius=3000,
        pickable=True,
    )

    # 4. 拠点レイヤー
    center_layer = pdk.Layer(
        "ScatterplotLayer",
        sanitize_data(center_df),
        get_position=["CENTER_LON", "CENTER_LAT"],
        get_color=[0, 100, 255, 200],
        get_radius=15000,
        pickable=True,
    )

    # 5. 初期表示設定
    view_state = pdk.ViewState(
        latitude=36.0,
        longitude=138.0,
        zoom=5,
        pitch=45,
    )

    # 6. Deck オブジェクト（ツールチップに重量などを追加）
    r = pdk.Deck(
        layers=[customer_layer, center_layer],
        initial_view_state=view_state,
        tooltip={
            "html": """
                <b>注文ID:</b> {ORDER_ID}<br/>
                <b>配送拠点:</b> {CENTER_NAME}<br/>
                <hr style='margin: 5px 0;'>
                <b>重量:</b> {WEIGHT_KG} kg<br/>
                <b>配送コスト:</b> ¥{DELIVERY_COST}<br/>
            """,
            "style": {"color": "white", "backgroundColor": "steelblue"},
        },
    )

    st.pydeck_chart(r)

else:
    st.warning(f"地図表示に必要なカラムが不足しています。必要: {map_cols}")
