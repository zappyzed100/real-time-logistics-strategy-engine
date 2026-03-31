# terraform/variables.tf
#
# 非機密の Terraform 設定は common.auto.tfvars で管理する。
# HCP Workspace Variables / .env には主に機密値（鍵等）を設定する想定。

variable "app_env" {
  type        = string
  description = "実行環境 (dev または prod)"

  validation {
    condition     = contains(["dev", "prod"], lower(var.app_env))
    error_message = "app_env には dev または prod を指定してください。"
  }
}

variable "DEV_TF_ADMIN_ROLE" {
  type        = string
  description = "DEV 環境で Terraform 実行に使用する Snowflake ロール名"
}

variable "PROD_TF_ADMIN_ROLE" {
  type        = string
  description = "PROD 環境で Terraform 実行に使用する Snowflake ロール名"
}

variable "DEV_DB_DATA_RETENTION_DAYS" {
  type        = number
  description = "DEV 環境の DB retention 日数"

  validation {
    condition     = var.DEV_DB_DATA_RETENTION_DAYS >= 1
    error_message = "DEV_DB_DATA_RETENTION_DAYS は 1 以上を指定してください。"
  }
}

variable "PROD_DB_DATA_RETENTION_DAYS" {
  type        = number
  description = "PROD 環境の DB retention 日数"

  validation {
    condition     = var.PROD_DB_DATA_RETENTION_DAYS >= 1
    error_message = "PROD_DB_DATA_RETENTION_DAYS は 1 以上を指定してください。"
  }
}

variable "SNOWFLAKE_SCHEMA_IS_TRANSIENT" {
  type        = bool
  description = "Schema の is_transient 設定 (true/false)"
}

variable "SNOWFLAKE_SCHEMA_WITH_MANAGED_ACCESS" {
  type        = bool
  description = "Schema の managed access 設定 (true/false)"
}

variable "SNOWFLAKE_BRONZE_SCHEMA" {
  type        = string
  description = "Bronze schema 名（全環境共通）"
}

variable "SNOWFLAKE_SILVER_SCHEMA" {
  type        = string
  description = "Silver schema 名（全環境共通）"
}

variable "SNOWFLAKE_GOLD_SCHEMA" {
  type        = string
  description = "Gold schema 名（全環境共通）"
}

variable "SNOWFLAKE_BRONZE_STAGE" {
  type        = string
  description = "Bronze stage 名（全環境共通）"
}

variable "SNOWFLAKE_WAREHOUSE_SIZE" {
  type        = string
  description = "Warehouse サイズ（全環境共通）"
}

variable "SNOWFLAKE_WAREHOUSE_AUTO_SUSPEND_SECONDS" {
  type        = number
  description = "Warehouse auto_suspend 秒数（全環境共通）"

  validation {
    condition     = var.SNOWFLAKE_WAREHOUSE_AUTO_SUSPEND_SECONDS >= 0
    error_message = "SNOWFLAKE_WAREHOUSE_AUTO_SUSPEND_SECONDS は 0 以上を指定してください。"
  }
}

variable "SNOWFLAKE_WAREHOUSE_AUTO_RESUME" {
  type        = bool
  description = "Warehouse auto_resume 設定 (true/false)"
}

variable "SNOWFLAKE_WAREHOUSE_INITIALLY_SUSPENDED" {
  type        = bool
  description = "Warehouse initially_suspended 設定 (true/false)"
}

variable "SNOWFLAKE_FILE_FORMAT_TYPE" {
  type        = string
  description = "Loader file format type"
}

variable "SNOWFLAKE_FILE_FORMAT_FIELD_DELIMITER" {
  type        = string
  description = "Loader file format field delimiter"
}

variable "SNOWFLAKE_FILE_FORMAT_SKIP_HEADER" {
  type        = number
  description = "Loader file format skip_header"

  validation {
    condition     = var.SNOWFLAKE_FILE_FORMAT_SKIP_HEADER >= 0
    error_message = "SNOWFLAKE_FILE_FORMAT_SKIP_HEADER は 0 以上を指定してください。"
  }
}

variable "SNOWFLAKE_FILE_FORMAT_TRIM_SPACE" {
  type        = bool
  description = "Loader file format trim_space (true/false)"
}

variable "SNOWFLAKE_FILE_FORMAT_FIELD_OPTIONALLY_ENCLOSED_BY" {
  type        = string
  description = "Loader file format field_optionally_enclosed_by"
}

variable "SNOWFLAKE_FILE_FORMAT_NULL_IF" {
  type        = list(string)
  description = "Loader file format null_if"
}

variable "DEV_BRONZE_DB" {
  type        = string
  description = "DEV Bronze DB 名"
}

variable "DEV_SILVER_DB" {
  type        = string
  description = "DEV Silver DB 名"
}

variable "DEV_GOLD_DB" {
  type        = string
  description = "DEV Gold DB 名"
}

variable "PROD_BRONZE_DB" {
  type        = string
  description = "PROD Bronze DB 名"
}

variable "PROD_SILVER_DB" {
  type        = string
  description = "PROD Silver DB 名"
}

variable "PROD_GOLD_DB" {
  type        = string
  description = "PROD Gold DB 名"
}

variable "DEV_LOADER_USER" {
  type        = string
  description = "DEV Loader user 名"
}

variable "DEV_LOADER_ROLE" {
  type        = string
  description = "DEV Loader role 名"
}

variable "DEV_LOADER_WH" {
  type        = string
  description = "DEV Loader warehouse 名"
}

variable "DEV_LOADER_FILE_FORMAT_NAME" {
  type        = string
  description = "DEV Loader file format 名"
}

variable "PROD_LOADER_USER" {
  type        = string
  description = "PROD Loader user 名"
}

variable "PROD_LOADER_ROLE" {
  type        = string
  description = "PROD Loader role 名"
}

variable "PROD_LOADER_WH" {
  type        = string
  description = "PROD Loader warehouse 名"
}

variable "PROD_LOADER_FILE_FORMAT_NAME" {
  type        = string
  description = "PROD Loader file format 名"
}

variable "DEV_DBT_USER" {
  type        = string
  description = "DEV dbt user 名"
}

variable "DEV_DBT_ROLE" {
  type        = string
  description = "DEV dbt role 名"
}

variable "DEV_DBT_WH" {
  type        = string
  description = "DEV dbt warehouse 名"
}

variable "PROD_DBT_USER" {
  type        = string
  description = "PROD dbt user 名"
}

variable "PROD_DBT_ROLE" {
  type        = string
  description = "PROD dbt role 名"
}

variable "PROD_DBT_WH" {
  type        = string
  description = "PROD dbt warehouse 名"
}

variable "DEV_STREAMLIT_USER" {
  type        = string
  description = "DEV Streamlit user 名"
}

variable "DEV_STREAMLIT_ROLE" {
  type        = string
  description = "DEV Streamlit role 名"
}

variable "DEV_STREAMLIT_WH" {
  type        = string
  description = "DEV Streamlit warehouse 名"
}

variable "PROD_STREAMLIT_USER" {
  type        = string
  description = "PROD Streamlit user 名"
}

variable "PROD_STREAMLIT_ROLE" {
  type        = string
  description = "PROD Streamlit role 名"
}

variable "PROD_STREAMLIT_WH" {
  type        = string
  description = "PROD Streamlit warehouse 名"
}

variable "DEV_NETWORK_POLICY_ALLOWED_IPS" {
  type        = list(string)
  description = "DEV 向けに許可する送信元CIDR"
}

variable "PROD_NETWORK_POLICY_ALLOWED_IPS" {
  type        = list(string)
  description = "PROD 向けに許可する送信元CIDR"
}

variable "DEV_NETWORK_POLICY_BLOCKED_IPS" {
  type        = list(string)
  description = "DEV 向けに拒否する送信元CIDR"
}

variable "PROD_NETWORK_POLICY_BLOCKED_IPS" {
  type        = list(string)
  description = "PROD 向けに拒否する送信元CIDR"
}

variable "loader_user_rsa_public_key" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "環境共通の Loader ユーザー公開鍵（推奨）"
}

variable "dbt_user_rsa_public_key" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "環境共通の dbt ユーザー公開鍵（推奨）"
}

variable "streamlit_user_rsa_public_key" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "環境共通の Streamlit ユーザー公開鍵（推奨）"
}



# SNOWFLAKE_ACCOUNT=ORG-ACCOUNT 形式の複合変数。.env / HCP 環境変数から TF_VAR_SNOWFLAKE_ACCOUNT で注入する。
# snowflake_organization_name / snowflake_account_name を個別に設定した場合はそちらが優先される。
variable "SNOWFLAKE_ACCOUNT" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "Snowflakeアカウント識別子（ORG-ACCOUNT 形式: 例 CWNOMGN-AF62260）"
}

variable "snowflake_organization_name" {
  type        = string
  default     = null
  nullable    = true
  description = "Snowflakeの組織名（個別指定時のみ設定。通常は SNOWFLAKE_ACCOUNT を使用）"

  validation {
    condition     = var.snowflake_organization_name == null || length(trimspace(var.snowflake_organization_name)) > 0
    error_message = "snowflake_organization_name は空文字にできません。"
  }
}

variable "snowflake_account_name" {
  type        = string
  default     = null
  nullable    = true
  description = "Snowflakeのアカウント名（個別指定時のみ設定。通常は SNOWFLAKE_ACCOUNT を使用）"

  validation {
    condition     = var.snowflake_account_name == null || length(trimspace(var.snowflake_account_name)) > 0
    error_message = "snowflake_account_name は空文字にできません。"
  }
}

variable "SNOWFLAKE_USER" {
  type        = string
  default     = null
  nullable    = true
  description = "Terraform実行に使用するSnowflakeユーザー名"
}

variable "SNOWFLAKE_PRIVATE_KEY" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "Terraform実行ユーザーのRSA秘密鍵(PEM本文)"
}

variable "SNOWFLAKE_AUTHENTICATOR" {
  type        = string
  nullable    = false
  description = "snowflakeへの認証方法設定"

  validation {
    condition     = contains(["SNOWFLAKE_JWT", "SNOWFLAKE", "EXTERNALBROWSER", "OAUTH", "USERNAME_PASSWORD_MFA"], upper(var.SNOWFLAKE_AUTHENTICATOR))
    error_message = "SNOWFLAKE_AUTHENTICATOR は SNOWFLAKE_JWT / SNOWFLAKE / EXTERNALBROWSER / OAUTH / USERNAME_PASSWORD_MFA のいずれかを指定してください。"
  }
}

variable "SNOWFLAKE_ROLE" {
  type        = string
  default     = null
  nullable    = true
  description = "Terraform 実行時に使用する Snowflake ロール。未設定時は {ENV}_TF_ADMIN_ROLE を自動選択"
}

