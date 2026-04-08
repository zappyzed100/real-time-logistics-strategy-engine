import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from src.utils.env_policy import assert_prod_access_allowed


class RelationSpec(NamedTuple):
    database: str
    schema: str
    name: str
    relation_type: str


def _target() -> str:
    target = (os.getenv("APP_ENV") or "dev").strip().lower() or "dev"
    assert_prod_access_allowed(target, "verify_dbt_view_rebuild")
    return target


def _suffix(target: str) -> str:
    return target.upper()


def _env_with_fallback(name: str, fallback: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return fallback
    return value


def _normalized_env(name: str, fallback: str = "") -> str:
    return _env_with_fallback(name, fallback).strip()


def _required(name: str) -> str:
    value = _normalized_env(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _target_value(target: str, suffix_name: str) -> str:
    value = _normalized_env(f"{_suffix(target)}_{suffix_name}")
    if not value:
        raise ValueError(f"{_suffix(target)}_{suffix_name} is required")
    return value


def _load_private_key_der(target: str) -> bytes:
    suffix = _suffix(target)

    private_key_text = (
        _env_with_fallback(f"SNOWFLAKE_DBT_PRIVATE_KEY_{suffix}")
        or _env_with_fallback("SNOWFLAKE_DBT_PRIVATE_KEY")
        or _env_with_fallback(f"{suffix}_DBT_USER_RSA_PRIVATE_KEY")
    )

    if not private_key_text:
        raise ValueError(
            "DBT private key is required. Set one of: "
            f"SNOWFLAKE_DBT_PRIVATE_KEY_{suffix}, SNOWFLAKE_DBT_PRIVATE_KEY, {suffix}_DBT_USER_RSA_PRIVATE_KEY"
        )

    private_key_text = private_key_text.replace("\\n", "\n")
    passphrase = _env_with_fallback("SNOWFLAKE_DBT_PRIVATE_KEY_PASSPHRASE")

    loaded_key = serialization.load_pem_private_key(
        private_key_text.encode("utf-8"),
        password=passphrase.encode("utf-8") if passphrase else None,
        backend=default_backend(),
    )

    return loaded_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _snowflake_connection(target: str):
    account = _required("TF_VAR_SNOWFLAKE_ACCOUNT")
    user = _target_value(target, "DBT_USER")
    role = _target_value(target, "DBT_ROLE")
    warehouse = _target_value(target, "DBT_WH")
    database = _target_value(target, "SILVER_DB")
    schema = _required("SNOWFLAKE_SILVER_SCHEMA")

    private_key = _load_private_key_der(target)

    return snowflake.connector.connect(
        user=user,
        account=account,
        private_key=private_key,
        warehouse=warehouse,
        database=database,
        schema=schema,
        role=role,
    )


def _relation_specs(target: str) -> list[RelationSpec]:
    silver_db = _target_value(target, "SILVER_DB")
    silver_schema = _required("SNOWFLAKE_SILVER_SCHEMA")
    gold_db = _target_value(target, "GOLD_DB")
    gold_schema = _required("SNOWFLAKE_GOLD_SCHEMA")

    return [
        RelationSpec(silver_db, silver_schema, "stg_orders", "VIEW"),
        RelationSpec(silver_db, silver_schema, "stg_products", "VIEW"),
        RelationSpec(silver_db, silver_schema, "stg_logistics_centers", "VIEW"),
        RelationSpec(silver_db, silver_schema, "int_delivery_cost_candidates", "VIEW"),
        RelationSpec(gold_db, gold_schema, "fct_delivery_candidate_rankings", "TABLE"),
        RelationSpec(gold_db, gold_schema, "fct_delivery_analysis", "TABLE"),
    ]


def _drop_relations(conn, target: str) -> None:
    relations = _relation_specs(target)

    cur = conn.cursor()
    try:
        for relation in relations:
            sql = f"DROP {relation.relation_type} IF EXISTS {relation.database}.{relation.schema}.{relation.name}"
            print(f"[drop] {sql}")
            cur.execute(sql)
    finally:
        cur.close()


def _run_dbt(target: str, repo_root: Path) -> None:
    cmd = [
        sys.executable,
        "src/scripts/deploy/run_dbt.py",
        "run",
        "--target",
        target,
        "--select",
        "+fct_delivery_analysis",
    ]
    print("[dbt]", " ".join(cmd))
    result = subprocess.run(cmd, cwd=repo_root, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"dbt run failed with exit code {result.returncode}")


def _assert_relations(conn, target: str) -> None:
    expected_relations = _relation_specs(target)
    expected_by_key = {
        (relation.database.upper(), relation.schema.upper(), relation.name.upper()): relation.relation_type
        for relation in expected_relations
    }

    cur = conn.cursor()
    try:
        actual_by_key: dict[tuple[str, str, str], str] = {}
        for relation in expected_relations:
            cur.execute(
                f"""
                select table_catalog, table_schema, table_name, table_type
                from {relation.database}.information_schema.tables
                where table_schema = %s and table_name = %s
                """,
                (relation.schema.upper(), relation.name.upper()),
            )
            for row in cur.fetchall():
                key = (str(row[0]).upper(), str(row[1]).upper(), str(row[2]).upper())
                actual_by_key[key] = "TABLE" if str(row[3]).upper() == "BASE TABLE" else str(row[3]).upper()
    finally:
        cur.close()

    missing = set(expected_by_key) - set(actual_by_key)
    if missing:
        formatted = ", ".join([".".join(m) for m in sorted(missing)])
        raise RuntimeError(f"Rebuild verification failed. Missing relations: {formatted}")

    wrong_type = {
        key: (expected_by_key[key], actual_by_key[key])
        for key in expected_by_key
        if actual_by_key[key] != expected_by_key[key]
    }
    if wrong_type:
        formatted = ", ".join(
            f"{'.'.join(key)} expected={expected_type} actual={actual_type}"
            for key, (expected_type, actual_type) in sorted(wrong_type.items())
        )
        raise RuntimeError(f"Rebuild verification failed. Wrong relation types: {formatted}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env.shared")
    load_dotenv(repo_root / ".env", override=True)

    target = _target()
    print(f"[verify] APP_ENV={target}")

    conn = _snowflake_connection(target)
    try:
        _drop_relations(conn, target)
        _run_dbt(target, repo_root)
        _assert_relations(conn, target)
    finally:
        conn.close()

    print("[verify] OK: silver/gold relations were recreated successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
