variable "env" {
  type        = string
  description = "環境識別子 (DEV, PROD など)"

  validation {
    condition     = contains(["DEV", "PROD"], upper(var.env))
    error_message = "env は DEV または PROD を指定してください。"
  }
}

variable "db_data_retention_days" {
  type        = number
  description = "Database の data retention 日数"

  validation {
    condition     = var.db_data_retention_days >= 1
    error_message = "db_data_retention_days は 1 以上を指定してください。"
  }
}

variable "schema_is_transient" {
  type        = bool
  description = "Schema の is_transient"
}

variable "schema_with_managed_access" {
  type        = bool
  description = "Schema の with_managed_access"
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

variable "warehouse_size" {
  type        = string
  description = "Warehouse サイズ"

  validation {
    condition     = contains(["X-SMALL", "SMALL", "MEDIUM", "LARGE", "X-LARGE", "2X-LARGE", "3X-LARGE", "4X-LARGE"], upper(var.warehouse_size))
    error_message = "warehouse_size は X-SMALL / SMALL / MEDIUM / LARGE / X-LARGE / 2X-LARGE / 3X-LARGE / 4X-LARGE のいずれかです。"
  }
}

variable "warehouse_auto_suspend" {
  type        = number
  description = "Warehouse auto_suspend 秒数"

  validation {
    condition     = var.warehouse_auto_suspend >= 0
    error_message = "warehouse_auto_suspend は 0 以上を指定してください。"
  }
}

variable "warehouse_auto_resume" {
  type        = bool
  description = "Warehouse auto_resume"
}

variable "warehouse_initially_suspended" {
  type        = bool
  description = "Warehouse initially_suspended"
}

variable "file_format_type" {
  type        = string
  description = "File format type"
}

variable "file_format_field_delimiter" {
  type        = string
  description = "File format field delimiter"
}

variable "file_format_skip_header" {
  type        = number
  description = "File format skip_header"

  validation {
    condition     = var.file_format_skip_header >= 0
    error_message = "file_format_skip_header は 0 以上を指定してください。"
  }
}

variable "file_format_trim_space" {
  type        = bool
  description = "File format trim_space"
}

variable "file_format_field_optionally_enclosed_by" {
  type        = string
  description = "File format field_optionally_enclosed_by"
}

variable "file_format_null_if" {
  type        = list(string)
  description = "File format null_if"
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
  description = "StreamlitユーザーのRSA公開鍵"
}

variable "network_policy_allowed_ip_list" {
  type        = list(string)
  description = "network policy で許可する送信元CIDR。common.auto.tfvars で管理すること（HCP Terraform IP 一覧は https://app.terraform.io/api/meta/ip-ranges 参照）。"
}

variable "network_policy_blocked_ip_list" {
  type        = list(string)
  description = "network policy で拒否する送信元CIDR"
  default     = []
}
