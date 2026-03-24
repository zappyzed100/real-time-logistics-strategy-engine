import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def _write_private_key_file(env: dict[str, str]) -> str | None:
    existing_path = env.get("SNOWFLAKE_DBT_PRIVATE_KEY_PATH")
    if existing_path:
        return None

    private_key = env.get("SNOWFLAKE_DBT_PRIVATE_KEY") or env.get(
        "DEV_DBT_USER_RSA_PRIVATE_KEY"
    )
    if not private_key:
        return None

    normalized_key = private_key.replace("\\n", "\n")
    handle, key_path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as key_file:
        key_file.write(normalized_key)

    env["SNOWFLAKE_DBT_PRIVATE_KEY_PATH"] = key_path
    return key_path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    project_dir = repo_root / "enterprise_data_pipeline"

    load_dotenv(repo_root / ".env")

    env = os.environ.copy()
    env.setdefault("DBT_PROFILES_DIR", str(project_dir))
    temp_key_path = _write_private_key_file(env)

    dbt_executable = Path(sys.executable).with_name("dbt.exe")
    if not dbt_executable.exists():
        dbt_executable = Path(sys.executable)

    if dbt_executable.name.lower() == "dbt.exe":
        command = [str(dbt_executable), *sys.argv[1:]]
    else:
        command = [str(dbt_executable), "-m", "dbt.cli.main", *sys.argv[1:]]

    try:
        completed = subprocess.run(command, cwd=project_dir, env=env, check=False)
        return completed.returncode
    finally:
        if temp_key_path:
            Path(temp_key_path).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
