#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TFVARS_FILE="${SCRIPT_DIR}/../common.auto.tfvars"
DEV_SQL_FILE="${SCRIPT_DIR}/sql/setup_snowflake_tf_dev.sql"
PROD_SQL_FILE="${SCRIPT_DIR}/sql/setup_snowflake_tf_prod.sql"

if [[ ! -f "${TFVARS_FILE}" ]]; then
  echo "[sync] tfvars not found: ${TFVARS_FILE}" >&2
  exit 1
fi

extract_scalar() {
  local key="$1"
  awk -F'=' -v key="${key}" '
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      val=$0
      sub(/^[^=]*=[[:space:]]*/, "", val)
      gsub(/^[[:space:]]*\"/, "", val)
      gsub(/\"[[:space:]]*$/, "", val)
      gsub(/[[:space:]]+$/, "", val)
      print val
      exit
    }
  ' "${TFVARS_FILE}"
}

require_non_empty() {
  local key="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    echo "[sync] required value is empty: ${key}" >&2
    exit 1
  fi
}

require_positive_integer() {
  local key="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[0-9]+$ ]] || [[ "${value}" -lt 1 ]]; then
    echo "[sync] ${key} must be a positive integer (current: ${value})" >&2
    exit 1
  fi
}

sync_env_sql() {
  local sql_file="$1"
  local env_prefix="$2"
  local retention_key="$3"

  local retention_days
  retention_days="$(extract_scalar "${retention_key}")"

  require_non_empty "${retention_key}" "${retention_days}"
  require_positive_integer "${retention_key}" "${retention_days}"

  sed -i -E "s#^ALTER DATABASE ${env_prefix}_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"
  sed -i -E "s#^ALTER DATABASE ${env_prefix}_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"
  sed -i -E "s#^ALTER DATABASE ${env_prefix}_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"

  echo "[sync] updated ${sql_file}"
}

sync_env_sql "${DEV_SQL_FILE}" "DEV" "DEV_DB_DATA_RETENTION_DAYS"
sync_env_sql "${PROD_SQL_FILE}" "PROD" "PROD_DB_DATA_RETENTION_DAYS"
