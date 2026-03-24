# terraform/variables.tf
variable "dev_loader_user_rsa_public_key" {
  type      = string
  sensitive = true
}

variable "dev_dbt_user_rsa_public_key" {
  type      = string
  sensitive = true
}

variable "dev_streamlit_user_rsa_public_key" {
  type      = string
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
  default     = null
  nullable    = true
  description = "snowflakeへの認証方法設定"
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