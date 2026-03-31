# terraform/variables.tf
#
# 命名値は .env.shared / .env から terraform/tf が TF_VAR_* として注入する。
# HCP Workspace Variables には主に機密値（鍵等）を設定する想定。

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
  # Source: https://app.terraform.io/api/meta/ip-ranges (2026-03-31取得)
  default = [
    "75.2.98.97/32",
    "99.83.150.238/32",
    "52.86.200.106/32",
    "52.86.201.227/32",
    "52.70.186.109/32",
    "44.236.246.186/32",
    "54.185.161.84/32",
    "44.238.78.236/32",
    "184.73.220.168/32",
    "35.169.128.114/32",
    "52.45.167.229/32",
    "54.225.227.126/32",
    "44.224.173.58/32",
    "44.225.195.96/32",
    "52.37.251.66/32",
    "52.41.30.244/32",
  ]
}

variable "PROD_NETWORK_POLICY_ALLOWED_IPS" {
  type        = list(string)
  description = "PROD 向けに許可する送信元CIDR"
  # Source: https://app.terraform.io/api/meta/ip-ranges (2026-03-31取得)
  default = [
    "75.2.98.97/32",
    "99.83.150.238/32",
    "52.86.200.106/32",
    "52.86.201.227/32",
    "52.70.186.109/32",
    "44.236.246.186/32",
    "54.185.161.84/32",
    "44.238.78.236/32",
    "184.73.220.168/32",
    "35.169.128.114/32",
    "52.45.167.229/32",
    "54.225.227.126/32",
    "44.224.173.58/32",
    "44.225.195.96/32",
    "52.37.251.66/32",
    "52.41.30.244/32",
  ]
}

variable "DEV_NETWORK_POLICY_BLOCKED_IPS" {
  type        = list(string)
  description = "DEV 向けに拒否する送信元CIDR"
  default     = []
}

variable "PROD_NETWORK_POLICY_BLOCKED_IPS" {
  type        = list(string)
  description = "PROD 向けに拒否する送信元CIDR"
  default     = []
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

variable "dev_loader_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "dev_dbt_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "dev_streamlit_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "prod_loader_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "prod_dbt_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "prod_streamlit_user_rsa_public_key" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "snowflake_organization_name" {
  type        = string
  description = "Snowflakeの組織名"
}

variable "snowflake_account_name" {
  type        = string
  description = "Snowflakeのアカウント名"
}

variable "snowflake_user" {
  type        = string
  default     = null
  nullable    = true
  description = "Terraform実行に使用するSnowflakeユーザー名"
}

variable "snowflake_private_key" {
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
}

variable "SNOWFLAKE_ROLE" {
  type        = string
  default     = null
  nullable    = true
  description = "Terraform 実行時に使用する Snowflake ロール。未設定時は {ENV}_TF_ADMIN_ROLE を自動選択"
}

# 互換性のための旧変数名（HCP側が未切替でも動作させる）
variable "SNOWFLAKE_USER" {
  type        = string
  default     = null
  nullable    = true
  description = "互換: 旧変数名のSnowflakeユーザー"
}

variable "SNOWFLAKE_PRIVATE_KEY" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "互換: 旧変数名のSnowflake秘密鍵"
}