terraform {
  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = ">= 2.0.0" # 再利用可能モジュールのため緩いバージョン制約を使用。固定はrootモジュール側で管理する。
    }
  }
}
