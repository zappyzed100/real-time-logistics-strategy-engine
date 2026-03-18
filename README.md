# enterprise-data-platform-snowflake

配送コスト最適化ロジックを Snowflake 上の **Vectorized Python UDF** として実装し、大規模データに対するパフォーマンス検証と CI/CD パイプラインを統合したデータエンジニアリング・ポートフォリオです。

---

## 🚀 プロジェクトのハイライト
* **Snowpark Vectorized UDF**: Pandas を用いたベクトル演算により、10,000件の幾何計算を高速にバッチ処理。
* **パフォーマンス・ベンチマーク**: 純粋な SQL と Python UDF の実行速度を定量的に比較検証。
* **モダンな開発環境**: `uv` (Astral) による高速な依存関係管理と、Snowflake 内蔵の Python ランタイム（Anaconda 供給パッケージ）とのバージョン整合を徹底。
* **自動化 CI パイプライン**: GitHub Actions による Lint (flake8) と Unit Test (pytest) の自動実行環境を構築。

---

## 🏗 アーキテクチャ



1.  **Local Development**: `uv` + `pytest` でロジックの正確性をローカルで担保。
2.  **Deployment**: Snowpark Session を介して Python ロジックを Snowflake 内の Internal Stage（@udf_stage）へデプロイ。
3.  **Execution**: Snowflake 上で `CALCULATE_DELIVERY_COST` 関数として登録し、SQL から直接呼び出し可能に。

---

## 📊 パフォーマンス検証結果

「10,000件の注文データを、2拠点との組み合わせで計20,000レコードとして処理し、ハバースサイン公式（地球の曲率を考慮した2点間距離）を用いた配送コスト計算の実行速度を比較しました。

| 実装手法 | 10,000件の処理時間 | スループット | 技術的考察 |
| :--- | :--- | :--- | :--- |
| **Pure SQL**(キャッシュ無効) | **705 ms** | ~28,368 rec/sec | エンジン直結の最適化により最速。 |
| **Python UDF** | **4.16 s** | ~4,804 rec/sec | **Pandasによるベクトル演算**。可読性・テスト性が高い。 |

**分析:**
**分析:**
Python UDF は Pure SQL 比で約6倍の時間を要しましたが、これは Python サンドボックスの起動とデータ転送のオーバーヘッドによるものです。一方で、20,000レコード規模でも数秒で処理できており、複雑なビジネスロジックをテスト可能な Python で記述できる点は、保守性と開発効率の面で大きな利点です。

---

## 🛠 技術スタック
* **Data Warehouse**: Snowflake
* **Framework**: Snowpark for Python
* **Package Manager**: `uv` (Astral)
* **Testing/CI**: `pytest`, `flake8`, GitHub Actions
* **Libraries**: `pandas`, `numpy (2.4.2)`, `python-dotenv`

---

## 📂 ディレクトリ構造
```text
.
├── .github/workflows/    # CI (GitHub Actions) 設定
├── src/
│   ├── udf/              # UDF コアロジック (Pandasベース)
│   ├── scripts/          # デプロイおよび性能計測スクリプト
│   └── data/             # テスト用ダミーデータ生成
├── tests/                # ユニットテスト (pytest)
├── pyproject.toml        # プロジェクト定義・依存関係
└── .env                  # Snowflake 接続設定（非公開）