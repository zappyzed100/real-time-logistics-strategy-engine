locals {
  env = upper(var.env)
}

# ============================================================
# Roles & Users
# ============================================================

# --- Loader ---
resource "snowflake_account_role" "loader_role" {
  name = "${local.env}_LOADER_ROLE"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_user" "loader_user" {
  name         = "${local.env}_LOADER_USER"
  login_name   = "${local.env}_LOADER_USER"
  rsa_public_key = var.loader_user_rsa_public_key
  default_role = snowflake_account_role.loader_role.name

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_grant_account_role" "loader_role_grant" {
  role_name = snowflake_account_role.loader_role.name
  user_name = snowflake_user.loader_user.name
}

# --- dbt ---
resource "snowflake_account_role" "dbt_role" {
  name = "${local.env}_DBT_ROLE"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_user" "dbt_user" {
  name         = "${local.env}_DBT_USER"
  login_name   = "${local.env}_DBT_USER"
  rsa_public_key = var.dbt_user_rsa_public_key
  default_role = snowflake_account_role.dbt_role.name

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_grant_account_role" "dbt_role_grant" {
  role_name = snowflake_account_role.dbt_role.name
  user_name = snowflake_user.dbt_user.name
}

# --- Streamlit Reader ---

resource "snowflake_account_role" "streamlit_role" {
  name = "${local.env}_STREAMLIT_READ_ROLE"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_user" "streamlit_user" {
  name            = "${local.env}_STREAMLIT_USER"
  login_name      = "${local.env}_STREAMLIT_USER"
  # 必要に応じてパスワード認証またはキーペア認証を選択
  rsa_public_key  = var.streamlit_user_rsa_public_key 
  default_role    = snowflake_account_role.streamlit_role.name
  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_grant_account_role" "streamlit_role_grant" {
  role_name = snowflake_account_role.streamlit_role.name
  user_name = snowflake_user.streamlit_user.name
}

# ============================================================
# Warehouses
# ============================================================

resource "snowflake_warehouse" "loader_wh" {
  name                = "${local.env}_LOADER_WH"
  warehouse_size      = "X-SMALL"     # 最小サイズ（コスト最適化）
  auto_suspend        = 60            # 60秒間クエリがないと自動停止
  auto_resume         = true          # クエリが来たら自動で再起動
  initially_suspended = true          # 作成直後は停止状態にする

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_warehouse" "dbt_wh" {
  name                = "${local.env}_DBT_WH"
  warehouse_size      = "X-SMALL"
  auto_suspend        = 60
  auto_resume         = true
  initially_suspended = true
  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_warehouse" "streamlit_wh" {
  name                = "${local.env}_STREAMLIT_WH"
  warehouse_size      = "X-SMALL"
  auto_suspend        = 60
  auto_resume         = true
  initially_suspended = true
  lifecycle {
    prevent_destroy = false
  }
}

# ============================================================
# Databases & Schemas
# ============================================================

# --- Bronze Layer (生データ) ---
resource "snowflake_database" "bronze" {
  name = "${local.env}_BRONZE_DB"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_schema" "bronze_raw" {
  database = snowflake_database.bronze.name
  name     = "RAW_DATA" # 外部から取り込んだそのままのデータが入る場所

  lifecycle {
    prevent_destroy = false
  }
}

# --- Silver Layer (中間加工) ---
resource "snowflake_database" "silver" {
  name = "${local.env}_SILVER_DB"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_schema" "silver_cleansed" {
  database = snowflake_database.silver.name
  name     = "CLEANSED" # 型変換やクレンジング後のデータ

  lifecycle {
    prevent_destroy = false
  }
}

# --- Gold Layer (展示層) ---
resource "snowflake_database" "gold" {
  name = "${local.env}_GOLD_DB"

  lifecycle {
    prevent_destroy = false
  }
}

resource "snowflake_schema" "gold_mart" {
  database = snowflake_database.gold.name
  name     = "MARKETING_MART"

  lifecycle {
    prevent_destroy = false
  }
}

# ============================================================
# Stage
# ============================================================

# 内部ステージ（PUTコマンドの宛先）
resource "snowflake_stage_internal" "bronze_raw_stage" {
  name     = "${local.env}_BRONZE_RAW_STAGE"
  database = snowflake_database.bronze.name
  schema   = snowflake_schema.bronze_raw.name
}

# ============================================================
# Tables (Bronze / RAW Layer)
# ============================================================

resource "snowflake_table" "orders" {
  database = snowflake_database.bronze.name
  schema   = snowflake_schema.bronze_raw.name
  name     = "ORDERS"

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
  database = snowflake_database.bronze.name
  schema   = snowflake_schema.bronze_raw.name
  name     = "INVENTORY"

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
  database = snowflake_database.bronze.name
  schema   = snowflake_schema.bronze_raw.name
  name     = "LOGISTICS_CENTERS"

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
  database = snowflake_database.bronze.name
  schema   = snowflake_schema.bronze_raw.name
  name     = "PRODUCTS"

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
  name        = "${local.env}_CSV_FORMAT"
  database    = snowflake_database.bronze.name
  schema      = snowflake_schema.bronze_raw.name
  format_type = "CSV"

  field_delimiter              = ","
  skip_header                  = 1
  trim_space                   = true
  field_optionally_enclosed_by = "\"" # 囲み文字がある場合
  null_if                      = ["NULL", ""]
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
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.bronze.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_bronze_usage" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.bronze.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_raw_schema_usage" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_stage_read_write" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["READ", "WRITE"]

  on_schema_object {
    object_type = "STAGE"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_stage_internal.bronze_raw_stage.name}"
  }
}

# ------ tables ------
resource "snowflake_grant_privileges_to_account_role" "loader_orders_insert" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_table.orders.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_inventory_insert" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_table.inventory.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_logistics_insert" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_table.logistics_centers.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "loader_products_insert" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["INSERT"]

  on_schema_object {
    object_type = "TABLE"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_table.products.name}"
  }
}

# ------ file format ------
resource "snowflake_grant_privileges_to_account_role" "loader_ff_usage" {
  account_role_name = snowflake_account_role.loader_role.name
  privileges        = ["USAGE"]

  on_schema_object {
    object_type = "FILE FORMAT"
    object_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}.${snowflake_file_format.csv_format.name}"
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
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.bronze.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.bronze.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_raw_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}"
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}"
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_bronze_select_future" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.bronze.name}.${snowflake_schema.bronze_raw.name}"
    }
  }
}

# ------ silver ------
resource "snowflake_grant_privileges_to_account_role" "dbt_silver_db_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE", "CREATE SCHEMA"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.silver.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_silver_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.silver.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_cleansed_all" {
  account_role_name = snowflake_account_role.dbt_role.name
  all_privileges    = true

  on_schema {
    schema_name = "${snowflake_database.silver.name}.${snowflake_schema.silver_cleansed.name}"
  }
}

# ------ gold ------
resource "snowflake_grant_privileges_to_account_role" "dbt_gold_db_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE", "CREATE SCHEMA"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.gold.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_gold_usage" {
  account_role_name = snowflake_account_role.dbt_role.name
  privileges        = ["USAGE"]

  on_schema {
    all_schemas_in_database = snowflake_database.gold.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "dbt_mart_all" {
  account_role_name = snowflake_account_role.dbt_role.name
  all_privileges    = true

  on_schema {
    schema_name = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
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
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["USAGE"]

  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.gold.name
  }
}

# ターゲットスキーマへのアクセス権限
resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_usage" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["USAGE"]

  on_schema {
    schema_name = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
  }
}

# --- SELECT Privileges (Current & Future) ---
# 既存および将来作成される全てのテーブルへの参照権限
resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_tables_select" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_future_tables_select" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
    }
  }
}

# 既存および将来作成される全てのビューへの参照権限
resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_views_select" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    all {
      object_type_plural = "VIEWS"
      in_schema          = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "streamlit_gold_mart_future_views_select" {
  account_role_name = snowflake_account_role.streamlit_role.name
  privileges        = ["SELECT"]

  on_schema_object {
    future {
      object_type_plural = "VIEWS"
      in_schema          = "${snowflake_database.gold.name}.${snowflake_schema.gold_mart.name}"
    }
  }
}

# ============================================================
# Network Policy
# ============================================================

# ネットワークポリシー本体の定義
# resource "snowflake_network_policy" "api_access_policy" {
#   name    = "${local.env}_API_NETWORK_POLICY"
#   comment = "Allow access from specific CIDR blocks"
# 
#  # 例：特定のVPCやオフィスのIP
#   allowed_ip_list = ["1.2.3.4/32", "192.168.0.0/24"]
#    lifecycle {
#      prevent_destroy = false
#    }
# }

# ユーザーへの適用
# resource "snowflake_user_public_keys" "loader_user_network" {
#   # ...（既存のユーザー設定）...
# }