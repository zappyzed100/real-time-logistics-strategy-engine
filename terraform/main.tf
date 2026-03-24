# DEV 環境 — modules/snowflake_env を呼び出す
module "dev" {
  source = "./modules/snowflake_env"

  env                           = "DEV"
  loader_user_rsa_public_key    = var.dev_loader_user_rsa_public_key
  dbt_user_rsa_public_key       = var.dev_dbt_user_rsa_public_key
  streamlit_user_rsa_public_key = var.dev_streamlit_user_rsa_public_key
}
