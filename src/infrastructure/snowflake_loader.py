import os
from dataclasses import dataclass
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LoadSpec:
    file_path: Path
    table_name: str
    select_list: tuple[str, ...]


class SnowflakeLoader:
    def __init__(self):
        self.env = os.getenv("SNOWFLAKE_ENV", "DEV").upper()
        self.account = self._require_env("SNOWFLAKE_ACCOUNT")
        self.user = os.getenv("SNOWFLAKE_LOADER_USER") or f"{self.env}_LOADER_USER"
        self.role = os.getenv("SNOWFLAKE_LOADER_ROLE") or f"{self.env}_LOADER_ROLE"
        self.warehouse = (
            os.getenv("SNOWFLAKE_LOADER_WAREHOUSE") or f"{self.env}_LOADER_WH"
        )
        self.database = (
            os.getenv("SNOWFLAKE_LOADER_DATABASE") or f"{self.env}_BRONZE_DB"
        )
        self.schema = os.getenv("SNOWFLAKE_LOADER_SCHEMA") or "RAW_DATA"
        self.stage_name = (
            os.getenv("SNOWFLAKE_LOADER_STAGE") or f"{self.env}_BRONZE_RAW_STAGE"
        )
        self.file_format_name = (
            os.getenv("SNOWFLAKE_LOADER_FILE_FORMAT") or f"{self.env}_CSV_FORMAT"
        )
        self.private_key = self._load_private_key()
        self.conn = snowflake.connector.connect(
            user=self.user,
            account=self.account,
            private_key=self.private_key,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
            role=self.role,
        )

    def _require_env(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Environment variable {key} is required")
        return value

    def _load_private_key(self) -> bytes:
        key_candidates = (
            f"{self.env}_LOADER_USER_RSA_PRIVATE_KEY",
            f"{self.env.lower()}_loader_user_rsa_private_key",
            "SNOWFLAKE_LOADER_PRIVATE_KEY",
        )
        private_key_value = next(
            (os.getenv(key) for key in key_candidates if os.getenv(key)), None
        )
        if not private_key_value:
            joined_keys = ", ".join(key_candidates)
            raise ValueError(
                f"Loader private key is required. Set one of: {joined_keys}"
            )

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

    def _qualify(self, object_name: str) -> str:
        if "." in object_name:
            return object_name
        return f"{self.database}.{self.schema}.{object_name}"

    def load_csv_to_table(self, spec: LoadSpec):
        file_path = spec.file_path.resolve()
        file_uri = file_path.as_posix()
        stage_fqn = self._qualify(self.stage_name)
        table_fqn = self._qualify(spec.table_name)
        file_format_fqn = self._qualify(self.file_format_name)
        staged_file_name = file_path.name
        select_clause = ",\n                    ".join(spec.select_list)

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                f"PUT 'file://{file_uri}' @{stage_fqn} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            )
            cursor.execute(
                f"""
                COPY INTO {table_fqn}
                FROM (
                    SELECT
                    {select_clause}
                    FROM @{stage_fqn}/{staged_file_name}.gz
                )
                FILE_FORMAT = (FORMAT_NAME = '{file_format_fqn}')
                ON_ERROR = 'ABORT_STATEMENT'
                PURGE = TRUE
                """
            )
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
        self.conn.close()


if __name__ == "__main__":
    loader = SnowflakeLoader()
    try:
        loader.load_default_seed_data()
    finally:
        loader.close()
