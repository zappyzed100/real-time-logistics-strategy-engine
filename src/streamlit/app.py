import streamlit as st
from snowflake.snowpark import Session
import pandas as pd

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

required_columns = [
    "DELIVERY_COST",
    "ORDER_ID",
    "ORDER_DATE",
    "PRODUCT_CATEGORY",
    "WAREHOUSE_NAME",
]
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    st.error(f"必須カラムが不足しています: {', '.join(missing_columns)}")
    st.stop()

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
