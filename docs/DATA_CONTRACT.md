# DATA_CONTRACT

このドキュメントは、データ提供者（パイプライン）とデータ利用者（BI/アナリスト）間の契約です。
公開テーブルの意味・品質・変更手続きを明文化し、下流システムのサイレント破壊を防止します。

## 1. 目的と適用範囲

- 目的:
  - セマンティック安定性（列名/型/意味）の維持
  - 品質期待値（鮮度・欠損・重複）の合意
  - 破壊的変更の計画的運用
- 適用範囲:
  - Public（契約対象）: Gold レイヤー
  - Internal（参考情報）: Silver レイヤー

契約単位:

- テーブル
- カラム
- 更新頻度
- 品質しきい値

## 2. 公開区分（Public / Internal）

## 2.1 Public（下流利用保証あり）

- `fct_delivery_analysis`（Gold）

このテーブルは BI/分析用途の公開インターフェースとして扱います。

## 2.2 Internal（互換保証なし）

- `stg_orders`
- `stg_products`
- `stg_logistics_centers`
- `int_delivery_cost_candidates`

Internal は実装都合で変更される可能性があるため、下流の直接参照を禁止します。

## 3. 提供保証（SLA/SLO 簡易版）

## 3.1 鮮度（Freshness）

- 対象: `fct_delivery_analysis`
- 目標: 日次更新（`prod-dbt-run` 完了後に最新化）
- 運用目安: 営業日 09:00 までに当日利用可能状態

## 3.2 可用性（Availability）

- 通常提供時間: 24h（計画メンテナンスを除く）
- 計画メンテナンス: 事前に Issue/PR で告知

## 3.3 遅延時ルール

- CI 失敗時は `docs/RUNBOOK.md` に従って復旧
- 下流影響がある場合、Issue で影響範囲と復旧見込みを共有

## 4. スキーマ変更ポリシー

## 4.1 変更種別

- 即時許容（後方互換）:
  - カラム追加（nullable かつ既存意味を壊さない）
- 事前通知必須（破壊的変更）:
  - カラム削除
  - カラム名変更
  - データ型変更
  - 既存カラムの意味変更（単位/定義/算出ロジック変更）

## 4.2 通知・移行期間

- 原則: 変更予定の 2 週間前までに告知
- 告知手段: GitHub Issue または PR 説明
- 必須記載:
  - 変更対象（テーブル/カラム）
  - 互換性への影響
  - 移行期限
  - 回避策（新旧併存、互換列の提供など）

## 4.3 破壊的変更フロー

1. 変更提案 Issue を作成
2. 影響分析（下流利用者/ジョブ/可視化）を記載
3. PR でレビュー（最低 1 名以上）
4. 必要に応じて段階リリース（新列追加 -> 下流移行 -> 旧列削除）
5. `docs/TESTING.md` の品質観点と整合確認
6. `docs/DEPLOYMENT.md` の手順に従って本番反映

## 5. 品質しきい値（Public テーブル）

対象: `fct_delivery_analysis`

- 一意性:
  - `order_id` は重複不可（`unique`）
- 完全性:
  - `order_id` は `not null`
  - `delivery_cost` は `not null`
- 妥当性:
  - `delivery_cost >= 0` を運用上の期待値とする

補足:

- しきい値は運用に応じて見直し可能
- 変更時は PR で根拠と影響範囲を明記する

## 6. インターフェース仕様（Public）

## 6.1 テーブル

- 名称: `fct_delivery_analysis`
- レイヤー: Gold
- 用途: 配送コスト分析の公開ファクト

## 6.2 契約カラム（最小保証）

- `order_id`:
  - 型: 数値
  - 意味: 注文識別子（公開主キー）
  - 制約: `not null`, `unique`
- `delivery_cost`:
  - 型: 数値
  - 意味: 注文に対する最終配送コスト
  - 制約: `not null`

## 6.3 互換性ルール

- 下流利用者は契約カラムへの依存を推奨
- Internal カラムへの依存は自己責任（互換保証なし）

## 7. 依存関係の可視化

```text
raw_data.ORDERS / PRODUCTS / LOGISTICS_CENTERS
  -> stg_orders / stg_products / stg_logistics_centers (Internal)
  -> int_delivery_cost_candidates (Internal)
  -> fct_delivery_analysis (Public)
```

## 8. 監査とエスカレーション

- 契約違反（鮮度遅延、品質逸脱、無通知破壊変更）を検知した場合:
  - Issue 起票
  - 影響範囲と暫定対処を記録
  - 必要に応じて `docs/RUNBOOK.md` に従い復旧

## 9. 関連ドキュメント

- `docs/TESTING.md`（品質検証方針）
- `docs/DEPLOYMENT.md`（本番反映手順）
- `docs/RUNBOOK.md`（障害時復旧）
- `CONTRIBUTING.md`（変更管理ルール）
