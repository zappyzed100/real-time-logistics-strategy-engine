import os
from dataclasses import dataclass
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from src.utils.env_policy import assert_prod_access_allowed


def _load_env_files() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env.shared")
    load_dotenv(repo_root / ".env", override=True)


_load_env_files()


@dataclass(frozen=True)
class LoadSpec:
    file_path: Path
    table_name: str
    select_list: tuple[str, ...]


@dataclass(frozen=True)
class LoadCommands:
    put_command: str
    copy_command: str


class SnowflakeLoader:
    def __init__(self, conn=None, connect: bool = True):
        self.env = self._resolve_app_env()
        self.account = self._require_env("TF_VAR_SNOWFLAKE_ACCOUNT")
        self.user = self._require_env(f"{self.env}_LOADER_USER")
        self.role = self._require_env(f"{self.env}_LOADER_ROLE")
        self.warehouse = self._require_env(f"{self.env}_LOADER_WH")
        self.database = self._require_env(f"{self.env}_BRONZE_DB")
        self.schema = self._require_env("SNOWFLAKE_BRONZE_SCHEMA")
        self.stage_name = self._require_env("SNOWFLAKE_BRONZE_STAGE")
        self.file_format_name = self._require_env(f"{self.env}_LOADER_FILE_FORMAT_NAME")
        self.private_key = None
        self.conn = conn

        if self.conn is None and connect:
            self.conn = self._connect()

    def _resolve_app_env(self) -> str:
        app_env = (os.getenv("APP_ENV") or "dev").strip().lower() or "dev"
        if app_env not in {"dev", "prod"}:
            raise ValueError(f"APP_ENV must be 'dev' or 'prod' (current: {app_env})")
        assert_prod_access_allowed(app_env, "snowflake_loader")
        return app_env.upper()

    def _require_env(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable {key} is required")
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"Environment variable {key} is required")
        return normalized_value

    def _load_private_key(self) -> bytes:
        key_candidates = (
            f"{self.env}_LOADER_USER_RSA_PRIVATE_KEY",
            f"{self.env.lower()}_loader_user_rsa_private_key",
            "SNOWFLAKE_LOADER_PRIVATE_KEY",
        )
        private_key_value = next((os.getenv(key) for key in key_candidates if os.getenv(key)), None)
        if not private_key_value:
            joined_keys = ", ".join(key_candidates)
            raise ValueError(f"Loader private key is required. Set one of: {joined_keys}")

        private_key_text = private_key_value.replace("\\n", "\n")
        passphrase = os.getenv("SNOWFLAKE_LOADER_PRIVATE_KEY_PASSPHRASE")
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

    def _connect(self):
        self.private_key = self._load_private_key()
        return snowflake.connector.connect(
            user=self.user,
            account=self.account,
            private_key=self.private_key,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
            role=self.role,
        )

    def _qualify(self, object_name: str) -> str:
        if "." in object_name:
            return object_name
        return f"{self.database}.{self.schema}.{object_name}"

    def build_load_commands(self, spec: LoadSpec) -> LoadCommands:
        file_path = spec.file_path.resolve()
        file_uri = file_path.as_posix()
        stage_fqn = self._qualify(self.stage_name)
        table_fqn = self._qualify(spec.table_name)
        file_format_fqn = self._qualify(self.file_format_name)
        staged_file_name = file_path.name
        select_clause = ",\n".join(f"        {select_item}" for select_item in spec.select_list)

        put_command = f"PUT 'file://{file_uri}' @{stage_fqn} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
        copy_command = "\n".join(
            [
                f"COPY INTO {table_fqn}",
                "FROM (",
                "    SELECT",
                select_clause,
                f"    FROM @{stage_fqn}/{staged_file_name}.gz",
                ")",
                f"FILE_FORMAT = (FORMAT_NAME = '{file_format_fqn}')",
                "ON_ERROR = 'ABORT_STATEMENT'",
                "PURGE = TRUE",
            ]
        )

        return LoadCommands(put_command=put_command, copy_command=copy_command)

    def load_csv_to_table(self, spec: LoadSpec):
        if self.conn is None:
            raise RuntimeError("Snowflake connection is not initialized")

        file_path = spec.file_path.resolve()
        table_fqn = self._qualify(spec.table_name)
        commands = self.build_load_commands(spec)

        cursor = self.conn.cursor()
        try:
            cursor.execute(commands.put_command)
            cursor.execute(commands.copy_command)
            print(f"Loaded {file_path} into {table_fqn}")
        finally:
            cursor.close()

    def load_default_seed_data(self):
        load_specs = [
            LoadSpec(
                file_path=Path("data/03_seed/logistics_centers.csv"),
                table_name="LOGISTICS_CENTERS",
                select_list=(
                    "$1::STRING",
                    "$2::STRING",
                    "$3::STRING",
                    "$4::STRING",
                    "METADATA$FILENAME::STRING",
                    "CURRENT_TIMESTAMP()::TIMESTAMP_NTZ",
                ),
            ),
            LoadSpec(
                file_path=Path("data/03_seed/products.csv"),
                table_name="PRODUCTS",
                select_list=(
                    "$1::STRING",
                    "$2::STRING",
                    "$3::STRING",
                    "$4::STRING",
                    "$5::STRING",
                    "METADATA$FILENAME::STRING",
                    "CURRENT_TIMESTAMP()::TIMESTAMP_NTZ",
                ),
            ),
            LoadSpec(
                file_path=Path("data/04_out/inventory.csv"),
                table_name="INVENTORY",
                select_list=(
                    "$1::STRING",
                    "$2::STRING",
                    "$3::STRING",
                    "METADATA$FILENAME::STRING",
                    "CURRENT_TIMESTAMP()::TIMESTAMP_NTZ",
                ),
            ),
            LoadSpec(
                file_path=Path("data/04_out/orders.csv"),
                table_name="ORDERS",
                select_list=(
                    "$1::STRING",
                    "$2::STRING",
                    "$3::STRING",
                    "$4::STRING",
                    "$5::STRING",
                    "$6::STRING",
                    "METADATA$FILENAME::STRING",
                    "CURRENT_TIMESTAMP()::TIMESTAMP_NTZ",
                ),
            ),
        ]

        for spec in load_specs:
            self.load_csv_to_table(spec)

    def close(self):
        if self.conn is not None:
            self.conn.close()


if __name__ == "__main__":
    loader = SnowflakeLoader()
    try:
        loader.load_default_seed_data()
    finally:
        loader.close()
