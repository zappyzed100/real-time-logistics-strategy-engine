# Real-Time Logistics Strategy Engine: Distilled MIP from 1M+ Logs to 0.1ms

本プロジェクトは、100万件超の配送ログから拠点戦略や人員配置をリアルタイムに検証するための物流リソース最適化プラットフォームです。

## 1. 概要（Core Value）

開発中

## 開発プロセスと運用ルール

本プロジェクトでは、変更の追跡可能性と運用の透明性を重視し、時期に応じてマージ戦略を明示的に使い分けています。

### マージ戦略の変遷

- **2026/03/26 以前:**
  開発速度とメインブランチの可読性を優先し、Atomic PR（関心事の分離）を前提とした `Squash and merge` を採用。過去の履歴には集約されたコミットが含まれます。
- **2026/03/27 以降:**
  稼働実績の客観的可視化および試行錯誤プロセスの完全な保持を目的として、`Squash and merge` を廃止。個別コミットのタイムスタンプと実装の変遷をすべて保持する `Create a merge commit` を原則運用とします。

### 運用の意図

この運用変更は、データエンジニアリングにおける「欠損を許さない品質管理」の考え方を、自身の開発活動ログ（メタデータ）にも適用するという方針に基づいています。採用担当者の方は、`git log` を通じて日々の作業密度や技術的判断の推移をシステム的に検証することが可能です。

## 2. クイックスタート（Docker 実行）

本プロジェクトは Docker コンテナ内での開発・実行を前提としています。ローカルマシンに Python や Terraform をインストールする必要はありません。

### 2.1. 準備: 接続情報のセットアップ

プロジェクトルートに以下の設定ファイルを作成してください。

- 環境変数（`.env`）: `src` 配下のスクリプト、dbt、Loader、Streamlit で使用

```bash
cp .env.example .env
# TF_VAR_SNOWFLAKE_ACCOUNT や各種 Private Key を設定
```

補足:

- ローカル実行は開発環境（dev）固定です
- 本番環境（prod）への実行は CI からのみ許可されます
- 環境切り替えの内部実装は運用者向けドキュメントで管理します
- Streamlit 接続も `.env` / `.env.shared` の環境変数 + RSA 鍵のみを使用します
- `.streamlit/secrets.toml` は使用しません

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

> **初回セットアップ（キーペア認証・Bootstrap SQL・Workspace 変数登録）は [`terraform/README.md`](terraform/README.md) のセクション 0 を参照してください。**

Terraform の非機密設定は `terraform/common.auto.tfvars`、HCP Terraform の接続先は `terraform/backend.dev.hcl` / `terraform/backend.prod.hcl` で管理します。

```bash
# ローカル実行例
export TF_TOKEN_app_terraform_io=YOUR_TERRAFORM_TEAM_TOKEN
TF_VAR_app_env=dev terraform -chdir=terraform init -reconfigure -backend-config=backend.dev.hcl
TF_VAR_app_env=dev terraform -chdir=terraform apply
```

運用制約:

- ローカル実行は常に開発環境（dev）
- 本番環境（prod）への実行は CI のみ許可
- PR では prod への apply は実行しません
- prod apply は main への push もしくは Actions の `workflow_dispatch(run_prod_apply=true)` で実行します

## 4. データパイプラインと蒸留プロセス

コンテナ内で以下の順序で実行することで、データの生成から最適化モデルの利用までを確認できます。

### 4.1. データ生成とロード

```bash
# ローカルでは常に dev として実行（prod は CI 専用）
docker compose run --rm streamlit python src/scripts/data_gen/generate_large_data.py -n 1000000
docker compose run --rm streamlit python src/infrastructure/snowflake_loader.py
```

`src/infrastructure/snowflake_loader.py` はローカルでは開発環境（dev）として実行されます。
本番環境（prod）での実行は CI のみ許可されます。

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
├── src/transform/            # dbt プロジェクト (変換ロジック)
├── src/
│   ├── infrastructure/       # Snowflake へのデータロード
│   ├── scripts/              # 1M+ ログ生成、dbt ラッパー
│   └── streamlit/            # 0.1ms 応答を実現する最適化 UI
└── docker-compose.yml        # 開発環境の定義
```

## 6. 詳細ドキュメント

- dbt モデルの詳細: `src/transform/README.md`
- Terraform 運用ガイド: `terraform/README.md`
- Python モジュール詳細: `src/README.md`
