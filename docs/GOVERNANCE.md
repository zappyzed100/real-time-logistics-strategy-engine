# GOVERNANCE

このドキュメントは、Snowflake 上の権限モデル、managed access、ネットワーク制御、データ保護の運用基準を定義します。

## 1. 目的

- 権限付与の責務を Terraform と bootstrap SQL に明確に分離する
- 本番環境の誤削除リスクを下げる
- functional role と data-layer access role を分離し、監査しやすい RBAC 階層を維持する

## 2. 適用範囲

- `terraform/modules/snowflake_env/` 配下の Snowflake role / user / warehouse / stage / table / grant 定義
- `terraform/bootstrap/sql/setup_snowflake_tf_dev.sql`
- `terraform/bootstrap/sql/setup_snowflake_tf_prod.sql`
- ルート `GOVERNANCE.md`（参照用の要約版）

## 3. 権限モデル

### 3.1 Functional Role

- Loader role: Bronze への取り込み実行主体
- dbt role: Bronze 読み取り、Silver/Gold 変換実行主体
- Streamlit role: Gold の参照主体

### 3.2 Data-layer Access Role

Terraform では、以下の access role を作成し functional role の下位に付与します。

- `<ENV>_READ_ONLY_ROLE`
- `<ENV>_READ_WRITE_ROLE`

- `<ENV>_BRONZE_LOADER_RW_ROLE`
- `<ENV>_BRONZE_TRANSFORM_RO_ROLE`
- `<ENV>_SILVER_TRANSFORM_RW_ROLE`
- `<ENV>_GOLD_PUBLISH_RW_ROLE`
- `<ENV>_GOLD_CONSUME_RO_ROLE`

階層:

- `READ_ONLY_ROLE` は Streamlit role に付与する
- `READ_WRITE_ROLE` は Loader role / dbt role に付与する
- `READ_WRITE_ROLE` は `READ_ONLY_ROLE` を継承し、更新系ロールが参照権限も内包する
- 各 data-layer access role は `READ_ONLY_ROLE` または `READ_WRITE_ROLE` に付与する

原則:

- オブジェクト権限は access role に付与する
- アプリケーションやユーザーへは functional role を直接割り当てる
- functional role は warehouse 利用権限と access role の束ね役に限定する

### 3.3 汎用 Grant モジュール

`terraform/modules/snowflake_env/modules/schema_object_grants/` に、schema object (TABLES / VIEWS) の権限付与を共通化するサブモジュールを配置する。

- `permission_level` 変数で `SELECT` / `ALL` を切り替える
- `grant_on_all` / `grant_on_future` で既存・将来オブジェクトへの付与範囲を制御する
- 標準運用は `grant_on_future=true` / `grant_on_all=false` とし、外部作成オブジェクト混在時の drift を抑制する
- Terraform が管理する既存テーブルへの権限付与は、`grant_on_all=true` ではなく個別の `snowflake_grant_privileges_to_account_role` リソースで行う。`grant_on_all` (GRANT ON ALL TABLES IN SCHEMA) は dbt DDL との混在環境で state drift の原因となるため使用しない

## 4. Managed Access 方針

- Bronze / Silver / Gold の各 schema は managed access を有効化する
- schema owner は bootstrap で `<ENV>_TF_ADMIN_ROLE` に集約する
- grant の変更は Terraform から行い、手作業の grant 追加は原則禁止とする

補足:

- 既存 schema への適用は `ALTER SCHEMA ... ENABLE MANAGED ACCESS;` で行う
- managed access 適用後、オブジェクト所有者ではなく schema owner が grant を統制する

## 5. ネットワークセキュリティ

- 実行ユーザー / service users に対して、IP allowlist 前提の network policy は標準運用に組み込まない
- 接続保護は JWT/RSA 鍵認証、ロール分離、GitHub Environment 承認で担保する

補足:

- 将来、固定 egress を持つ self-hosted runner / proxy 経路が整備された場合のみ、network policy を再導入候補とする

## 6. データ保護

### 6.1 Time Travel 保持期間

- DEV: `DATA_RETENTION_TIME_IN_DAYS = 7`
- PROD: `DATA_RETENTION_TIME_IN_DAYS = 90`

保持期間の設定は bootstrap SQL で各 Database に適用する。

### 6.2 削除保護

- すべての環境で Bronze raw tables を critical resource とみなし、`prevent_destroy = true` を適用する

対象:

- bronze raw tables

注記:

- 本リポジトリの現行構成では Storage Integration を利用していないため、Storage Integration に対する削除保護は未適用

## 7. 変更管理

- 権限モデル変更は同一 PR で `docs/DECISIONS.md` と ADR を更新する
- managed access や `prevent_destroy` に影響する変更は PR 本文に rollback 方針を記載する
- データ契約に影響する変更は `docs/DATA_CONTRACT.md` も更新する

## 8. 検証観点

- Terraform lint/validate が通ること
- grant 変更後も loader/dbt/streamlit の責務分離が維持されること
- critical resource の destroy plan がブロックされること

## 9. 関連ドキュメント

- `CONTRIBUTING.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/DATA_CONTRACT.md`
- `docs/DEPLOYMENT.md`
- `docs/TESTING.md`
- `terraform/README.md`
- `GOVERNANCE.md`
