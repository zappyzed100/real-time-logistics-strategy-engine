# Real-Time Logistics Strategy Engine: Distilled MIP from 1M+ Logs to 0.1ms

本プロジェクトは、100万件超の配送ログから拠点戦略や人員配置をリアルタイムに検証するための物流リソース最適化プラットフォームです。

## 1. 概要（Core Value）

開発中

## 2. クイックスタート（Docker 実行）

本プロジェクトは Docker コンテナ内での開発・実行を前提としています。ローカルマシンに Python や Terraform をインストールする必要はありません。

### 2.1. 準備: 接続情報のセットアップ

プロジェクトルートに以下の設定ファイルを作成してください。

- 環境変数（`.env`）: `src` 配下のスクリプト、dbt、Loader で使用

```bash
cp .env.example .env
# SNOWFLAKE_ACCOUNT や各種 Private Key を設定
```

- Streamlit Secrets（`.streamlit/secrets.toml`）: 

```toml
[connections.snowpark]
account = "..."
user = "..."
password = "..."
role = "..."
warehouse = "..."
database = "..."
schema = "..."
```

### 2.2. サービスの起動

Docker Compose を使用して、必要なコンポーネントを起動します。

```bash
# 基本構成 (Streamlit + dbt 実行環境)
docker compose up --build

# フルスタック (API / Dagster を含む場合)
docker compose --profile api --profile orchestration up --build
```
## 3. インフラ管理（HCP Terraform）

Snowflake の基盤リソースは `terraform/` 内で定義されており、Docker コンテナから HCP Terraform 経由で適用します。

```bash
# コンテナ内での操作例
cd terraform
terraform login
terraform init -reconfigure -backend-config="backend.hcl" -backend-config="backend.dev.hcl"
terraform apply
```

注意: `SNOWFLAKE_PRIVATE_KEY` 等の改行を含む変数は、HCP Terraform の Workspace Variables に Category `terraform` として登録してください。

## 4. データパイプラインと蒸留プロセス

コンテナ内で以下の順序で実行することで、データの生成から最適化モデルの利用までを確認できます。

### 4.1. データ生成とロード

```bash
docker compose run --rm streamlit python src/scripts/data_gen/generate_large_data.py -n 1000000
docker compose run --rm streamlit python src/infrastructure/snowflake_loader.py
```

### 4.2. dbt による特徴量エンジニアリング

```bash
docker compose run --rm streamlit python src/scripts/deploy/run_dbt.py run
```

### 4.3. モデル参照（Streamlit）

`http://localhost:8501` 


## 5. 設計判断とディレクトリ要点

### 5.1. 実装方針

- MIP Distillation: 重い最適化計算を軽量な Proxy Model へ蒸留し、UI 応答性能を極限まで追求
- dbt-Core Integration: ロジックの大部分を Snowflake 上の SQL（dbt）に寄せることで、データ処理の透過性を確保

### 5.2. ディレクトリ構造

```text
.
├── terraform/                # Snowflake 基盤管理 (HCP Terraform)
├── enterprise_data_pipeline/ # dbt プロジェクト (変換ロジック)
├── src/
│   ├── infrastructure/       # Snowflake へのデータロード
│   ├── scripts/              # 1M+ ログ生成、dbt ラッパー
│   └── streamlit/            # 0.1ms 応答を実現する最適化 UI
└── docker-compose.yml        # 開発環境の定義
```

## 6. 詳細ドキュメント

- dbt モデルの詳細: `enterprise_data_pipeline/README.md`
- Terraform 運用ガイド: `terraform/README.md`
- Python モジュール詳細: `src/README.md`
