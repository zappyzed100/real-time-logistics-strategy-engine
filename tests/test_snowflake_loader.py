from textwrap import dedent

from src.infrastructure.snowflake_loader import LoadSpec, SnowflakeLoader


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.closed = False

    def execute(self, command: str):
        self.executed.append(command)

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def set_loader_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test-account")
    monkeypatch.delenv("SNOWFLAKE_LOADER_USER", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_ROLE", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_WAREHOUSE", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_DATABASE", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_SCHEMA", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_STAGE", raising=False)
    monkeypatch.delenv("SNOWFLAKE_LOADER_FILE_FORMAT", raising=False)


def test_build_load_commands_generates_expected_snowflake_sql(monkeypatch, tmp_path):
    set_loader_env(monkeypatch)
    csv_path = tmp_path / "orders.csv"
    csv_path.write_text("1,2,3\n", encoding="utf-8")

    loader = SnowflakeLoader(connect=False)
    spec = LoadSpec(
        file_path=csv_path,
        table_name="ORDERS",
        select_list=(
            "$1::STRING",
            "$2::STRING",
            "METADATA$FILENAME::STRING",
            "CURRENT_TIMESTAMP()::TIMESTAMP_NTZ",
        ),
    )

    commands = loader.build_load_commands(spec)

    assert commands.put_command == (
        f"PUT 'file://{csv_path.resolve().as_posix()}' "
        "@DEV_BRONZE_DB.RAW_DATA.DEV_BRONZE_RAW_STAGE "
        "AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    )
    assert commands.copy_command == dedent(
        f"""
        COPY INTO DEV_BRONZE_DB.RAW_DATA.ORDERS
        FROM (
            SELECT
                $1::STRING,
                $2::STRING,
                METADATA$FILENAME::STRING,
                CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
            FROM @DEV_BRONZE_DB.RAW_DATA.DEV_BRONZE_RAW_STAGE/{csv_path.name}.gz
        )
        FILE_FORMAT = (FORMAT_NAME = 'DEV_BRONZE_DB.RAW_DATA.DEV_CSV_FORMAT')
        ON_ERROR = 'ABORT_STATEMENT'
        PURGE = TRUE
        """
    ).strip()


def test_load_csv_to_table_executes_generated_commands_in_order(monkeypatch, tmp_path):
    set_loader_env(monkeypatch)
    csv_path = tmp_path / "inventory.csv"
    csv_path.write_text("1,2\n", encoding="utf-8")

    fake_conn = FakeConnection()
    loader = SnowflakeLoader(conn=fake_conn, connect=False)
    spec = LoadSpec(
        file_path=csv_path,
        table_name="INVENTORY",
        select_list=(
            "$1::STRING",
            "$2::STRING",
        ),
    )

    expected_commands = loader.build_load_commands(spec)

    loader.load_csv_to_table(spec)

    assert fake_conn.cursor_instance.executed == [
        expected_commands.put_command,
        expected_commands.copy_command,
    ]
    assert fake_conn.cursor_instance.closed is True


def test_loader_trims_whitespace_from_required_account_env(monkeypatch):
    set_loader_env(monkeypatch)
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test-account\r\n")

    loader = SnowflakeLoader(connect=False)

    assert loader.account == "test-account"
