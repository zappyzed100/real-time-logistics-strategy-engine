from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests  # type: ignore[import-untyped]
from dotenv import load_dotenv

URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
E_STAT_APP_ID = "YOUR_E_STAT_APP_ID"
DEFAULT_STATS_DATA_ID = "0003433220"
DEFAULT_OUTPUT_PATH = Path("data/01_raw/estat/prefecture_population_density.csv")
LOGISTICS_CENTERS_PATH = Path("data/03_seed/logistics_centers.csv")
PREFECTURES = {
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
}


def normalize_prefecture_name(name: str) -> str:
    normalized = str(name).strip().replace(" ", "").replace("　", "")
    if normalized == "東京都":
        return "東京"
    if normalized == "京都府":
        return "京都"
    if normalized == "大阪府":
        return "大阪"
    if normalized == "北海道":
        return "北海道"
    if normalized.endswith("県"):
        return normalized[:-1]
    return normalized


def _load_env_files() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env.shared")
    load_dotenv(repo_root / ".env", override=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="e-Stat API から都道府県別の人口密度データを取得して CSV に保存する")
    parser.add_argument(
        "--stats-data-id",
        default=os.getenv("E_STAT_STATS_DATA_ID", DEFAULT_STATS_DATA_ID),
        help="取得対象の statsDataId。未指定時は E_STAT_STATS_DATA_ID または既定値を利用",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("E_STAT_PREF_DENSITY_OUTPUT", str(DEFAULT_OUTPUT_PATH)),
        help="出力先 CSV パス。未指定時は E_STAT_PREF_DENSITY_OUTPUT または既定値を利用",
    )
    parser.add_argument(
        "--debug-print-limit",
        type=int,
        default=8,
        help="レスポンス概要として表示する class / metric の件数",
    )
    return parser.parse_args()


def get_app_id() -> str:
    app_id = E_STAT_APP_ID.strip()
    if not app_id or app_id == "YOUR_E_STAT_APP_ID":
        raise ValueError("E_STAT_APP_ID の定数値を設定してください。")
    return app_id


def fetch_estat_data(app_id: str, stats_data_id: str) -> dict:
    params = {
        "appId": app_id,
        "statsDataId": stats_data_id,
        "lang": "J",
    }

    response = requests.get(URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    result = payload.get("GET_STATS_DATA", {}).get("RESULT", {})
    if result.get("STATUS") not in {"0", 0, None}:
        raise ValueError(f"e-Stat API error: {result}")

    return payload


def _as_list(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def build_class_maps(data: dict) -> dict[str, dict[str, str]]:
    statistical_data = data["GET_STATS_DATA"]["STATISTICAL_DATA"]
    class_objects = statistical_data.get("CLASS_INF", {}).get("CLASS_OBJ", [])

    class_maps: dict[str, dict[str, str]] = {}
    for class_object in _as_list(class_objects):
        class_id = str(class_object.get("@id", "")).lower()
        class_items = _as_list(class_object.get("CLASS"))
        class_maps[class_id] = {str(item.get("@code", "")): str(item.get("@name", "")) for item in class_items}
    return class_maps


def print_response_overview(data: dict, limit: int = 8) -> None:
    class_maps = build_class_maps(data)
    print("e-Stat response overview:")
    print(f"  class_ids={sorted(class_maps.keys())}")
    for class_id in sorted(class_maps.keys()):
        items = list(class_maps[class_id].items())[:limit]
        print(f"  {class_id} sample={items}")


def parse_estat_json(data: dict) -> pd.DataFrame:
    values = _as_list(data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"])
    class_maps = build_class_maps(data)

    rows: list[dict[str, object]] = []
    for value in values:
        area_code = str(value.get("@area", ""))
        area_name = class_maps.get("area", {}).get(area_code, area_code)

        metric_name = None
        for class_id in ("cat01", "cat02", "tab", "time", "unit"):
            raw_code = value.get(f"@{class_id}")
            if raw_code is None:
                continue
            metric_name = class_maps.get(class_id, {}).get(str(raw_code), str(raw_code))
            if metric_name:
                break

        raw_value = str(value.get("$", "")).replace(",", "")
        try:
            numeric_value = float(raw_value)
        except ValueError:
            continue

        rows.append(
            {
                "area_code": area_code,
                "prefecture": area_name,
                "time_code": str(value.get("@time", "")),
                "metric": metric_name,
                "unit": str(value.get("@unit", "")),
                "value": numeric_value,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError("e-Stat API 応答から数値データを抽出できませんでした。")

    return frame


def load_logistics_centers(path: Path = LOGISTICS_CENTERS_PATH) -> pd.DataFrame:
    centers = pd.read_csv(path)
    centers["center_name_normalized"] = centers["center_name"].map(normalize_prefecture_name)
    return centers


def attach_center_ids(df: pd.DataFrame, centers: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()
    enriched["prefecture_normalized"] = enriched["prefecture"].map(normalize_prefecture_name)

    center_lookup = centers[["center_id", "center_name", "center_name_normalized"]].copy()
    matched = enriched.merge(
        center_lookup,
        left_on="prefecture_normalized",
        right_on="center_name_normalized",
        how="left",
    )

    unresolved_mask = matched["center_id"].isna()
    if unresolved_mask.any():
        fallback_rows = matched.loc[unresolved_mask, ["prefecture_normalized"]].copy()
        fallback_rows["fallback_key"] = fallback_rows["prefecture_normalized"]

        fallback_matches: list[dict[str, object]] = []
        for row in fallback_rows.itertuples(index=False):
            fallback_key = str(row.fallback_key)
            contains_mask = centers["center_name_normalized"].astype(str).str.contains(fallback_key, na=False)
            reverse_contains_mask = centers["center_name_normalized"].map(
                lambda value: fallback_key in value if isinstance(value, str) else False
            )
            candidates = centers[contains_mask | reverse_contains_mask]
            if len(candidates) == 1:
                candidate = candidates.iloc[0]
                fallback_matches.append(
                    {
                        "prefecture_normalized": row.prefecture_normalized,
                        "center_id_fallback": candidate["center_id"],
                        "center_name_fallback": candidate["center_name"],
                    }
                )

        if fallback_matches:
            fallback_df = pd.DataFrame(fallback_matches).drop_duplicates("prefecture_normalized")
            matched = matched.merge(fallback_df, on="prefecture_normalized", how="left")
            matched["center_id"] = matched["center_id"].fillna(matched.get("center_id_fallback"))
            matched["center_name"] = matched["center_name"].fillna(matched.get("center_name_fallback"))
            matched = matched.drop(
                columns=[column for column in ("center_id_fallback", "center_name_fallback") if column in matched.columns]
            )

    unresolved = matched[matched["center_id"].isna()]["prefecture"].drop_duplicates().tolist()
    if unresolved:
        raise ValueError(f"center_id を解決できない都道府県があります: {', '.join(unresolved)}")

    matched = matched.drop(columns=["prefecture_normalized", "center_name_normalized"])
    ordered_columns = [
        "center_id",
        "center_name",
        "prefecture",
        "population_metric",
        "population",
        "area_metric",
        "area",
        "density",
    ]
    return matched[ordered_columns].sort_values("center_id").reset_index(drop=True)


def build_density_table(df: pd.DataFrame, population_keyword: str, area_keyword: str) -> pd.DataFrame:
    normalized_prefectures = {normalize_prefecture_name(name) for name in PREFECTURES}
    prefecture_rows = df[df["prefecture"].map(normalize_prefecture_name).isin(normalized_prefectures)].copy()
    if prefecture_rows.empty:
        raise ValueError("都道府県データが抽出できませんでした。statsDataId を確認してください。")

    latest_time_code = prefecture_rows["time_code"].max()
    prefecture_rows = prefecture_rows[prefecture_rows["time_code"] == latest_time_code].copy()

    metrics = prefecture_rows["metric"].fillna("")
    print("selected latest time_code:", latest_time_code)
    print("metric candidates:", sorted({metric for metric in metrics.unique() if metric})[:20])

    density = prefecture_rows[metrics.str.contains("人口密度", na=False)].copy()
    area = prefecture_rows[metrics.str.contains("面積", na=False)].copy()
    population = prefecture_rows[
        metrics.str.contains("人口", na=False) & ~metrics.str.contains("人口密度|人口性比|人口増減|増減率|世帯", na=False)
    ].copy()

    if population.empty or area.empty or density.empty:
        metric_examples = ", ".join(sorted({metric for metric in metrics.unique() if metric})[:20])
        raise ValueError(f"人口・面積・人口密度の指標を特定できませんでした。候補 metric={metric_examples}")

    population = population.sort_values(["prefecture", "metric"]).drop_duplicates("prefecture")
    area = area.sort_values(["prefecture", "metric"]).drop_duplicates("prefecture")
    density = density.sort_values(["prefecture", "metric"]).drop_duplicates("prefecture")

    merged = population.merge(area, on="prefecture", suffixes=("_pop", "_area"), how="inner")
    merged = merged.merge(
        density[["prefecture", "metric", "value"]].rename(columns={"metric": "metric_density", "value": "value_density"}),
        on="prefecture",
        how="inner",
    )

    result = merged[
        [
            "prefecture",
            "metric_pop",
            "value_pop",
            "metric_area",
            "value_area",
            "metric_density",
            "value_density",
        ]
    ].copy()
    result.columns = [
        "prefecture",
        "population_metric",
        "population",
        "area_metric",
        "area",
        "density_metric",
        "density",
    ]
    return result.sort_values("prefecture").reset_index(drop=True)


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def main() -> None:
    _load_env_files()
    args = parse_args()

    app_id = get_app_id()
    data = fetch_estat_data(app_id=app_id, stats_data_id=args.stats_data_id)
    print_response_overview(data, limit=args.debug_print_limit)
    raw_df = parse_estat_json(data)
    density_df = build_density_table(raw_df, population_keyword="人口", area_keyword="面積")
    centers_df = load_logistics_centers()
    density_df = attach_center_ids(density_df, centers_df)

    output_path = Path(args.output)
    save_csv(density_df, output_path)
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
