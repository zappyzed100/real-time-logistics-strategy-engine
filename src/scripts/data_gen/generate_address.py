"""ランダムな日本の市区町村を世帯人員加重で抽出するスクリプト。

世帯人員が多い市区町村ほど選ばれやすくなる。
CSVの3列目「ここまでの合計世帯人員」を累積下限値として利用し、
bisectによるO(log n)探索で市区町村を選択する。
"""

import bisect
import csv
import random
from pathlib import Path

CSV_PATH = Path(__file__).parents[3] / "data" / "01_raw" / "estat" / "b01_01.csv"


def load_municipalities(csv_path: Path) -> tuple[list[str], list[int], int]:
    """CSVを読み込み、市区町村名・累積下限リスト・総世帯人員を返す。

    Returns:
        names     : 市区町村名のリスト
        cumulative: 各行の「ここまでの合計世帯人員」(累積下限) のリスト
        total     : 全世帯人員の合計 L
    """
    names: list[str] = []
    cumulative: list[int] = []
    households: list[int] = []

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダースキップ
        for row in reader:
            if len(row) < 3:
                continue
            try:
                hh = int(row[1].strip())
                cum = int(row[2].strip())
            except ValueError:
                continue  # '-' など数値変換できない行はスキップ
            names.append(row[0].strip())
            households.append(hh)
            cumulative.append(cum)

    total = cumulative[-1] + households[-1]
    return names, cumulative, total


def sample_municipality(
    names: list[str],
    cumulative: list[int],
    total: int,
) -> str:
    """世帯人員に比例した確率で市区町村を1件ランダムに返す。

    アルゴリズム:
        [0, L) の乱数 r を生成 → cumulative で bisect_right → 1つ左のインデックスが該当行
    """
    r = random.randrange(total)
    idx = bisect.bisect_right(cumulative, r) - 1
    return names[idx]


def main() -> None:
    names, cumulative, total = load_municipalities(CSV_PATH)
    print(f"総世帯人員 L = {total:,}")
    print(f"市区町村数  = {len(names)}")
    print()

    print("サンプル抽出 (10件):")
    for _ in range(10):
        print(f"  {sample_municipality(names, cumulative, total)}")


if __name__ == "__main__":
    main()
