variable "account_role_name" {
  type        = string
  description = "権限付与先の account role 名"
}

variable "in_schema" {
  type        = string
  description = "対象スキーマ (DATABASE.SCHEMA)"
}

variable "object_type_plural" {
  type        = string
  description = "権限対象オブジェクト種別 (TABLES または VIEWS)"

  validation {
    condition     = contains(["TABLES", "VIEWS"], upper(var.object_type_plural))
    error_message = "object_type_plural は TABLES または VIEWS を指定してください。"
  }
}

variable "permission_level" {
  type        = string
  description = "権限レベル (SELECT または ALL)"

  validation {
    condition     = contains(["SELECT", "ALL"], upper(var.permission_level))
    error_message = "permission_level は SELECT または ALL を指定してください。"
  }
}

variable "grant_on_all" {
  type        = bool
  description = "既存オブジェクトへの権限付与を行うか"
  default     = false
}

variable "grant_on_future" {
  type        = bool
  description = "将来作成オブジェクトへの権限付与を行うか"
  default     = true

  validation {
    condition     = var.grant_on_all || var.grant_on_future
    error_message = "grant_on_all または grant_on_future のどちらか一方は true を指定してください。"
  }
}
