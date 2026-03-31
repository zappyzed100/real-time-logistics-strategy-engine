terraform {
  required_providers {
    snowflake = {
      source = "snowflakedb/snowflake"
    }
  }
}

locals {
  object_type_plural_upper = upper(var.object_type_plural)
  permission_level_upper   = upper(var.permission_level)

  all_privileges_by_object = {
    TABLES = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES"]
    VIEWS  = ["SELECT"]
  }

  resolved_privileges = local.permission_level_upper == "SELECT" ? ["SELECT"] : local.all_privileges_by_object[local.object_type_plural_upper]
}

resource "snowflake_grant_privileges_to_account_role" "on_all" {
  count             = var.grant_on_all ? 1 : 0
  account_role_name = var.account_role_name
  privileges        = local.resolved_privileges

  on_schema_object {
    all {
      object_type_plural = local.object_type_plural_upper
      in_schema          = var.in_schema
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "on_future" {
  count             = var.grant_on_future ? 1 : 0
  account_role_name = var.account_role_name
  privileges        = local.resolved_privileges

  on_schema_object {
    future {
      object_type_plural = local.object_type_plural_upper
      in_schema          = var.in_schema
    }
  }
}

