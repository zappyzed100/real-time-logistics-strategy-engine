import numpy as np
import pandas as pd


def calculate_delivery_cost_vec(
    center_lat: pd.Series,
    center_lon: pd.Series,
    customer_lat: pd.Series,
    customer_lon: pd.Series,
    weight_kg: pd.Series,
) -> pd.Series:
    """
    ハバースサイン公式を用いて2点間の距離(km)を求め、配送コストを算出する。
    Vectorized UDFとして動作させるため、入力・出力ともに Pandas Series を使用する。
    """
    # 地球の半径 (km)
    R = 6371.0

    # 緯度経度をラジアンに変換
    phi1, lam1 = np.radians(center_lat), np.radians(center_lon)
    phi2, lam2 = np.radians(customer_lat), np.radians(customer_lon)

    # ハバースサイン公式による距離計算
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distance_km = R * c

    # コスト計算ロジック（例：距離1kmあたり10円 × 重量kg）
    # ビジネスルールに応じてここを調整可能
    cost_per_km_kg = 10.0
    delivery_cost = distance_km * weight_kg * cost_per_km_kg

    return delivery_cost.round(2)
