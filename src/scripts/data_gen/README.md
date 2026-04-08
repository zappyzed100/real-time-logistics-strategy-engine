# data_gen ガイド

このディレクトリには、配送データ生成とその前処理に使うスクリプトをまとめています。

## 1. 役割

- `generate_large_data.py`: 注文データの生成
- `geospatial.py`: 市区町村重み付けと緯度経度生成
- `aggregate_mlit.py`: e-Stat と MLIT 生データの共通市区町村抽出
- `generate_mlint_a_lite.py`: 軽量サンプル用の MLIT 中間データ生成
- `fetch_prefecture_population_density.py`: 都道府県別人口密度の取得
- `generate_shipping_costs.py`: shipping_costs seed の生成

## 2. スクリプト別の働き

### 2.1 generate_large_data.py

役割:

- 注文データ `orders.csv` を生成するメイン入口
- `--geo-mode lite` または `--geo-mode strict` を指定して位置生成方法を切り替える

入力:

- [data/03_seed/products.csv](data/03_seed/products.csv)
- `lite` の場合: [data/02_intermediate/estat/b01_01_lite.csv](data/02_intermediate/estat/b01_01_lite.csv), [data/02_intermediate/mlit/mlit_a_lite.csv](data/02_intermediate/mlit/mlit_a_lite.csv)
- `strict` の場合: [data/02_intermediate/estat/b01_01_filtered.csv](data/02_intermediate/estat/b01_01_filtered.csv), [data/02_intermediate/mlit/mlit_a_filtered.csv](data/02_intermediate/mlit/mlit_a_filtered.csv)

出力:

- [data/04_out/orders.csv](data/04_out/orders.csv)

使いどころ:

- 受注レコードを大量生成したいときの標準スクリプト

### 2.2 geospatial.py

役割:

- `generate_large_data.py` から呼ばれる地理情報ユーティリティ
- e-Stat の世帯人員を重みに市区町村をサンプリングする
- MLIT の街区レベル座標から基準点を選び、最大 500m のジッターを加える

入力:

- [data/02_intermediate/estat/b01_01_lite.csv](data/02_intermediate/estat/b01_01_lite.csv) または [data/02_intermediate/estat/b01_01_filtered.csv](data/02_intermediate/estat/b01_01_filtered.csv)
- [data/02_intermediate/mlit/mlit_a_lite.csv](data/02_intermediate/mlit/mlit_a_lite.csv) または [data/02_intermediate/mlit/mlit_a_filtered.csv](data/02_intermediate/mlit/mlit_a_filtered.csv)

出力:

- Python の内部データ構造として座標候補と乱数サンプル結果を返す

使いどころ:

- 位置生成ロジックだけを調べたいとき
- lite と strict の違いを追いたいとき

### 2.3 aggregate_mlit.py

役割:

- e-Stat と MLIT の生データから共通市区町村だけを残した中間 CSV を作る
- strict モードの前処理として最重要

入力:

- [data/01_raw/estat/b01_01.csv](data/01_raw/estat/b01_01.csv)
- [data/01_raw/mlint](data/01_raw/mlint) 配下の `*a` フォルダ内 CSV 群

出力:

- [data/02_intermediate/mlit/mlit_a.csv](data/02_intermediate/mlit/mlit_a.csv)
- [data/02_intermediate/estat/b01_01_filtered.csv](data/02_intermediate/estat/b01_01_filtered.csv)
- [data/02_intermediate/mlit/mlit_a_filtered.csv](data/02_intermediate/mlit/mlit_a_filtered.csv)

使いどころ:

- strict モード用の原データ整形
- e-Stat と MLIT の対応がどこで取れているかを確認したいとき

### 2.4 generate_mlint_a_lite.py

役割:

- filtered 済み MLIT データから、軽量実行用の `mlit_a_lite.csv` を作る
- 市区町村ごとの代表点と重み付き追加抽出で 1 万行まで増やす

入力:

- [data/02_intermediate/estat/b01_01_lite.csv](data/02_intermediate/estat/b01_01_lite.csv)
- [data/02_intermediate/mlit/mlit_a_filtered.csv](data/02_intermediate/mlit/mlit_a_filtered.csv)

出力:

- [data/02_intermediate/mlit/mlit_a_lite.csv](data/02_intermediate/mlit/mlit_a_lite.csv)

使いどころ:

- strict ほど重くせずに位置生成の形を保ちたいとき

### 2.5 fetch_prefecture_population_density.py

役割:

- e-Stat API から都道府県別の人口・面積・人口密度を取得する
- logistics_centers の `center_id` と `center_name` を付与する

入力:

- e-Stat API
- [data/03_seed/logistics_centers.csv](data/03_seed/logistics_centers.csv)

出力:

- [data/01_raw/estat/prefecture_population_density.csv](data/01_raw/estat/prefecture_population_density.csv)

使いどころ:

- 都道府県単位の配送コスト seed を作る前段

### 2.6 generate_shipping_costs.py

役割:

- 人口密度 CSV をもとに `shipping_costs.csv` を作る
- `log(density)` を正規化して配送コスト係数へ写像する

入力:

- [data/01_raw/estat/prefecture_population_density.csv](data/01_raw/estat/prefecture_population_density.csv)

出力:

- [data/03_seed/shipping_costs.csv](data/03_seed/shipping_costs.csv)

使いどころ:

- 配送コスト seed を作るとき

## 3. strict モードについて

`generate_large_data.py --geo-mode strict` は、リポジトリに同梱された軽量サンプルだけではなく、自分で収集した原データを前処理して使う前提です。

strict モードを使うには、少なくとも次の 2 系統の原データが必要です。

1. e-Stat: 国勢調査の「人口等基本集計」由来の市区町村データ
2. MLIT: 47 都道府県の街区レベル位置参照情報

この 2 つを配置したあと、`aggregate_mlit.py` などで中間データを作ってから strict モードを使います。

## 4. 必要な原データ

### 4.1 e-Stat

必要なのは、`aggregate_mlit.py` が参照する [data/01_raw/estat/b01_01.csv](data/01_raw/estat/b01_01.csv) です。

想定内容:

- 国勢調査の人口等基本集計
- 市区町村名、世帯人員、累積用の基礎になる列を含む CSV

このスクリプト群では、最終的に次の列構成で読めることを前提にしています。

- 1列目: 市区町村名
- 2列目: 世帯人員
- 3列目以降: 元データ由来の列

配置先:

- [data/01_raw/estat/b01_01.csv](data/01_raw/estat/b01_01.csv)

### 4.2 MLIT

必要なのは、国土交通省の位置参照情報のうち、47 都道府県分の街区レベル位置参照情報です。

`aggregate_mlit.py` は [data/01_raw/mlint](data/01_raw/mlint) 配下の `*a` ディレクトリを走査し、その中の CSV を 1 個ずつ読む実装になっています。したがって、都道府県ごとに `a` 形式フォルダを置く必要があります。

期待している列名:

- 市区町村名
- 大字・丁目名
- 小字・通称名
- 緯度
- 経度

文字コードは元データに合わせて `cp932` を想定しています。

## 5. 配置例

strict モード向けの原データ配置は、少なくとも次のようにしておくのが安全です。

```text
data/
  01_raw/
    estat/
      b01_01.csv
    mlint/
      01a/
        01-01a.csv
      02a/
        02-01a.csv
      03a/
        03-01a.csv
      ...
      47a/
        47-01a.csv
```

補足:

- フォルダ名は `a` で終わる必要があります。`aggregate_mlit.py` がそれを条件に走査します。
- 各 `*a` フォルダには少なくとも 1 つの CSV が必要です。
- CSV のファイル名自体は固定ではありませんが、各フォルダの先頭に見つかった CSV が使われます。

## 6. strict モードまでの流れ

1. e-Stat の人口等基本集計 CSV を [data/01_raw/estat/b01_01.csv](data/01_raw/estat/b01_01.csv) に置く
2. MLIT の 47 都道府県分の街区レベル位置参照情報を [data/01_raw/mlint](data/01_raw/mlint) 配下の `*a` フォルダへ置く
3. `aggregate_mlit.py` を実行して `b01_01_filtered.csv` と `mlit_a_filtered.csv` を作る
4. 必要なら `generate_mlint_a_lite.py` で lite 用サンプルを作る
5. `generate_large_data.py --geo-mode strict` を実行する

## 7. 中間データの出力先

strict モードが最終的に参照するのは次の中間データです。

- [data/02_intermediate/estat/b01_01_filtered.csv](data/02_intermediate/estat/b01_01_filtered.csv)
- [data/02_intermediate/mlit/mlit_a_filtered.csv](data/02_intermediate/mlit/mlit_a_filtered.csv)

`geospatial.py` は strict モード時にこの 2 つを読み込みます。
