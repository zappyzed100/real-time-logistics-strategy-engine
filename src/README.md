# src 実行ガイド

このドキュメントは、src 配下のコードを初見の人がすぐ実行できるように、用途別に整理したガイドです。

## 1. まず理解すること

src には次の役割があります。

- データ生成: `src/scripts/data_gen/`
- Snowflake へのロード: `src/infrastructure/`
- dbt 実行補助: `src/scripts/deploy/run_dbt.py`
- シミュレーション用ドメイン層: `src/simulation/`
- 可視化: `src/streamlit/app.py`

## 2. 最短実行フロー

リポジトリルートで実行します。

### 2.1 データ生成

```bash
uv run python src/scripts/data_gen/generate_large_data.py -n 10000
```

生成物。

- `data/04_out/orders.csv`

位置生成の精度を上げたい場合は `--geo-mode strict` を使います。

```bash
uv run python src/scripts/data_gen/generate_large_data.py -n 10000 --geo-mode strict
```

`strict` モードでは、自分で収集した e-Stat と MLIT の原データから中間データを作る必要があります。取得元、配置方法、前処理の流れは [src/scripts/data_gen/README.md](src/scripts/data_gen/README.md) にまとめています。

### 2.2 Bronze へロード

```bash
# ローカルは開発環境（dev）固定（prod は CI 専用）
uv run python src/infrastructure/snowflake_loader.py
```

必要な主な環境変数 (`.env`)。

- `TF_VAR_SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_LOADER_PRIVATE_KEY` または `DEV_LOADER_USER_RSA_PRIVATE_KEY`

`src/infrastructure/snowflake_loader.py` はローカルでは開発環境（dev）を利用します。
本番環境（prod）の実行は CI でのみ許可されます。

### 2.3 dbt 実行

```bash
uv run python src/scripts/deploy/run_dbt.py debug
uv run python src/scripts/deploy/run_dbt.py run --select +int_delivery_cost_candidates +fct_delivery_analysis
uv run python src/scripts/deploy/run_dbt.py test
```

### 2.4 Streamlit 起動

```bash
uv run streamlit run src/streamlit/app.py
```

## 3. Streamlit の設定

`src/streamlit/app.py` は `.env.shared` と `.env` を読み込み、ローカルでは開発環境（dev）で接続します。

主な環境変数。

- `TF_VAR_SNOWFLAKE_ACCOUNT`
- `DEV_STREAMLIT_USER` / `PROD_STREAMLIT_USER`
- `DEV_STREAMLIT_ROLE` / `PROD_STREAMLIT_ROLE`
- `DEV_STREAMLIT_WH` / `PROD_STREAMLIT_WH`
- `DEV_GOLD_DB` / `PROD_GOLD_DB`
- `STREAMLIT_ANALYSIS_TABLE`

## 4. ファイル別の役割

### 維持対象 (現役)

1. `src/scripts/deploy/run_dbt.py`

- dbt 実行の標準入口

1. `src/infrastructure/snowflake_loader.py`

- CSV を Bronze テーブルへロード

1. `src/scripts/data_gen/generate_large_data.py`

- 受注データを生成

1. `src/scripts/data_gen/geospatial.py`

- データ生成で使う地理情報ヘルパー
- `lite` / `strict` のデータセット切替、MLIT 座標の抽出、500m ジッター付与を担当

1. `src/scripts/data_gen/README.md`

- strict モード用の原データ取得元、配置例、前処理フローのガイド

1. `src/streamlit/app.py`

- Gold 層結果の可視化

1. `src/simulation/domain.py`

- Streamlit / FastAPI から共通利用する配賦シミュレーションの計算ロジック

### 見直し候補 (レガシー寄り)

1. `src/scripts/deploy/deploy_udf.py`

- 旧 Python UDF 登録用途

1. `src/scripts/benchmark/measure_performance.py`

- 旧 UDF 前提の計測用途

1. `src/connection_test.py`

- 単発の接続確認用途

1. `src/udf/delivery_cost_calculator.py`

- `tests/test_udf.py` が参照するため削除は要注意

## 5. 整理の進め方

1. 先に README から導線を外す
2. `src/legacy` へ移動して一定期間様子を見る
3. 問題なければ削除とテスト更新を同時に行う
