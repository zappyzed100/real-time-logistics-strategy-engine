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


def _set_target_specific_env(env: dict[str, str]) -> None:
    target = _resolve_target(env)
    suffix = _target_suffix(target)

    # Keep compatibility with legacy generic env vars while preferring
    # target-specific values when they are available.
    for generic, scoped in (
        ("SNOWFLAKE_DBT_USER", f"SNOWFLAKE_DBT_USER_{suffix}"),
        ("SNOWFLAKE_DBT_ROLE", f"SNOWFLAKE_DBT_ROLE_{suffix}"),
        ("SNOWFLAKE_DBT_WAREHOUSE", f"SNOWFLAKE_DBT_WAREHOUSE_{suffix}"),
        ("SNOWFLAKE_DBT_PRIVATE_KEY", f"SNOWFLAKE_DBT_PRIVATE_KEY_{suffix}"),
        (
            "SNOWFLAKE_DBT_PRIVATE_KEY_PATH",
            f"SNOWFLAKE_DBT_PRIVATE_KEY_PATH_{suffix}",
        ),
        (
            "SNOWFLAKE_SILVER_DATABASE",
            f"SNOWFLAKE_SILVER_DATABASE_{suffix}",
        ),
        ("SNOWFLAKE_GOLD_DATABASE", f"SNOWFLAKE_GOLD_DATABASE_{suffix}"),
        (
            "SNOWFLAKE_BRONZE_DATABASE",
            f"SNOWFLAKE_BRONZE_DATABASE_{suffix}",
        ),
    ):
        scoped_value = env.get(scoped)
        if scoped_value and not env.get(generic):
            env[generic] = scoped_value


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

    load_dotenv(repo_root / ".env")

    env = os.environ.copy()
    env["APP_ENV"] = _resolve_target(env)
    _set_target_specific_env(env)
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
