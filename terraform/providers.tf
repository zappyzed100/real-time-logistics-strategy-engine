# terraform/providers.tf
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "= 2.13.0" # preview feature 依存のため、意図しない自動更新を防ぐために固定
    }
  }

  # backend-config 未指定の直接実行で実運用 state を汚さないよう、
  # デフォルトはガード用 workspace に固定する。
  backend "remote" {
    organization = "zappyzed100"

    workspaces {
      name = "__guard_do_not_use_without_backend_config__"
    }
  }
}

locals {
  snowflake_user_effective        = var.snowflake_user != null ? var.snowflake_user : var.SNOWFLAKE_USER
  snowflake_private_key_raw       = var.snowflake_private_key != null ? var.snowflake_private_key : var.SNOWFLAKE_PRIVATE_KEY
  snowflake_private_key_effective = local.snowflake_private_key_raw != null ? replace(local.snowflake_private_key_raw, "\\n", "\n") : null
  snowflake_authenticator         = trimspace(replace(var.SNOWFLAKE_AUTHENTICATOR, "\r", ""))
  snowflake_role                  = var.SNOWFLAKE_ROLE != null ? trimspace(replace(var.SNOWFLAKE_ROLE, "\r", "")) : trimspace(replace(local.tf_admin_role, "\r", ""))

  # 誤環境実行防止： app_env と snowflake_role のプレフィックスが一致することを検証
  # 同一SnowflakeアカウントでDEV/PRODを共用する構成であるため、ロールプレフィックスで誤環境実行を検出する
  role_env_prefix_valid = (
    local.snowflake_role == null ||
    startswith(upper(local.snowflake_role), upper(local.app_env_upper))
  )
}

check "env_role_mismatch" {
  assert {
    condition     = local.role_env_prefix_valid
    error_message = "SNOWFLAKE_ROLE (${local.snowflake_role}) のプレフィックスが app_env (${local.app_env_upper}) と一致しません。誤環境実行の可能性があります。"
  }
}

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = local.snowflake_user_effective
  private_key       = local.snowflake_private_key_effective
  authenticator     = local.snowflake_authenticator
  role              = local.snowflake_role

  # preview feature を利用しているため、provider 更新時は terraform/README.md の
  # 「Snowflake Provider 更新ポリシー」に従って段階的に検証すること。
  preview_features_enabled = [
    "snowflake_table_resource",
    "snowflake_stage_internal_resource",
    "snowflake_file_format_resource"
  ]
}