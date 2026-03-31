locals {
  app_env_upper = upper(var.app_env)
  env           = local.app_env_upper

  env_config = {
    DEV = {
      tf_admin_role              = var.DEV_TF_ADMIN_ROLE
      db_data_retention_days     = var.DEV_DB_DATA_RETENTION_DAYS
      bronze_db_name             = var.DEV_BRONZE_DB
      silver_db_name             = var.DEV_SILVER_DB
      gold_db_name               = var.DEV_GOLD_DB
      loader_user_name           = var.DEV_LOADER_USER
      loader_role_name           = var.DEV_LOADER_ROLE
      loader_warehouse_name      = var.DEV_LOADER_WH
      loader_file_format_name    = var.DEV_LOADER_FILE_FORMAT_NAME
      dbt_user_name              = var.DEV_DBT_USER
      dbt_role_name              = var.DEV_DBT_ROLE
      dbt_warehouse_name         = var.DEV_DBT_WH
      streamlit_user_name        = var.DEV_STREAMLIT_USER
      streamlit_role_name        = var.DEV_STREAMLIT_ROLE
      streamlit_warehouse_name   = var.DEV_STREAMLIT_WH
      network_policy_allowed_ips = var.DEV_NETWORK_POLICY_ALLOWED_IPS
      network_policy_blocked_ips = var.DEV_NETWORK_POLICY_BLOCKED_IPS
    }
    PROD = {
      tf_admin_role              = var.PROD_TF_ADMIN_ROLE
      db_data_retention_days     = var.PROD_DB_DATA_RETENTION_DAYS
      bronze_db_name             = var.PROD_BRONZE_DB
      silver_db_name             = var.PROD_SILVER_DB
      gold_db_name               = var.PROD_GOLD_DB
      loader_user_name           = var.PROD_LOADER_USER
      loader_role_name           = var.PROD_LOADER_ROLE
      loader_warehouse_name      = var.PROD_LOADER_WH
      loader_file_format_name    = var.PROD_LOADER_FILE_FORMAT_NAME
      dbt_user_name              = var.PROD_DBT_USER
      dbt_role_name              = var.PROD_DBT_ROLE
      dbt_warehouse_name         = var.PROD_DBT_WH
      streamlit_user_name        = var.PROD_STREAMLIT_USER
      streamlit_role_name        = var.PROD_STREAMLIT_ROLE
      streamlit_warehouse_name   = var.PROD_STREAMLIT_WH
      network_policy_allowed_ips = var.PROD_NETWORK_POLICY_ALLOWED_IPS
      network_policy_blocked_ips = var.PROD_NETWORK_POLICY_BLOCKED_IPS
    }
  }

  selected_env = local.env_config[local.app_env_upper]

  tf_admin_role              = local.selected_env.tf_admin_role
  db_data_retention_days     = local.selected_env.db_data_retention_days
  schema_is_transient        = var.SNOWFLAKE_SCHEMA_IS_TRANSIENT
  schema_with_managed_access = var.SNOWFLAKE_SCHEMA_WITH_MANAGED_ACCESS

  bronze_db_name     = local.selected_env.bronze_db_name
  silver_db_name     = local.selected_env.silver_db_name
  gold_db_name       = local.selected_env.gold_db_name
  bronze_schema_name = var.SNOWFLAKE_BRONZE_SCHEMA
  silver_schema_name = var.SNOWFLAKE_SILVER_SCHEMA
  gold_schema_name   = var.SNOWFLAKE_GOLD_SCHEMA
  bronze_stage_name  = var.SNOWFLAKE_BRONZE_STAGE

  loader_user_name        = local.selected_env.loader_user_name
  loader_role_name        = local.selected_env.loader_role_name
  loader_warehouse_name   = local.selected_env.loader_warehouse_name
  loader_file_format_name = local.selected_env.loader_file_format_name

  dbt_user_name      = local.selected_env.dbt_user_name
  dbt_role_name      = local.selected_env.dbt_role_name
  dbt_warehouse_name = local.selected_env.dbt_warehouse_name

  streamlit_user_name                      = local.selected_env.streamlit_user_name
  streamlit_role_name                      = local.selected_env.streamlit_role_name
  streamlit_warehouse_name                 = local.selected_env.streamlit_warehouse_name
  warehouse_size                           = var.SNOWFLAKE_WAREHOUSE_SIZE
  warehouse_auto_suspend                   = var.SNOWFLAKE_WAREHOUSE_AUTO_SUSPEND_SECONDS
  warehouse_auto_resume                    = var.SNOWFLAKE_WAREHOUSE_AUTO_RESUME
  warehouse_initially_suspended            = var.SNOWFLAKE_WAREHOUSE_INITIALLY_SUSPENDED
  file_format_type                         = var.SNOWFLAKE_FILE_FORMAT_TYPE
  file_format_field_delimiter              = var.SNOWFLAKE_FILE_FORMAT_FIELD_DELIMITER
  file_format_skip_header                  = var.SNOWFLAKE_FILE_FORMAT_SKIP_HEADER
  file_format_trim_space                   = var.SNOWFLAKE_FILE_FORMAT_TRIM_SPACE
  file_format_field_optionally_enclosed_by = upper(var.SNOWFLAKE_FILE_FORMAT_FIELD_OPTIONALLY_ENCLOSED_BY) == "DOUBLE_QUOTE" ? "\"" : var.SNOWFLAKE_FILE_FORMAT_FIELD_OPTIONALLY_ENCLOSED_BY
  file_format_null_if                      = var.SNOWFLAKE_FILE_FORMAT_NULL_IF
  network_policy_allowed_ips               = local.selected_env.network_policy_allowed_ips
  network_policy_blocked_ips               = local.selected_env.network_policy_blocked_ips

  # HCP Workspace Variables から受け取る値（各ワークスペースで設定）
  selected_loader_user_rsa_public_key    = var.loader_user_rsa_public_key
  selected_dbt_user_rsa_public_key       = var.dbt_user_rsa_public_key
  selected_streamlit_user_rsa_public_key = var.streamlit_user_rsa_public_key
}

check "env_resource_prefix_alignment" {
  assert {
    condition = alltrue([
      startswith(upper(local.loader_user_name), "${local.app_env_upper}_"),
      startswith(upper(local.loader_role_name), "${local.app_env_upper}_"),
      startswith(upper(local.loader_warehouse_name), "${local.app_env_upper}_"),
      startswith(upper(local.dbt_user_name), "${local.app_env_upper}_"),
      startswith(upper(local.dbt_role_name), "${local.app_env_upper}_"),
      startswith(upper(local.dbt_warehouse_name), "${local.app_env_upper}_"),
      startswith(upper(local.streamlit_user_name), "${local.app_env_upper}_"),
      startswith(upper(local.streamlit_role_name), "${local.app_env_upper}_"),
      startswith(upper(local.streamlit_warehouse_name), "${local.app_env_upper}_"),
      startswith(upper(local.bronze_db_name), "${local.app_env_upper}_"),
      startswith(upper(local.silver_db_name), "${local.app_env_upper}_"),
      startswith(upper(local.gold_db_name), "${local.app_env_upper}_"),
    ])
    error_message = "app_env と選択されたリソース名プレフィックスが不一致です。HCP Workspace Variables (app_env / *_USER / *_ROLE / *_DB) を確認してください。"
  }
}

# module 名を dev -> snowflake_env へ変更した際の state 移行
moved {
  from = module.dev
  to   = module.snowflake_env
}

# ============================================================
# bootstrap SQL で作成済みのオブジェクトを state へ取り込む
# ============================================================
import {
  to = module.snowflake_env.snowflake_database.bronze_db
  id = local.bronze_db_name
}

import {
  to = module.snowflake_env.snowflake_database.silver_db
  id = local.silver_db_name
}

import {
  to = module.snowflake_env.snowflake_database.gold_db
  id = local.gold_db_name
}

import {
  to = module.snowflake_env.snowflake_schema.bronze_schema
  id = "\"${local.bronze_db_name}\".\"${local.bronze_schema_name}\""
}

import {
  to = module.snowflake_env.snowflake_schema.silver_schema
  id = "\"${local.silver_db_name}\".\"${local.silver_schema_name}\""
}

import {
  to = module.snowflake_env.snowflake_schema.gold_schema
  id = "\"${local.gold_db_name}\".\"${local.gold_schema_name}\""
}

# APP_ENV に応じて DEV / PROD の Snowflake リソースを作成
module "snowflake_env" {
  source = "./modules/snowflake_env"

  env                                      = local.env
  db_data_retention_days                   = local.db_data_retention_days
  schema_is_transient                      = local.schema_is_transient
  schema_with_managed_access               = local.schema_with_managed_access
  bronze_db_name                           = local.bronze_db_name
  silver_db_name                           = local.silver_db_name
  gold_db_name                             = local.gold_db_name
  bronze_schema_name                       = local.bronze_schema_name
  silver_schema_name                       = local.silver_schema_name
  gold_schema_name                         = local.gold_schema_name
  bronze_stage_name                        = local.bronze_stage_name
  loader_user_name                         = local.loader_user_name
  loader_role_name                         = local.loader_role_name
  loader_warehouse_name                    = local.loader_warehouse_name
  loader_file_format_name                  = local.loader_file_format_name
  dbt_user_name                            = local.dbt_user_name
  dbt_role_name                            = local.dbt_role_name
  dbt_warehouse_name                       = local.dbt_warehouse_name
  streamlit_user_name                      = local.streamlit_user_name
  streamlit_role_name                      = local.streamlit_role_name
  streamlit_warehouse_name                 = local.streamlit_warehouse_name
  warehouse_size                           = local.warehouse_size
  warehouse_auto_suspend                   = local.warehouse_auto_suspend
  warehouse_auto_resume                    = local.warehouse_auto_resume
  warehouse_initially_suspended            = local.warehouse_initially_suspended
  file_format_type                         = local.file_format_type
  file_format_field_delimiter              = local.file_format_field_delimiter
  file_format_skip_header                  = local.file_format_skip_header
  file_format_trim_space                   = local.file_format_trim_space
  file_format_field_optionally_enclosed_by = local.file_format_field_optionally_enclosed_by
  file_format_null_if                      = local.file_format_null_if
  loader_user_rsa_public_key               = local.selected_loader_user_rsa_public_key
  dbt_user_rsa_public_key                  = local.selected_dbt_user_rsa_public_key
  streamlit_user_rsa_public_key            = local.selected_streamlit_user_rsa_public_key
  network_policy_allowed_ip_list           = local.network_policy_allowed_ips
  network_policy_blocked_ip_list           = local.network_policy_blocked_ips
}
