import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DOTENV_FILES = (".env",)
TEXT_FILE_SUFFIXES = (
    ".py",
    ".yml",
    ".yaml",
    ".sql",
    ".md",
    ".toml",
    ".cfg",
    ".ini",
)
TEXT_FILE_NAMES = {".env.example"}


def _run(command: list[str]) -> int:
    print("[check]", " ".join(command))
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode


def _can_run(command: list[str]) -> bool:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _is_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS", "").lower() == "true"


def _iter_tracked_text_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("git ls-files failed while collecting tracked files")

    files: list[Path] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8"))
        if relative.name in TEXT_FILE_NAMES or relative.suffix in TEXT_FILE_SUFFIXES:
            path = REPO_ROOT / relative
            if path.is_file():
                files.append(path)
    return sorted(files)


def _check_cr_in_files(paths: list[Path], label: str) -> int:
    offenders: list[str] = []
    for path in paths:
        if b"\r" in path.read_bytes():
            offenders.append(str(path.relative_to(REPO_ROOT)))

    if not offenders:
        print(f"[check] OK: no CR found in {label}")
        return 0

    print(f"[check] ERROR: CR (\\r) found in {label}:", file=sys.stderr)
    for offender in offenders:
        print(offender, file=sys.stderr)
    return 1


def _check_repo_crlf() -> int:
    return _check_cr_in_files(_iter_tracked_text_files(), "git-tracked text files")


def _check_dotenv(dotenv_path: str) -> int:
    path = Path(dotenv_path)
    if not path.is_absolute():
        path = REPO_ROOT / path

    if not path.exists():
        print(f"[check] ERROR: dotenv file not found: {path}", file=sys.stderr)
        return 2

    return _check_cr_in_files([path], f"dotenv file {path.relative_to(REPO_ROOT)}")


def _check_default_dotenv_files() -> int:
    paths = [REPO_ROOT / name for name in DEFAULT_DOTENV_FILES]
    existing_paths = [path for path in paths if path.exists()]

    if not existing_paths:
        print("[check] SKIP: default dotenv files not found")
        return 0

    return _check_cr_in_files(existing_paths, "default dotenv files")


def _check_reference_integrity() -> int:
    # モジュール解決の実行時エラーは Ruff 単体では検知できないため、
    # pytest --collect-only や pyright/mypy で補完する。
    pytest_exit = _run(["uv", "run", "pytest", "tests/", "--collect-only", "-q"])
    if pytest_exit != 0:
        return pytest_exit

    if _can_run(["uv", "run", "pyright", "--version"]):
        pyright_exit = _run(["uv", "run", "pyright"])
        if pyright_exit != 0:
            return pyright_exit
    else:
        print("[check] SKIP: pyright is not available")

    if _can_run(["uv", "run", "mypy", "--version"]):
        mypy_exit = _run(["uv", "run", "mypy", "--explicit-package-bases", "src", "tests"])
        if mypy_exit != 0:
            return mypy_exit
    else:
        print("[check] SKIP: mypy is not available")

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run lint and CRLF checks for tracked files, plus optional dotenv validation.",
    )
    parser.add_argument(
        "--dotenv",
        help="Optional dotenv file to check locally, e.g. .env",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply Ruff auto-fixes locally (not intended for CI)",
    )
    parser.add_argument(
        "--skip-reference-check",
        action="store_true",
        help="Skip pytest collection check for import/reference integrity.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    ruff_check_cmd = ["uv", "run", "ruff", "check", "."]
    if _is_github_actions():
        # Emit GitHub-native annotations in CI for quick navigation.
        ruff_check_cmd.extend(["--output-format", "github"])
    if args.fix:
        ruff_check_cmd.append("--fix")

    lint_exit = _run(ruff_check_cmd)
    if lint_exit != 0:
        return lint_exit

    format_cmd = ["uv", "run", "ruff", "format"]
    if not args.fix:
        format_cmd.append("--check")
    format_cmd.append(".")

    format_exit = _run(format_cmd)
    if format_exit != 0:
        return format_exit

    repo_crlf_exit = _check_repo_crlf()
    if repo_crlf_exit != 0:
        return repo_crlf_exit

    default_dotenv_exit = _check_default_dotenv_files()
    if default_dotenv_exit != 0:
        return default_dotenv_exit

    if args.dotenv:
        dotenv_exit = _check_dotenv(args.dotenv)
        if dotenv_exit != 0:
            return dotenv_exit

    if not args.skip_reference_check:
        reference_exit = _check_reference_integrity()
        if reference_exit != 0:
            return reference_exit

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
