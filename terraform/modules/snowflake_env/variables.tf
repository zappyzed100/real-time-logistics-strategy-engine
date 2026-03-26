variable "env" {
  type        = string
  description = "環境識別子 (DEV, PROD など)"

  validation {
    condition     = contains(["DEV", "PROD"], upper(var.env))
    error_message = "env は DEV または PROD を指定してください。"
  }
}

variable "bronze_db_name" {
  type        = string
  description = "Bronze DB 名"
}

variable "silver_db_name" {
  type        = string
  description = "Silver DB 名"
}

variable "gold_db_name" {
  type        = string
  description = "Gold DB 名"
}

variable "bronze_schema_name" {
  type        = string
  description = "Bronze schema 名"
}

variable "silver_schema_name" {
  type        = string
  description = "Silver schema 名"
}

variable "gold_schema_name" {
  type        = string
  description = "Gold schema 名"
}

variable "bronze_stage_name" {
  type        = string
  description = "Bronze stage 名"
}

variable "loader_user_name" {
  type        = string
  description = "Loader user 名"
}

variable "loader_role_name" {
  type        = string
  description = "Loader role 名"
}

variable "loader_warehouse_name" {
  type        = string
  description = "Loader warehouse 名"
}

variable "loader_file_format_name" {
  type        = string
  description = "Loader file format 名"
}

variable "dbt_user_name" {
  type        = string
  description = "dbt user 名"
}

variable "dbt_role_name" {
  type        = string
  description = "dbt role 名"
}

variable "dbt_warehouse_name" {
  type        = string
  description = "dbt warehouse 名"
}

variable "streamlit_user_name" {
  type        = string
  description = "Streamlit user 名"
}

variable "streamlit_role_name" {
  type        = string
  description = "Streamlit role 名"
}

variable "streamlit_warehouse_name" {
  type        = string
  description = "Streamlit warehouse 名"
}

variable "loader_user_rsa_public_key" {
  type        = string
  nullable    = false
  sensitive   = true
  description = "LoaderユーザーのRSA公開鍵"
}

variable "dbt_user_rsa_public_key" {
  type        = string
  nullable    = false
  sensitive   = true
  description = "dbtユーザーのRSA公開鍵"
}

variable "streamlit_user_rsa_public_key" {
  type        = string
  nullable    = false
  sensitive   = true
  description = "dbtユーザーのRSA公開鍵"
}
