import numpy as np
import pandas as pd


def create_mlit_a_lite(b_file_path, m_file_path, output_path):
    # CSVの読み込み
    df_b = pd.read_csv(b_file_path)
    df_m = pd.read_csv(m_file_path)

    # 1. 市町村名リスト(A)を取得
    municipality_list = df_b["市区町村"].unique().tolist()

    # 処理高速化のため、mlit_a_filteredを市区町村名ごとにグループ化してインデックスを保持
    # key: 市区町村名, value: その市区町村に該当する行のインデックス（numpy配列）
    m_indices_by_city = {name: group.index.values for name, group in df_m.groupby("市区町村名")}

    results_indices = []
    seen_indices = set()

    # 2. Aの各市区町村からランダムに一つずつ抜き出す
    for city in municipality_list:
        if city in m_indices_by_city:
            # 該当するインデックスの中からランダムに1つ選択
            idx = np.random.choice(m_indices_by_city[city])
            results_indices.append(idx)
            seen_indices.add(idx)

    # 3 & 4. 世帯人員に応じた重み付けサンプリング（1万行に達するまで繰り返す）
    total_population = df_b["世帯人員"].sum()
    cum_sums = df_b["ここまでの合計世帯人員"].values

    # 全体で抽出可能な最大ユニーク行数を確認（無限ループ防止）
    available_total = sum(len(m_indices_by_city.get(c, [])) for c in municipality_list)
    target_count = min(10000, available_total)

    while len(results_indices) < target_count:
        # 0〜Bまでの乱数Cを作成
        c = np.random.uniform(0, total_population)

        # 乱数Cと「ここまでの合計世帯人員」を照らし合わせ、市区町村を決定
        # np.searchsortedを使用して高速にインデックスを特定
        # cum_sums[i] <= c < cum_sums[i+1] となる i を探す
        city_idx = np.searchsorted(cum_sums, c, side="right") - 1
        city = df_b.iloc[city_idx]["市区町村"]

        if city in m_indices_by_city:
            # 決定した市区町村に対応する行をランダムに一つ選択
            target_idx = np.random.choice(m_indices_by_city[city])

            # mlit_a_liteに入っていなければ（＝まだ選ばれていないインデックスなら）追加
            if target_idx not in seen_indices:
                results_indices.append(target_idx)
                seen_indices.add(target_idx)

    # 抽出したインデックスに基づいて新しいDataFrameを作成し、保存
    df_lite = df_m.loc[results_indices].reset_index(drop=True)
    df_lite.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"ファイルを作成しました: {output_path} (行数: {len(df_lite)})")


if __name__ == "__main__":
    b_01_01_lite_path = "data/02_intermediate/estat/b01_01_lite.csv"
    mlint_a_lite_path = "data/02_intermediate/mlit/mlit_a_lite.csv"
    mlint_filtered_path = "data/02_intermediate/mlit/mlit_a_filtered.csv"

    create_mlit_a_lite(b_01_01_lite_path, mlint_filtered_path, mlint_a_lite_path)
