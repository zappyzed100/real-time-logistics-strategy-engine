from pathlib import Path

import numpy as np
import pandas as pd


def sync_estat_lite(filtered_path: str, lite_path: str) -> None:
    filtered = pd.read_csv(filtered_path)
    Path(lite_path).parent.mkdir(parents=True, exist_ok=True)
    filtered.to_csv(lite_path, index=False, encoding="utf-8-sig")
    print(f"ファイルを作成しました: {lite_path} (行数: {len(filtered)})")


def create_mlit_a_lite(b_file_path: str, m_file_path: str, output_path: str) -> None:
    # CSVの読み込み
    df_b = pd.read_csv(b_file_path)
    df_m = pd.read_csv(m_file_path)

    # 1. 市町村名リスト(A)を取得
    municipality_list = [str(name) for name in df_b["市区町村"].dropna().astype(str).unique().tolist()]

    # 処理高速化のため、mlit_a_filteredを市区町村名ごとにグループ化してインデックスを保持
    # key: 市区町村名, value: その市区町村に該当する行のインデックス（numpy配列）
    m_indices_by_city: dict[str, np.ndarray] = {
        str(name): group.index.to_numpy(dtype=np.int64) for name, group in df_m.groupby("市区町村名")
    }

    results_indices: list[int] = []
    seen_indices: set[int] = set()

    # 2. Aの各市区町村からランダムに一つずつ抜き出す
    for city in municipality_list:
        if city in m_indices_by_city:
            # 該当するインデックスの中からランダムに1つ選択
            idx = int(np.random.choice(m_indices_by_city[city]))
            results_indices.append(idx)
            seen_indices.add(idx)

    # 3 & 4. 世帯人員に応じた重み付けサンプリング（1万行に達するまで繰り返す）
    total_population = float(df_b["世帯人員"].sum())
    cum_sums = df_b["ここまでの合計世帯人員"].to_numpy(dtype=float)

    # 全体で抽出可能な最大ユニーク行数を確認（無限ループ防止）
    available_total = sum(len(m_indices_by_city.get(c, [])) for c in municipality_list)
    target_count = min(10000, available_total)

    while len(results_indices) < target_count:
        # 0〜Bまでの乱数Cを作成
        c = np.random.uniform(0, total_population)

        # 乱数Cと「ここまでの合計世帯人員」を照らし合わせ、市区町村を決定
        # np.searchsortedを使用して高速にインデックスを特定
        # cum_sums[i] <= c < cum_sums[i+1] となる i を探す
        city_idx = int(np.searchsorted(cum_sums, c, side="right") - 1)
        city = str(df_b.iloc[city_idx]["市区町村"])

        if city in m_indices_by_city:
            # 決定した市区町村に対応する行をランダムに一つ選択
            target_idx = int(np.random.choice(m_indices_by_city[city]))

            # mlit_a_liteに入っていなければ（＝まだ選ばれていないインデックスなら）追加
            if target_idx not in seen_indices:
                results_indices.append(target_idx)
                seen_indices.add(target_idx)

    # 抽出したインデックスに基づいて新しいDataFrameを作成し、保存
    df_lite = df_m.loc[results_indices].reset_index(drop=True)
    df_lite.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"ファイルを作成しました: {output_path} (行数: {len(df_lite)})")


if __name__ == "__main__":
    b_01_01_filtered_path = "data/02_intermediate/estat/b01_01_filtered.csv"
    b_01_01_lite_path = "data/02_intermediate/estat/b01_01_lite.csv"
    mlint_a_lite_path = "data/02_intermediate/mlit/mlit_a_lite.csv"
    mlint_filtered_path = "data/02_intermediate/mlit/mlit_a_filtered.csv"

    sync_estat_lite(b_01_01_filtered_path, b_01_01_lite_path)
    create_mlit_a_lite(b_01_01_lite_path, mlint_filtered_path, mlint_a_lite_path)
