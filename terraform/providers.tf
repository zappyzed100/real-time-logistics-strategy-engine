# terraform/providers.tf
terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.13.0" # 使用するバージョンを指定
    }
  }

  # organization / workspaces は backend.hcl (gitignore対象) から注入する
  backend "remote" {}
}

locals {
  snowflake_user_effective = var.snowflake_user != null ? var.snowflake_user : var.SNOWFLAKE_USER
  snowflake_private_key_raw = var.snowflake_private_key != null ? var.snowflake_private_key : var.SNOWFLAKE_PRIVATE_KEY
  snowflake_private_key_effective = local.snowflake_private_key_raw != null ? replace(local.snowflake_private_key_raw, "\\n", "\n") : null
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = local.snowflake_user_effective
  private_key       = local.snowflake_private_key_effective
  role              = "ACCOUNTADMIN"

  # プレビュー機能を有効化する設定を追加
  preview_features_enabled = [
    "snowflake_table_resource",
    "snowflake_stage_internal_resource",
    "snowflake_file_format_resource"
  ]
}