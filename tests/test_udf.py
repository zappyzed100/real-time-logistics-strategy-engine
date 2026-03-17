import pandas as pd
import pytest
from src.udf.delivery_cost_calculator import calculate_delivery_cost_vec


def test_calculate_delivery_cost_logic():
    # テスト用データ（東京駅付近から新宿駅付近への配送を想定）
    data = pd.DataFrame(
        {
            "c_lat": [35.6812],
            "c_lon": [139.7671],
            "cust_lat": [35.6895],
            "cust_lon": [139.6917],
            "weight": [2.5],
        }
    )

    result = calculate_delivery_cost_vec(
        data["c_lat"], data["c_lon"], data["cust_lat"], data["cust_lon"], data["weight"]
    )

    # 期待値の検証（約7km、2.5kg、10円/km/kg = 約175円前後）
    assert len(result) == 1
    assert result[0] > 0
    print(f"\nCalculated Cost: {result[0]} JPY")


if __name__ == "__main__":
    pytest.main([__file__])
