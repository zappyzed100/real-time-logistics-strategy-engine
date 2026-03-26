locals {
  app_env_upper = upper(var.app_env)
  env           = local.app_env_upper

  tf_admin_role = local.app_env_upper == "PROD" ? var.PROD_TF_ADMIN_ROLE : var.DEV_TF_ADMIN_ROLE

  bronze_db_name     = local.app_env_upper == "PROD" ? var.PROD_BRONZE_DB : var.DEV_BRONZE_DB
  silver_db_name     = local.app_env_upper == "PROD" ? var.PROD_SILVER_DB : var.DEV_SILVER_DB
  gold_db_name       = local.app_env_upper == "PROD" ? var.PROD_GOLD_DB : var.DEV_GOLD_DB
  bronze_schema_name = var.SNOWFLAKE_BRONZE_SCHEMA
  silver_schema_name = var.SNOWFLAKE_SILVER_SCHEMA
  gold_schema_name   = var.SNOWFLAKE_GOLD_SCHEMA
  bronze_stage_name  = var.SNOWFLAKE_BRONZE_STAGE

  loader_user_name        = local.app_env_upper == "PROD" ? var.PROD_LOADER_USER : var.DEV_LOADER_USER
  loader_role_name        = local.app_env_upper == "PROD" ? var.PROD_LOADER_ROLE : var.DEV_LOADER_ROLE
  loader_warehouse_name   = local.app_env_upper == "PROD" ? var.PROD_LOADER_WH : var.DEV_LOADER_WH
  loader_file_format_name = local.app_env_upper == "PROD" ? var.PROD_LOADER_FILE_FORMAT_NAME : var.DEV_LOADER_FILE_FORMAT_NAME

  dbt_user_name      = local.app_env_upper == "PROD" ? var.PROD_DBT_USER : var.DEV_DBT_USER
  dbt_role_name      = local.app_env_upper == "PROD" ? var.PROD_DBT_ROLE : var.DEV_DBT_ROLE
  dbt_warehouse_name = local.app_env_upper == "PROD" ? var.PROD_DBT_WH : var.DEV_DBT_WH

  streamlit_user_name      = local.app_env_upper == "PROD" ? var.PROD_STREAMLIT_USER : var.DEV_STREAMLIT_USER
  streamlit_role_name      = local.app_env_upper == "PROD" ? var.PROD_STREAMLIT_ROLE : var.DEV_STREAMLIT_ROLE
  streamlit_warehouse_name = local.app_env_upper == "PROD" ? var.PROD_STREAMLIT_WH : var.DEV_STREAMLIT_WH

  # HCP Workspace Variables から受け取る値（各ワークスペースで設定）
  selected_loader_user_rsa_public_key = coalesce(
    var.loader_user_rsa_public_key,
    local.app_env_upper == "PROD" ? var.prod_loader_user_rsa_public_key : var.dev_loader_user_rsa_public_key,
  )
  selected_dbt_user_rsa_public_key = coalesce(
    var.dbt_user_rsa_public_key,
    local.app_env_upper == "PROD" ? var.prod_dbt_user_rsa_public_key : var.dev_dbt_user_rsa_public_key,
  )
  selected_streamlit_user_rsa_public_key = coalesce(
    var.streamlit_user_rsa_public_key,
    local.app_env_upper == "PROD" ? var.prod_streamlit_user_rsa_public_key : var.dev_streamlit_user_rsa_public_key,
  )
}

# module 名を dev -> snowflake_env へ変更した際の state 移行
moved {
  from = module.dev
  to   = module.snowflake_env
}

# APP_ENV に応じて DEV / PROD の Snowflake リソースを作成
module "snowflake_env" {
  source = "./modules/snowflake_env"

  env                           = local.env
  bronze_db_name                = local.bronze_db_name
  silver_db_name                = local.silver_db_name
  gold_db_name                  = local.gold_db_name
  bronze_schema_name            = local.bronze_schema_name
  silver_schema_name            = local.silver_schema_name
  gold_schema_name              = local.gold_schema_name
  bronze_stage_name             = local.bronze_stage_name
  loader_user_name              = local.loader_user_name
  loader_role_name              = local.loader_role_name
  loader_warehouse_name         = local.loader_warehouse_name
  loader_file_format_name       = local.loader_file_format_name
  dbt_user_name                 = local.dbt_user_name
  dbt_role_name                 = local.dbt_role_name
  dbt_warehouse_name            = local.dbt_warehouse_name
  streamlit_user_name           = local.streamlit_user_name
  streamlit_role_name           = local.streamlit_role_name
  streamlit_warehouse_name      = local.streamlit_warehouse_name
  loader_user_rsa_public_key    = local.selected_loader_user_rsa_public_key
  dbt_user_rsa_public_key       = local.selected_dbt_user_rsa_public_key
  streamlit_user_rsa_public_key = local.selected_streamlit_user_rsa_public_key
}
