"""ランダムな日本住所の緯度経度を生成するスクリプト。

処理手順:
1. b01_01_filtered.csv を使って、世帯人員加重で市区町村を1件抽出
2. mlit_a_filtered.csv から該当市区町村の緯度経度候補を取得
3. 候補から1件ランダム選択し、軽いジッターを加えて返す
"""

from __future__ import annotations

import argparse
import bisect
import csv
from functools import lru_cache
import math
import random
from pathlib import Path

ESTAT_FILTERED_PATH = (
    Path(__file__).parents[3]
    / "data"
    / "02_intermediate"
    / "estat"
    / "b01_01_filtered.csv"
)
MLIT_FILTERED_PATH = (
    Path(__file__).parents[3]
    / "data"
    / "02_intermediate"
    / "mlit"
    / "mlit_a_filtered.csv"
)

# 市区町村代表点からの微小な揺らぎ。平均的な市区町村サイズよりは十分小さい値にする。
JITTER_METERS = 500.0
LocationPoint = tuple[float, float, str, str]
WeightedContext = tuple[list[str], list[int], int]


@lru_cache(maxsize=4)
def load_weighted_municipalities(csv_path: Path) -> WeightedContext:
    """世帯人員加重抽選に必要なデータを読み込む。"""
    names: list[str] = []
    cumulative: list[int] = []
    households: list[int] = []

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                hh = int(row[1].strip())
                cum = int(row[2].strip())
            except ValueError:
                continue
            names.append(row[0].strip())
            households.append(hh)
            cumulative.append(cum)

    if not names:
        raise ValueError("市区町村データが空です")

    total = cumulative[-1] + households[-1]
    return names, cumulative, total


def sample_municipality(names: list[str], cumulative: list[int], total: int) -> str:
    """世帯人員に比例した確率で市区町村を返す。"""
    r = random.randrange(total)
    idx = bisect.bisect_right(cumulative, r) - 1
    return names[idx]


@lru_cache(maxsize=4)
def load_mlit_points_by_municipality(csv_path: Path) -> dict[str, list[LocationPoint]]:
    """市区町村ごとの緯度経度候補を読み込む。"""
    points: dict[str, list[LocationPoint]] = {}

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            if len(row) < 5:
                continue
            municipality = row[0].strip()
            oaza = row[1].strip()
            koaza = row[2].strip()
            try:
                lat = float(row[3].strip())
                lon = float(row[4].strip())
            except ValueError:
                continue

            if municipality not in points:
                points[municipality] = []
            points[municipality].append((lat, lon, oaza, koaza))

    return points


def jitter_lat_lon(lat: float, lon: float, max_meters: float) -> tuple[float, float]:
    """緯度経度にランダムな微小オフセットを加える。"""
    distance_m = random.uniform(0.0, max_meters)
    angle = random.uniform(0.0, 2.0 * math.pi)

    d_lat = (distance_m * math.cos(angle)) / 111_320.0
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-12:
        d_lon = 0.0
    else:
        d_lon = (distance_m * math.sin(angle)) / (111_320.0 * cos_lat)

    return lat + d_lat, lon + d_lon


def generate_random_location(
    names: list[str],
    cumulative: list[int],
    total: int,
    points_by_city: dict[str, list[LocationPoint]],
) -> dict[str, str | float]:
    """市区町村加重抽選 + 座標抽選 + ジッター付与で1件生成する。"""
    municipality = sample_municipality(names, cumulative, total)

    candidates = points_by_city.get(municipality)
    if not candidates:
        raise ValueError(f"座標候補がありません: {municipality}")

    base_lat, base_lon, oaza, koaza = random.choice(candidates)
    lat, lon = jitter_lat_lon(base_lat, base_lon, JITTER_METERS)

    return {
        "municipality": municipality,
        "oaza_chome": oaza,
        "koaza_alias": koaza,
        "base_lat": base_lat,
        "base_lon": base_lon,
        "lat": lat,
        "lon": lon,
    }


def generate_random_locations(
    n: int,
    names: list[str],
    cumulative: list[int],
    total: int,
    points_by_city: dict[str, list[LocationPoint]],
) -> list[dict[str, str | float]]:
    """ランダム地点を n 件まとめて生成して返す。"""
    if n <= 0:
        return []

    locations: list[dict[str, str | float]] = []
    while len(locations) < n:
        try:
            location = generate_random_location(
                names, cumulative, total, points_by_city
            )
            locations.append(location)
        except ValueError:
            # 座標候補がない市区町村が抽選された場合は再抽選
            continue

    return locations


@lru_cache(maxsize=1)
def build_generation_context() -> (
    tuple[list[str], list[int], int, dict[str, list[LocationPoint]]]
):
    """生成に必要なデータを1回だけ構築して返す。"""
    names, cumulative, total = load_weighted_municipalities(ESTAT_FILTERED_PATH)
    points_by_city = load_mlit_points_by_municipality(MLIT_FILTERED_PATH)

    # 座標候補を持つ市区町村だけを抽選対象に残して再構築する。
    filtered_names: list[str] = []
    filtered_households: list[int] = []

    for i, municipality in enumerate(names):
        if municipality not in points_by_city:
            continue

        current_cum = cumulative[i]
        if i + 1 < len(cumulative):
            households = cumulative[i + 1] - current_cum
        else:
            households = total - current_cum

        if households <= 0:
            continue

        filtered_names.append(municipality)
        filtered_households.append(households)

    if not filtered_names:
        raise ValueError("座標候補のある市区町村が見つかりません")

    filtered_cumulative: list[int] = []
    running_total = 0
    for households in filtered_households:
        filtered_cumulative.append(running_total)
        running_total += households

    return filtered_names, filtered_cumulative, running_total, points_by_city


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ランダムな緯度経度をまとめて生成する")
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=10,
        help="生成する件数 (default: 10)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    names, cumulative, total, points_by_city = build_generation_context()

    print(f"総世帯人員 L = {total:,}")
    print(f"市区町村数    = {len(names):,}")
    print(f"座標候補市区町村数 = {len(points_by_city):,}")
    print()

    locations = generate_random_locations(
        n=args.num,
        names=names,
        cumulative=cumulative,
        total=total,
        points_by_city=points_by_city,
    )

    print(f"ランダム地点サンプル ({len(locations)}件):")
    for location in locations:
        print(
            "  "
            f"{location['municipality']} / {location['oaza_chome']} {location['koaza_alias']} "
            f"-> ({location['lat']:.6f}, {location['lon']:.6f})"
        )


if __name__ == "__main__":
    main()
