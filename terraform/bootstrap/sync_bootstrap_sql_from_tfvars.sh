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

extract_list() {
  local key="$1"
  awk -v key="${key}" '
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" { in_list=1 }
    in_list {
      while (match($0, /"[^"]+"/)) {
        item = substr($0, RSTART + 1, RLENGTH - 2)
        print item
        $0 = substr($0, RSTART + RLENGTH)
      }
      if ($0 ~ /\]/) {
        exit
      }
    }
  ' "${TFVARS_FILE}"
}

build_sql_ip_list() {
  local key="$1"
  local items=()
  while IFS= read -r cidr; do
    [[ -n "${cidr}" ]] || continue
    items+=("'${cidr}'")
  done < <(extract_list "${key}")

  if [[ ${#items[@]} -eq 0 ]]; then
    echo "[sync] ${key} is empty in ${TFVARS_FILE}" >&2
    exit 1
  fi

  local joined
  joined=$(IFS=', '; echo "${items[*]}")
  printf '%s' "${joined}"
}

sync_env_sql() {
  local sql_file="$1"
  local env_prefix="$2"
  local retention_key="$3"
  local allowed_ips_key="$4"

  local retention_days
  retention_days="$(extract_scalar "${retention_key}")"

  require_non_empty "${retention_key}" "${retention_days}"
  require_positive_integer "${retention_key}" "${retention_days}"

  local allowed_ips_sql
  allowed_ips_sql="$(build_sql_ip_list "${allowed_ips_key}")"

  sed -i -E "s#^ALTER DATABASE ${env_prefix}_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"
  sed -i -E "s#^ALTER DATABASE ${env_prefix}_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"
  sed -i -E "s#^ALTER DATABASE ${env_prefix}_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = [0-9]+;#ALTER DATABASE ${env_prefix}_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = ${retention_days};#" "${sql_file}"

  sed -i -E "s#^  ALLOWED_IP_LIST = \(.*\);#  ALLOWED_IP_LIST = (${allowed_ips_sql});#" "${sql_file}"
  sed -i -E "s#^  SET ALLOWED_IP_LIST = \(.*\);#  SET ALLOWED_IP_LIST = (${allowed_ips_sql});#" "${sql_file}"

  echo "[sync] updated ${sql_file}"
}

sync_env_sql "${DEV_SQL_FILE}" "DEV" "DEV_DB_DATA_RETENTION_DAYS" "DEV_NETWORK_POLICY_ALLOWED_IPS"
sync_env_sql "${PROD_SQL_FILE}" "PROD" "PROD_DB_DATA_RETENTION_DAYS" "PROD_NETWORK_POLICY_ALLOWED_IPS"
