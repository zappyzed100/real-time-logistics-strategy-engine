output "bronze_db_name" {
  description = "Bronze DB 名"
  value       = snowflake_database.bronze.name
}

output "silver_db_name" {
  description = "Silver DB 名"
  value       = snowflake_database.silver.name
}

output "gold_db_name" {
  description = "Gold DB 名"
  value       = snowflake_database.gold.name
}

output "loader_role_name" {
  description = "Loaderロール名"
  value       = snowflake_account_role.loader_role.name
}

output "dbt_role_name" {
  description = "dbtロール名"
  value       = snowflake_account_role.dbt_role.name
}

output "streamlit_role_name" {
  description = "streamlitロール名"
  value       = snowflake_account_role.streamlit_role.name
}

output "bronze_raw_stage_name" {
  description = "Bronze RAW ステージ名"
  value       = snowflake_stage_internal.bronze_raw_stage.name
}
