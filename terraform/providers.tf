# terraform/providers.tf
terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.13.0" # 使用するバージョンを指定
    }
  }

  # organization / workspace は terraform/tf ラッパーの init 時に注入する
  backend "remote" {}
}

locals {
  snowflake_user_effective        = var.snowflake_user != null ? var.snowflake_user : var.SNOWFLAKE_USER
  snowflake_private_key_raw       = var.snowflake_private_key != null ? var.snowflake_private_key : var.SNOWFLAKE_PRIVATE_KEY
  snowflake_private_key_effective = local.snowflake_private_key_raw != null ? replace(local.snowflake_private_key_raw, "\\n", "\n") : null
  snowflake_authenticator_raw     = var.SNOWFLAKE_AUTHENTICATOR != null ? var.SNOWFLAKE_AUTHENTICATOR : "SNOWFLAKE_JWT"
  snowflake_authenticator         = trimspace(replace(local.snowflake_authenticator_raw, "\r", ""))
  # SNOWFLAKE_ROLE 未設定時は APP_ENV から自動選択（DEV_TF_ADMIN_ROLE / PROD_TF_ADMIN_ROLE）
  snowflake_role = var.SNOWFLAKE_ROLE != null ? trimspace(replace(var.SNOWFLAKE_ROLE, "\r", "")) : "${upper(var.app_env)}_TF_ADMIN_ROLE"
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = local.snowflake_user_effective
  private_key       = local.snowflake_private_key_effective
  authenticator     = local.snowflake_authenticator
  role              = local.snowflake_role

  # プレビュー機能を有効化する設定を追加
  preview_features_enabled = [
    "snowflake_table_resource",
    "snowflake_stage_internal_resource",
    "snowflake_file_format_resource"
  ]
}