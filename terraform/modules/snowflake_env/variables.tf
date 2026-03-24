variable "env" {
  type        = string
  description = "環境識別子 (DEV, PROD など)"

  validation {
    condition     = contains(["DEV", "PROD"], upper(var.env))
    error_message = "env は DEV または PROD を指定してください。"
  }
}

variable "loader_user_rsa_public_key" {
  type        = string
  sensitive   = true
  description = "LoaderユーザーのRSA公開鍵"
}

variable "dbt_user_rsa_public_key" {
  type        = string
  sensitive   = true
  description = "dbtユーザーのRSA公開鍵"
}

variable "streamlit_user_rsa_public_key" {
  type        = string
  sensitive   = true
  description = "dbtユーザーのRSA公開鍵"
}
