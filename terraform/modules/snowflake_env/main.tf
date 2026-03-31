locals {
  env                           = upper(var.env)
  bronze_db_name                = var.bronze_db_name
  silver_db_name                = var.silver_db_name
  gold_db_name                  = var.gold_db_name
  bronze_schema_name            = var.bronze_schema_name
  silver_schema_name            = var.silver_schema_name
  gold_schema_name              = var.gold_schema_name
  terraform_network_policy_name = "${local.env}_TERRAFORM_NETWORK_POLICY"
  read_only_role_name           = "${local.env}_READ_ONLY_ROLE"
  read_write_role_name          = "${local.env}_READ_WRITE_ROLE"
  bronze_loader_rw_role_name    = "${local.env}_BRONZE_LOADER_RW_ROLE"
  bronze_transform_ro_role_name = "${local.env}_BRONZE_TRANSFORM_RO_ROLE"
  silver_transform_rw_role_name = "${local.env}_SILVER_TRANSFORM_RW_ROLE"
  gold_publish_rw_role_name     = "${local.env}_GOLD_PUBLISH_RW_ROLE"
  gold_consume_ro_role_name     = "${local.env}_GOLD_CONSUME_RO_ROLE"
}

resource "snowflake_network_policy" "terraform_access_policy" {
  name            = local.terraform_network_policy_name
  allowed_ip_list = var.network_policy_allowed_ip_list
  blocked_ip_list = var.network_policy_blocked_ip_list
  comment         = "${local.env} environment network policy for service users"
}

# ============================================================
# Roles & Users
# ============================================================

# --- Loader ---
resource "snowflake_account_role" "loader_role" {
  name = var.loader_role_name
}

resource "snowflake_user" "loader_user" {
  name           = var.loader_user_name
  login_name     = var.loader_user_name
  rsa_public_key = var.loader_user_rsa_public_key
  default_role   = snowflake_account_role.loader_role.name
  network_policy = snowflake_network_policy.terraform_access_policy.name
}

resource "snowflake_grant_account_role" "loader_role_grant" {
  role_name = snowflake_account_role.loader_role.name
  user_name = snowflake_user.loader_user.name
}

# --- dbt ---
resource "snowflake_account_role" "dbt_role" {
  name = var.dbt_role_name
}

resource "snowflake_user" "dbt_user" {
  name           = var.dbt_user_name
  login_name     = var.dbt_user_name
  rsa_public_key = var.dbt_user_rsa_public_key
  default_role   = snowflake_account_role.dbt_role.name
  network_policy = snowflake_network_policy.terraform_access_policy.name
}

resource "snowflake_grant_account_role" "dbt_role_grant" {
  role_name = snowflake_account_role.dbt_role.name
  user_name = snowflake_user.dbt_user.name
}

# --- Streamlit Reader ---

resource "snowflake_account_role" "streamlit_role" {
  name = var.streamlit_role_name
}

resource "snowflake_user" "streamlit_user" {
  name       = var.streamlit_user_name
  login_name = var.streamlit_user_name
  # 必要に応じてパスワード認証またはキーペア認証を選択
  rsa_public_key = var.streamlit_user_rsa_public_key
  default_role   = snowflake_account_role.streamlit_role.name
  network_policy = snowflake_network_policy.terraform_access_policy.name
}

resource "snowflake_grant_account_role" "streamlit_role_grant" {
  role_name = snowflake_account_role.streamlit_role.name
  user_name = snowflake_user.streamlit_user.name
}

# --- Shared policy roles ---
resource "snowflake_account_role" "read_only_role" {
  name = local.read_only_role_name
}

resource "snowflake_account_role" "read_write_role" {
  name = local.read_write_role_name
}

resource "snowflake_grant_account_role" "read_only_to_streamlit_role" {
  role_name        = snowflake_account_role.read_only_role.name
  parent_role_name = snowflake_account_role.streamlit_role.name
}

resource "snowflake_grant_account_role" "read_write_to_loader_role" {
  role_name        = snowflake_account_role.read_write_role.name
  parent_role_name = snowflake_account_role.loader_role.name
}

resource "snowflake_grant_account_role" "read_write_to_dbt_role" {
  role_name        = snowflake_account_role.read_write_role.name
  parent_role_name = snowflake_account_role.dbt_role.name
}

resource "snowflake_grant_account_role" "read_only_to_read_write_role" {
  role_name        = snowflake_account_role.read_only_role.name
  parent_role_name = snowflake_account_role.read_write_role.name
}

# --- Shared access roles ---
resource "snowflake_account_role" "bronze_loader_rw_role" {
  name = local.bronze_loader_rw_role_name
}

resource "snowflake_account_role" "bronze_transform_ro_role" {
  name = local.bronze_transform_ro_role_name
}

resource "snowflake_account_role" "silver_transform_rw_role" {
  name = local.silver_transform_rw_role_name
}

resource "snowflake_account_role" "gold_publish_rw_role" {
  name = local.gold_publish_rw_role_name
}

resource "snowflake_account_role" "gold_consume_ro_role" {
  name = local.gold_consume_ro_role_name
}

resource "snowflake_grant_account_role" "bronze_loader_rw_to_loader_role" {
  role_name        = snowflake_account_role.bronze_loader_rw_role.name
  parent_role_name = snowflake_account_role.read_write_role.name
}

resource "snowflake_grant_account_role" "bronze_transform_ro_to_dbt_role" {
  role_name        = snowflake_account_role.bronze_transform_ro_role.name
  parent_role_name = snowflake_account_role.read_only_role.name
}

resource "snowflake_grant_account_role" "silver_transform_rw_to_dbt_role" {
  role_name        = snowflake_account_role.silver_transform_rw_role.name
  parent_role_name = snowflake_account_role.read_write_role.name
}

resource "snowflake_grant_account_role" "gold_publish_rw_to_dbt_role" {
  role_name        = snowflake_account_role.gold_publish_rw_role.name
  parent_role_name = snowflake_account_role.read_write_role.name
}

resource "snowflake_grant_account_role" "gold_consume_ro_to_streamlit_role" {
  role_name        = snowflake_account_role.gold_consume_ro_role.name
  parent_role_name = snowflake_account_role.read_only_role.name
}

# ============================================================
# Warehouses
# ============================================================

# ============================================================
# Databases / Schemas
# ============================================================

resource "snowflake_database" "bronze_db" {
  name                        = local.bronze_db_name
  data_retention_time_in_days = var.db_data_retention_days

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_database" "silver_db" {
  name                        = local.silver_db_name
  data_retention_time_in_days = var.db_data_retention_days

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_database" "gold_db" {
  name                        = local.gold_db_name
  data_retention_time_in_days = var.db_data_retention_days

  lifecycle {
    prevent_destroy = true
  }
}

resource "snowflake_schema" "bronze_schema" {
  database            = snowflake_database.bronze_db.name
  name                = local.bronze_schema_name
  is_transient        = var.schema_is_transient
  with_managed_access = var.schema_with_managed_access

  lifecycle {
    prevent_destroy = true
    # with_managed_access は apply 後に provider が "true" へ書き換えるため差分を無視する
    # （Snowflake provider v2.x の既知の挙動。bootstrap SQL で MANAGED ACCESS を設定済みの場合に発生）
    ignore_changes = [with_managed_access]
  }
}

resource "snowflake_schema" "silver_schema" {
  database            = snowflake_database.silver_db.name
  name                = local.silver_schema_name
  is_transient        = var.schema_is_transient
  with_managed_access = var.schema_with_managed_access

  lifecycle {
    prevent_destroy = true
    # with_managed_access は apply 後に provider が "true" へ書き換えるため差分を無視する
    # （Snowflake provider v2.x の既知の挙動。bootstrap SQL で MANAGED ACCESS を設定済みの場合に発生）
    ignore_changes = [with_managed_access]
  }
}

resource "snowflake_schema" "gold_schema" {
  database            = snowflake_database.gold_db.name
  name                = local.gold_schema_name
  is_transient        = var.schema_is_transient
  with_managed_access = var.schema_with_managed_access

  lifecycle {
    prevent_destroy = true
    # with_managed_access は apply 後に provider が "true" へ書き換えるため差分を無視する
    # （Snowflake provider v2.x の既知の挙動。bootstrap SQL で MANAGED ACCESS を設定済みの場合に発生）
    ignore_changes = [with_managed_access]
  }
}

resource "snowflake_warehouse" "loader_wh" {
  name                = var.loader_warehouse_name
  warehouse_size      = var.warehouse_size
  auto_suspend        = var.warehouse_auto_suspend
  auto_resume         = var.warehouse_auto_resume
  initially_suspended = var.warehouse_initially_suspended
}

resource "snowflake_warehouse" "dbt_wh" {
  name                = var.dbt_warehouse_name
  warehouse_size      = var.warehouse_size
  auto_suspend        = var.warehouse_auto_suspend
  auto_resume         = var.warehouse_auto_resume
  initially_suspended = var.warehouse_initially_suspended
}

resource "snowflake_warehouse" "streamlit_wh" {
  name                = var.streamlit_warehouse_name
  warehouse_size      = var.warehouse_size
  auto_suspend        = var.warehouse_auto_suspend
  auto_resume         = var.warehouse_auto_resume
  initially_suspended = var.warehouse_initially_suspended
}

# ============================================================
# Stage
# ============================================================

# 内部ステージ（PUTコマンドの宛先）
resource "snowflake_stage_internal" "bronze_raw_stage" {
  name     = var.bronze_stage_name
  database = snowflake_schema.bronze_schema.database
  schema   = snowflake_schema.bronze_schema.name

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [snowflake_schema.bronze_schema]
}

# ============================================================
# Tables (Bronze / RAW Layer)
# ============================================================

resource "snowflake_table" "orders" {
  database = snowflake_schema.bronze_schema.database
  schema   = snowflake_schema.bronze_schema.name
  name     = "ORDERS"

  lifecycle {
    prevent_destroy = true
  }

  # ID類も一旦 STRING で受けることで、予期せぬ文字列混入による停止を防ぐ
  column {
    name     = "ORDER_ID"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "PRODUCT_ID"
    type     = "STRING"
    nullable = true
  }
  # 数値型も、一旦 STRING で受けて Silver で CAST するのが最も堅牢
  column {
    name     = "QUANTITY"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "CUSTOMER_LAT"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "CUSTOMER_LON"
    type     = "STRING"
    nullable = true
  }
  # 日付もフォーマット違いを許容するために STRING
  column {
    name     = "ORDER_DATE"
    type     = "STRING"
    nullable = true
  }
  column {
    name    = "SOURCE_FILE"
    type    = "STRING"
    comment = "取り込み元のファイル名"
  }
  # 取り込み日時（メタデータ）：いつ届いたデータか判別するため
  column {
    name = "LOADED_AT"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}

resource "snowflake_table" "inventory" {
  database = snowflake_schema.bronze_schema.database
  schema   = snowflake_schema.bronze_schema.name
  name     = "INVENTORY"

  lifecycle {
    prevent_destroy = true
  }

  column {
    name     = "CENTER_ID"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "PRODUCT_ID"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "STOCK_QUANTITY"
    type     = "STRING"
    nullable = true
  }
  column {
    name    = "SOURCE_FILE"
    type    = "STRING"
    comment = "取り込み元のファイル名"
  }
  column {
    name = "LOADED_AT"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}

resource "snowflake_table" "logistics_centers" {
  database = snowflake_schema.bronze_schema.database
  schema   = snowflake_schema.bronze_schema.name
  name     = "LOGISTICS_CENTERS"

  lifecycle {
    prevent_destroy = true
  }

  column {
    name     = "CENTER_ID"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "CENTER_NAME"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "LATITUDE"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "LONGITUDE"
    type     = "STRING"
    nullable = true
  }
  column {
    name    = "SOURCE_FILE"
    type    = "STRING"
    comment = "取り込み元のファイル名"
  }
  column {
    name = "LOADED_AT"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}

resource "snowflake_table" "products" {
  database = snowflake_schema.bronze_schema.database
  schema   = snowflake_schema.bronze_schema.name
  name     = "PRODUCTS"

  lifecycle {
    prevent_destroy = true
  }

  column {
    name     = "PRODUCT_ID"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "PRODUCT_NAME"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "CATEGORY"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "WEIGHT_KG"
    type     = "STRING"
    nullable = true
  }
  column {
    name     = "UNIT_PRICE"
    type     = "STRING"
    nullable = true
  }
  column {
    name    = "SOURCE_FILE"
    type    = "STRING"
    comment = "取り込み元のファイル名"
  }
  column {
    name = "LOADED_AT"
    type = "TIMESTAMP_NTZ"
    default {
      expression = "CURRENT_TIMESTAMP()"
    }
  }
}

# ============================================================
# File Format
# ============================================================

resource "snowflake_file_format" "csv_format" {
  name        = var.loader_file_format_name
  database    = snowflake_schema.bronze_schema.database
  schema      = snowflake_schema.bronze_schema.name
  format_type = var.file_format_type

  field_delimiter              = var.file_format_field_delimiter
  skip_header                  = var.file_format_skip_header
  trim_space                   = var.file_format_trim_space
  field_optionally_enclosed_by = var.file_format_field_optionally_enclosed_by
  null_if                      = var.file_format_null_if

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [snowflake_schema.bronze_schema]
}

# ============================================================
# Grants — Loader Role
# ============================================================

# ------ warehouse ------
resource "snowflake_grant_privileges_to_account_role" "loader_wh_usage" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.loader_wh.name
  }
}

# ------ bronze ------
resource "snowflake_grant_privileges_to_account_role" "loader_bronze_db_usage" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = local.bronze_db_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_raw_schema_usage" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${local.bronze_db_name}.${local.bronze_schema_name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_stage_read_write" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["READ", "WRITE"]

  on_schema_object {
    object_type = "STAGE"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_stage_internal.bronze_raw_stage.name}"
  }
}

# ------ tables ------
resource "snowflake_grant_privileges_to_account_role" "loader_orders_insert" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_table.orders.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_inventory_insert" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_table.inventory.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_logistics_insert" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_table.logistics_centers.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_products_insert" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_table.products.name}"
  }
}

# ------ file format ------
resource "snowflake_grant_privileges_to_account_role" "loader_ff_usage" {
  account_role_name = snowflake_account_role.bronze_loader_rw_role.name
  privileges        = ["USAGE"]

  on_schema_object {
    object_type = "FILE FORMAT"
    object_name = "${local.bronze_db_name}.${local.bronze_schema_name}.${snowflake_file_format.csv_format.name}"
  }
}

# ============================================================
# Grants — dbt Role
# ============================================================

# ------ warehouse ------
resource "snowflake_grant_privileges_to_account_role" "dbt_wh_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.dbt_wh.name
  }
}

# ------ bronze ------
resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_db_usage" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = local.bronze_db_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_raw_usage" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${snowflake_schema.bronze_schema.database}.${snowflake_schema.bronze_schema.name}"
  }
}

module "dbt_bronze_table_grants" {
  source = "./modules/schema_object_grants"

  # grant_on_all は使用しない。
  # Terraform 管理テーブルへの SELECT は下の個別リソースで付与し、
  # 将来 dbt や Terraform が追加するテーブルは grant_on_future でカバーする。
  # これにより dbt DDL 混在環境での state drift を防ぐ。
  account_role_name  = snowflake_account_role.bronze_transform_ro_role.name
  in_schema          = "${snowflake_schema.bronze_schema.database}.${snowflake_schema.bronze_schema.name}"
  object_type_plural = "TABLES"
  permission_level   = "SELECT"
  grant_on_all       = false
  grant_on_future    = true
}

# Terraform が管理する Bronze テーブル 4 本への明示的 SELECT 付与。
# grant_on_all (ON ALL TABLES IN SCHEMA) はスナップショット操作のため、
# dbt が新テーブルを作るたびに plan 差分が出る drift の温床になる。
# 代わりにリソース参照で個別付与することで state を安定させる。
resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select_orders" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["SELECT"]
  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_table.orders.database}.${snowflake_table.orders.schema}.${snowflake_table.orders.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select_inventory" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["SELECT"]
  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_table.inventory.database}.${snowflake_table.inventory.schema}.${snowflake_table.inventory.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select_logistics_centers" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["SELECT"]
  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_table.logistics_centers.database}.${snowflake_table.logistics_centers.schema}.${snowflake_table.logistics_centers.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select_products" {
  account_role_name = snowflake_account_role.bronze_transform_ro_role.name
  privileges        = ["SELECT"]
  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_table.products.database}.${snowflake_table.products.schema}.${snowflake_table.products.name}"
  }
}

# ------ silver ------
resource "snowflake_grant_privileges_to_account_role" "dbt_silver_db_usage" {
  account_role_name = snowflake_account_role.silver_transform_rw_role.name
  privileges        = ["USAGE", "CREATE SCHEMA"]

  on_account_object {
    object_type = "DATABASE"
    object_name = local.silver_db_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_silver_usage" {
  account_role_name = snowflake_account_role.silver_transform_rw_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.silver_db.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_cleansed_all" {
  account_role_name = snowflake_account_role.silver_transform_rw_role.name
  # dbt が Silver スキーマで必要な権限を明示指定。all_privileges は将来の権限追加時に自動付与されるため不使用
  privileges = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE",
    "CREATE SEQUENCE", "CREATE FUNCTION", "CREATE PROCEDURE",
  "MODIFY", "MONITOR"]

  on_schema {
    schema_name = "${snowflake_schema.silver_schema.database}.${snowflake_schema.silver_schema.name}"
  }
}

# ------ gold ------
resource "snowflake_grant_privileges_to_account_role" "dbt_gold_db_usage" {
  account_role_name = snowflake_account_role.gold_publish_rw_role.name
  privileges        = ["USAGE", "CREATE SCHEMA"]

  on_account_object {
    object_type = "DATABASE"
    object_name = local.gold_db_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_gold_usage" {
  account_role_name = snowflake_account_role.gold_publish_rw_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.gold_db.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_mart_all" {
  account_role_name = snowflake_account_role.gold_publish_rw_role.name
  # dbt が Gold スキーマで必要な権限を明示指定。all_privileges は将来の権限追加時に自動付与されるため不使用
  privileges = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE STAGE",
    "CREATE SEQUENCE", "CREATE FUNCTION", "CREATE PROCEDURE",
  "MODIFY", "MONITOR"]

  on_schema {
    schema_name = "${snowflake_schema.gold_schema.database}.${snowflake_schema.gold_schema.name}"
  }
}

# ============================================================
# Grants — streamlit Role
# ============================================================

# --- warehouse ---
resource "snowflake_grant_privileges_to_account_role" "streamlit_wh_usage" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.streamlit_wh.name
  }
}

# --- gold ---
# データベースへのアクセス権限
resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_db_usage" {
  account_role_name = snowflake_account_role.gold_consume_ro_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = local.gold_db_name
  }
}

# ターゲットスキーマへのアクセス権限
resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_usage" {
  account_role_name = snowflake_account_role.gold_consume_ro_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${snowflake_schema.gold_schema.database}.${snowflake_schema.gold_schema.name}"
  }
}

# --- SELECT Privileges (Current & Future) ---
# 既存および将来作成される全てのテーブルへの参照権限
module "streamlit_gold_table_grants" {
  source = "./modules/schema_object_grants"

  account_role_name  = snowflake_account_role.gold_consume_ro_role.name
  in_schema          = "${snowflake_schema.gold_schema.database}.${snowflake_schema.gold_schema.name}"
  object_type_plural = "TABLES"
  permission_level   = "SELECT"
  grant_on_all       = false
  grant_on_future    = true
}

# 既存および将来作成される全てのビューへの参照権限
module "streamlit_gold_view_grants" {
  source = "./modules/schema_object_grants"

  account_role_name  = snowflake_account_role.gold_consume_ro_role.name
  in_schema          = "${snowflake_schema.gold_schema.database}.${snowflake_schema.gold_schema.name}"
  object_type_plural = "VIEWS"
  permission_level   = "SELECT"
  grant_on_all       = false
  grant_on_future    = true
}