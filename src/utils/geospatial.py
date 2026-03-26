from __future__ import annotations

import bisect
import csv
import math
import random
from functools import lru_cache
from pathlib import Path
from typing import Literal

BASE_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "02_intermediate"
JITTER_METERS = 500.0

DatasetMode = Literal["lite", "strict"]
LocationPoint = tuple[float, float, str, str]
WeightedContext = tuple[list[str], list[int], int]
GenerationContext = tuple[list[str], list[int], int, dict[str, list[LocationPoint]]]

DATASET_PATHS: dict[DatasetMode, tuple[Path, Path]] = {
    "lite": (
        BASE_DATA_DIR / "estat" / "b01_01_lite.csv",
        BASE_DATA_DIR / "mlit" / "mlit_a_lite.csv",
    ),
    "strict": (
        BASE_DATA_DIR / "estat" / "b01_01_filtered.csv",
        BASE_DATA_DIR / "mlit" / "mlit_a_filtered.csv",
    ),
}


def normalize_dataset_mode(mode: str = "lite") -> DatasetMode:
    normalized_mode = mode.strip().lower()
    if normalized_mode not in DATASET_PATHS:
        raise ValueError(f"未対応のデータセット種別です: {mode}. 'lite' または 'strict' を指定してください")
    return normalized_mode  # type: ignore[return-value]


def get_dataset_paths(mode: str = "lite") -> tuple[Path, Path]:
    dataset_mode = normalize_dataset_mode(mode)
    estat_path, mlit_path = DATASET_PATHS[dataset_mode]

    missing_paths = [path for path in (estat_path, mlit_path) if not path.exists()]
    if missing_paths:
        missing = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"{dataset_mode} 用データセットが見つかりません: {missing}")

    return estat_path, mlit_path


@lru_cache(maxsize=4)
def load_weighted_municipalities(csv_path: Path) -> WeightedContext:
    names: list[str] = []
    cumulative: list[int] = []
    households: list[int] = []

    with open(csv_path, encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.reader(file_obj)
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                household_count = int(row[1].strip())
                cumulative_value = int(row[2].strip())
            except ValueError:
                continue
            names.append(row[0].strip())
            households.append(household_count)
            cumulative.append(cumulative_value)

    if not names:
        raise ValueError("市区町村データが空です")

    total = cumulative[-1] + households[-1]
    return names, cumulative, total


def sample_municipality(names: list[str], cumulative: list[int], total: int) -> str:
    random_value = random.randrange(total)
    index = bisect.bisect_right(cumulative, random_value) - 1
    return names[index]


@lru_cache(maxsize=4)
def load_mlit_points_by_municipality(csv_path: Path) -> dict[str, list[LocationPoint]]:
    points: dict[str, list[LocationPoint]] = {}

    with open(csv_path, encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.reader(file_obj)
        next(reader, None)

        for row in reader:
            if len(row) < 5:
                continue
            municipality = row[0].strip()
            oaza = row[1].strip()
            koaza = row[2].strip()
            try:
                latitude = float(row[3].strip())
                longitude = float(row[4].strip())
            except ValueError:
                continue

            points.setdefault(municipality, []).append((latitude, longitude, oaza, koaza))

    return points


def jitter_lat_lon(lat: float, lon: float, max_meters: float = JITTER_METERS) -> tuple[float, float]:
    distance_m = random.uniform(0.0, max_meters)
    angle = random.uniform(0.0, 2.0 * math.pi)

    delta_lat = (distance_m * math.cos(angle)) / 111_320.0
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-12:
        delta_lon = 0.0
    else:
        delta_lon = (distance_m * math.sin(angle)) / (111_320.0 * cos_lat)

    return lat + delta_lat, lon + delta_lon


def generate_random_location(
    names: list[str],
    cumulative: list[int],
    total: int,
    points_by_city: dict[str, list[LocationPoint]],
    max_jitter_meters: float = JITTER_METERS,
) -> dict[str, str | float]:
    municipality = sample_municipality(names, cumulative, total)

    candidates = points_by_city.get(municipality)
    if not candidates:
        raise ValueError(f"座標候補がありません: {municipality}")

    base_lat, base_lon, oaza, koaza = random.choice(candidates)
    lat, lon = jitter_lat_lon(base_lat, base_lon, max_jitter_meters)

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
    max_jitter_meters: float = JITTER_METERS,
) -> list[dict[str, str | float]]:
    if n <= 0:
        return []

    locations: list[dict[str, str | float]] = []
    while len(locations) < n:
        try:
            location = generate_random_location(
                names,
                cumulative,
                total,
                points_by_city,
                max_jitter_meters=max_jitter_meters,
            )
            locations.append(location)
        except ValueError:
            continue

    return locations


@lru_cache(maxsize=2)
def build_generation_context(mode: str = "lite") -> GenerationContext:
    estat_path, mlit_path = get_dataset_paths(mode)
    names, cumulative, total = load_weighted_municipalities(estat_path)
    points_by_city = load_mlit_points_by_municipality(mlit_path)

    filtered_names: list[str] = []
    filtered_households: list[int] = []

    for index, municipality in enumerate(names):
        if municipality not in points_by_city:
            continue

        current_cumulative = cumulative[index]
        if index + 1 < len(cumulative):
            households = cumulative[index + 1] - current_cumulative
        else:
            households = total - current_cumulative

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


__all__ = [
    "DatasetMode",
    "GenerationContext",
    "JITTER_METERS",
    "LocationPoint",
    "build_generation_context",
    "generate_random_location",
    "generate_random_locations",
    "get_dataset_paths",
    "normalize_dataset_mode",
]
