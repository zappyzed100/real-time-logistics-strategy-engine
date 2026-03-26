"""国土交通省 位置参照情報 (mlit) CSVを統合する前処理スクリプト。

data/01_raw/mlint/ 配下の a 形式フォルダ内に存在するCSV(SJIS)を読み込み、
以下の成果物を data/02_intermediate/mlit/ に出力する。

    mlit_a.csv       : a 形式CSVの統合結果
    mlit_columns.csv : 元CSVごとのヘッダー列一覧

抽出列:
    市区町村名, 大字・丁目名, 小字・通称名, 緯度, 経度
"""

import csv
from pathlib import Path

ESTAT_PATH = Path(__file__).parents[3] / "data" / "01_raw" / "estat" / "b01_01.csv"
RAW_DIR = Path(__file__).parents[3] / "data" / "01_raw" / "mlint"
OUT_DIR = Path(__file__).parents[3] / "data" / "02_intermediate" / "mlit"
ESTAT_INTERMEDIATE_DIR = Path(__file__).parents[3] / "data" / "02_intermediate" / "estat"

OUT_HEADER = ["市区町村名", "大字・丁目名", "小字・通称名", "緯度", "経度"]
REQUIRED_SOURCE_COLUMNS = OUT_HEADER.copy()
ESTAT_FILTERED_HEADER = ["市区町村", "世帯人員", "ここまでの合計世帯人員"]


def iter_source_csvs() -> list[tuple[Path, Path]]:
    """a 形式の元CSV一覧を返す。"""
    source_csvs: list[tuple[Path, Path]] = []
    for folder in sorted(RAW_DIR.iterdir()):
        if not folder.is_dir():
            continue
        if not folder.name.endswith("a"):
            continue
        csv_files = sorted(folder.glob("*.csv"))
        if not csv_files:
            continue
        source_csvs.append((folder, csv_files[0]))
    return source_csvs


def resolve_extract_columns(header: list[str], csv_path: Path) -> list[int] | None:
    """a 形式CSVの必要列番号をヘッダー名から解決する。"""
    header_index = {column.strip(): index for index, column in enumerate(header)}
    resolved_indices: list[int] = []

    for column_name in REQUIRED_SOURCE_COLUMNS:
        if column_name not in header_index:
            print(f"  必要列が見つかりません: {csv_path.relative_to(RAW_DIR)} / {column_name}")

            return None

        resolved_indices.append(header_index[column_name])

    return resolved_indices


def iter_rows() -> list[list[str]]:
    """mlint配下のa形式CSVを走査し、必要列だけを返す。"""
    rows: list[list[str]] = []
    for _, csv_path in iter_source_csvs():
        with open(csv_path, encoding="cp932", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            extract_cols = resolve_extract_columns(header, csv_path)
            if extract_cols is None:
                continue

            for row in reader:
                if len(row) <= max(extract_cols):
                    continue
                rows.append([row[col_index].strip() for col_index in extract_cols])
    return rows


def load_estat_municipalities() -> set[str]:
    """e-Statの市区町村一覧を返す。"""
    municipalities: set[str] = set()

    with open(ESTAT_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)

        for row in reader:
            if not row:
                continue
            municipality_name = row[0].strip()
            if municipality_name:
                municipalities.add(municipality_name)

    return municipalities


def load_mlit_municipalities() -> set[str]:
    """mlit a形式CSVの市区町村一覧を返す。"""
    municipalities: set[str] = set()

    for _, csv_path in iter_source_csvs():
        with open(csv_path, encoding="cp932", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            extract_cols = resolve_extract_columns(header, csv_path)
            if extract_cols is None:
                continue

            municipality_col = extract_cols[0]
            for row in reader:
                if municipality_col >= len(row):
                    continue
                municipality_name = row[municipality_col].strip()
                if municipality_name:
                    municipalities.add(municipality_name)

    return municipalities


def write_filtered_intermediates() -> None:
    """両データセットで共通する市区町村のみに絞り込んだ中間CSVを出力する。

    出力:
        02_intermediate/estat/b01_01_filtered.csv : 共通市区町村のみの estat データ（累積列を再計算）
        02_intermediate/mlit/mlit_a_filtered.csv  : 共通市区町村のみの mlit_a データ
    """
    common = load_estat_municipalities() & load_mlit_municipalities()

    # --- estat filtered (累積列を再計算) ---
    estat_rows: list[list] = []
    cumulative = 0
    with open(ESTAT_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダースキップ
        for row in reader:
            if not row or row[0].strip() not in common:
                continue
            try:
                households = int(row[1].strip())
            except ValueError:
                continue
            estat_rows.append([row[0].strip(), households, cumulative])
            cumulative += households

    estat_out = ESTAT_INTERMEDIATE_DIR / "b01_01_filtered.csv"
    estat_out.parent.mkdir(parents=True, exist_ok=True)
    with open(estat_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(ESTAT_FILTERED_HEADER)
        writer.writerows(estat_rows)
    print(f"  書き込み完了: {estat_out.relative_to(Path(__file__).parents[3])}  ({len(estat_rows):,} 行)")

    # --- mlit_a filtered ---
    mlit_rows: list[list[str]] = []
    for _, csv_path in iter_source_csvs():
        with open(csv_path, encoding="cp932", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            extract_cols = resolve_extract_columns(header, csv_path)
            if extract_cols is None:
                continue
            municipality_col = extract_cols[0]
            for row in reader:
                if len(row) <= max(extract_cols):
                    continue
                if row[municipality_col].strip() not in common:
                    continue
                mlit_rows.append([row[col].strip() for col in extract_cols])

    mlit_out = OUT_DIR / "mlit_a_filtered.csv"
    mlit_out.parent.mkdir(parents=True, exist_ok=True)
    with open(mlit_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUT_HEADER)
        writer.writerows(mlit_rows)
    print(f"  書き込み完了: {mlit_out.relative_to(Path(__file__).parents[3])}  ({len(mlit_rows):,} 行)")


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OUT_HEADER)
        writer.writerows(rows)
    print(f"  書き込み完了: {path.relative_to(Path(__file__).parents[3])}  ({len(rows):,} 行)")


def build_mlit_intermediates() -> None:
    """a形式の統合CSV、列一覧CSV、フィルタ済み中間CSVを生成する。"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("mlit統合CSVを生成中...")

    rows = iter_rows()
    write_csv(OUT_DIR / "mlit_a.csv", rows)

    print("\n共通市区町村でフィルタした中間CSVを生成中...")
    write_filtered_intermediates()

    print("完了")


if __name__ == "__main__":
    build_mlit_intermediates()
