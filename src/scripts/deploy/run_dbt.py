import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def _resolve_target(env: dict[str, str]) -> str:
    return env.get("APP_ENV", "dev").strip().lower() or "dev"


def _target_suffix(target: str) -> str:
    return target.upper()


def _sanitize_runtime_env(env: dict[str, str]) -> None:
    # Guard against CRLF-contaminated values (e.g. account ends with '\r').
    for key in (
        "SNOWFLAKE_ACCOUNT",
        "DEV_DBT_USER",
        "DEV_DBT_ROLE",
        "DEV_DBT_WH",
        "DEV_BRONZE_DB",
        "DEV_SILVER_DB",
        "DEV_GOLD_DB",
        "PROD_DBT_USER",
        "PROD_DBT_ROLE",
        "PROD_DBT_WH",
        "PROD_BRONZE_DB",
        "PROD_SILVER_DB",
        "PROD_GOLD_DB",
    ):
        value = env.get(key)
        if value is not None:
            env[key] = value.strip()


def _write_private_key_file(env: dict[str, str]) -> str | None:
    existing_path = env.get("SNOWFLAKE_DBT_PRIVATE_KEY_PATH")
    if existing_path:
        return None

    target = _resolve_target(env)
    suffix = _target_suffix(target)

    private_key = (
        env.get("SNOWFLAKE_DBT_PRIVATE_KEY")
        or env.get(f"SNOWFLAKE_DBT_PRIVATE_KEY_{suffix}")
        or env.get(f"{suffix}_DBT_USER_RSA_PRIVATE_KEY")
    )
    if not private_key:
        return None

    normalized_key = private_key.replace("\\n", "\n")
    handle, key_path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as key_file:
        key_file.write(normalized_key)

    env["SNOWFLAKE_DBT_PRIVATE_KEY_PATH"] = key_path
    return key_path


def _resolve_dbt_command(args: list[str]) -> list[str]:
    # Prefer the dbt console script in the same virtual environment as this Python.
    python_path = Path(sys.executable)
    candidate_names = ("dbt", "dbt.exe")
    for name in candidate_names:
        candidate = python_path.with_name(name)
        if candidate.exists():
            return [str(candidate), *args]

    dbt_script = shutil.which("dbt")
    if dbt_script:
        return [dbt_script, *args]

    return [str(python_path), "-m", "dbt.cli.main", *args]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    project_dir = repo_root / "enterprise_data_pipeline"
    cli_target = os.environ.get("APP_ENV", "")

    load_dotenv(repo_root / ".env", override=True)

    env = os.environ.copy()
    _sanitize_runtime_env(env)
    if cli_target.strip():
        env["APP_ENV"] = cli_target.strip().lower()
    else:
        env["APP_ENV"] = _resolve_target(env)
    env.setdefault("DBT_PROFILES_DIR", str(project_dir))
    temp_key_path = _write_private_key_file(env)

    command = _resolve_dbt_command(sys.argv[1:])

    try:
        completed = subprocess.run(command, cwd=project_dir, env=env, check=False)
        return completed.returncode
    finally:
        if temp_key_path:
            Path(temp_key_path).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
