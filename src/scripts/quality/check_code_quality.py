import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
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
CHECK_ORDER = ("python", "yaml", "shell", "markdown", "docker", "toml", "terraform")
VERBOSE = False


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str
    failed_files: list[str]


CheckResult = tuple[str, int, int, str, list[str]]


def _extract_failed_files(text: str) -> list[str]:
    candidates: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Common patterns:
        # path/to/file.py:12: error ...
        # ./path/to/file.yml
        # path/to/file.yml  1:1 warning ...
        m = re.match(r"^([./A-Za-z0-9_\-][^:\s]*\.[A-Za-z0-9_\-]+):(\d+)(?::\d+)?", stripped)
        if m:
            candidates.add(m.group(1).lstrip("./"))
            continue

        m = re.match(r"^([./A-Za-z0-9_\-/]+\.[A-Za-z0-9_\-]+)\s+\d+", stripped)
        if m:
            candidates.add(m.group(1).lstrip("./"))
            continue

        m = re.match(r"^([./A-Za-z0-9_\-/]+\.[A-Za-z0-9_\-]+)$", stripped)
        if m:
            candidates.add(m.group(1).lstrip("./"))

    return sorted(candidates)


def _run(command: list[str], extra_env: dict[str, str] | None = None) -> CommandResult:
    if VERBOSE:
        print("[check]", " ".join(command))
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    completed_text = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if VERBOSE:
        if completed_text.stdout:
            print(completed_text.stdout, end="")
        if completed_text.stderr:
            print(completed_text.stderr, end="", file=sys.stderr)

    output_text = f"{completed_text.stdout}\n{completed_text.stderr}"
    return CommandResult(
        exit_code=completed_text.returncode,
        stdout=completed_text.stdout,
        stderr=completed_text.stderr,
        failed_files=_extract_failed_files(output_text),
    )


def _can_run(command: list[str]) -> bool:
    completed_text = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed_text.returncode == 0


def _is_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS", "").lower() == "true"


def _require_command(command: str) -> int:
    if shutil.which(command):
        return 0
    return 127


def _relative_paths(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(REPO_ROOT)) for path in paths]


def _report_step_result(check_name: str, started_at: float, status: str, target_count: int, detail: str = "") -> None:
    elapsed_sec = time.perf_counter() - started_at
    suffix = f" | {detail}" if detail else ""
    print(f"[check] {check_name:<9} | {status:<4} | targets={target_count:<3} | {elapsed_sec:.2f}s{suffix}")


def _print_failure_details(failed_files: list[str], stdout: str = "", stderr: str = "") -> None:
    if failed_files:
        print(f"[check] failed_files | {', '.join(failed_files)}")

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)


def _iter_tracked_files_by_patterns(*patterns: str) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", *patterns],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("git ls-files failed while collecting tracked files by patterns")

    files: list[Path] = []
    for raw_path in completed.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = REPO_ROOT / Path(raw_path.decode("utf-8"))
        if path.is_file():
            files.append(path)

    return sorted(files)


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
        return 0

    return _check_cr_in_files(existing_paths, "default dotenv files")


def _check_reference_integrity() -> tuple[int, str, list[str], str, str]:
    # モジュール解決の実行時エラーは Ruff 単体では検知できないため、
    # pytest --collect-only や pyright/mypy で補完する。
    pytest_result = _run(["uv", "run", "pytest", "tests/", "--collect-only", "-q"])
    if pytest_result.exit_code != 0:
        return (
            pytest_result.exit_code,
            "pytest collect",
            pytest_result.failed_files,
            pytest_result.stdout,
            pytest_result.stderr,
        )

    if _can_run(["uv", "run", "pyright", "--version"]):
        pyright_result = _run(["uv", "run", "pyright"])
        if pyright_result.exit_code != 0:
            return (
                pyright_result.exit_code,
                "pyright",
                pyright_result.failed_files,
                pyright_result.stdout,
                pyright_result.stderr,
            )
    if _can_run(["uv", "run", "mypy", "--version"]):
        mypy_result = _run(["uv", "run", "mypy", "--explicit-package-bases", "src", "tests"])
        if mypy_result.exit_code != 0:
            return (mypy_result.exit_code, "mypy", mypy_result.failed_files, mypy_result.stdout, mypy_result.stderr)

    return (0, "", [], "", "")


def _run_python_checks(args: argparse.Namespace) -> CheckResult:
    python_files = _iter_tracked_files_by_patterns("*.py", "*.pyi")
    if not python_files:
        return ("skip", 0, 0, "no tracked *.py/*.pyi", [])

    relative_python_files = _relative_paths(python_files)

    ruff_check_cmd = ["uv", "run", "ruff", "check", *relative_python_files]
    if _is_github_actions():
        # Emit GitHub-native annotations in CI for quick navigation.
        ruff_check_cmd.extend(["--output-format", "github"])
    if args.fix:
        ruff_check_cmd.append("--fix")

    lint_result = _run(ruff_check_cmd)
    if lint_result.exit_code != 0:
        _print_failure_details(lint_result.failed_files, lint_result.stdout, lint_result.stderr)
        return ("fail", lint_result.exit_code, len(python_files), "ruff check", lint_result.failed_files)

    format_cmd = ["uv", "run", "ruff", "format"]
    if not args.fix:
        format_cmd.append("--check")
    format_cmd.extend(relative_python_files)

    format_result = _run(format_cmd)
    if format_result.exit_code != 0:
        _print_failure_details(format_result.failed_files, format_result.stdout, format_result.stderr)
        return ("fail", format_result.exit_code, len(python_files), "ruff format", format_result.failed_files)

    repo_crlf_exit = _check_repo_crlf()
    if repo_crlf_exit != 0:
        return ("fail", repo_crlf_exit, len(python_files), "CRLF check", [])

    default_dotenv_exit = _check_default_dotenv_files()
    if default_dotenv_exit != 0:
        return ("fail", default_dotenv_exit, len(python_files), "default dotenv check", [])

    if args.dotenv:
        dotenv_exit = _check_dotenv(args.dotenv)
        if dotenv_exit != 0:
            return ("fail", dotenv_exit, len(python_files), "dotenv check", [args.dotenv])

    if not args.skip_reference_check:
        reference_exit, tool_name, failed_files, stdout, stderr = _check_reference_integrity()
        if reference_exit != 0:
            _print_failure_details(failed_files, stdout, stderr)
            return ("fail", reference_exit, len(python_files), f"reference integrity ({tool_name})", failed_files)

    detail = "tracked *.py/*.pyi; includes CRLF/default-dotenv/reference checks"
    return ("ok", 0, len(python_files), detail, [])


def _run_yaml_lint() -> CheckResult:
    yaml_files = _iter_tracked_files_by_patterns("*.yml", "*.yaml")
    if not yaml_files:
        return ("skip", 0, 0, "no tracked *.yml/*.yaml", [])

    result = _run(
        [
            "uv",
            "run",
            "--with",
            "yamllint",
            "yamllint",
            "-c",
            ".yamllint",
            *_relative_paths(yaml_files),
        ]
    )
    if result.exit_code != 0:
        _print_failure_details(result.failed_files, result.stdout, result.stderr)
        return ("fail", result.exit_code, len(yaml_files), "yamllint", result.failed_files)
    return ("ok", 0, len(yaml_files), "tracked *.yml/*.yaml", [])


def _run_shell_lint() -> CheckResult:
    shell_files = _iter_tracked_files_by_patterns("terraform/tf")
    if not shell_files:
        return ("skip", 0, 0, "no tracked shell targets", [])

    cmd_exit = _require_command("shellcheck")
    if cmd_exit != 0:
        return ("skip", 0, len(shell_files), "shellcheck not installed", _relative_paths(shell_files))

    result = _run(["shellcheck", *_relative_paths(shell_files)])
    if result.exit_code != 0:
        _print_failure_details(result.failed_files, result.stdout, result.stderr)
        return ("fail", result.exit_code, len(shell_files), "shellcheck", result.failed_files)
    return ("ok", 0, len(shell_files), "tracked terraform/tf", [])


def _run_markdown_lint() -> CheckResult:
    markdown_files = _iter_tracked_files_by_patterns("*.md")
    if not markdown_files:
        return ("skip", 0, 0, "no tracked *.md", [])

    cmd_exit = _require_command("markdownlint-cli2")
    if cmd_exit != 0:
        return ("skip", 0, len(markdown_files), "markdownlint-cli2 not installed", _relative_paths(markdown_files))

    result = _run(["markdownlint-cli2", *_relative_paths(markdown_files)])
    if result.exit_code != 0:
        _print_failure_details(result.failed_files, result.stdout, result.stderr)
        return ("fail", result.exit_code, len(markdown_files), "markdownlint-cli2", result.failed_files)
    return ("ok", 0, len(markdown_files), "tracked *.md", [])


def _run_docker_lint() -> CheckResult:
    docker_files = _iter_tracked_files_by_patterns("Dockerfile")
    if not docker_files:
        return ("skip", 0, 0, "no tracked Dockerfile", [])

    cmd_exit = _require_command("hadolint")
    if cmd_exit != 0:
        return ("skip", 0, len(docker_files), "hadolint not installed", _relative_paths(docker_files))

    result = _run(["hadolint", "--failure-threshold", "error", *_relative_paths(docker_files)])
    if result.exit_code != 0:
        _print_failure_details(result.failed_files, result.stdout, result.stderr)
        return ("fail", result.exit_code, len(docker_files), "hadolint", result.failed_files)
    return ("ok", 0, len(docker_files), "tracked Dockerfile", [])


def _run_toml_lint() -> CheckResult:
    toml_files = _iter_tracked_files_by_patterns("*.toml")
    if not toml_files:
        return ("skip", 0, 0, "no tracked *.toml", [])

    cmd_exit = _require_command("taplo")
    if cmd_exit != 0:
        return ("skip", 0, len(toml_files), "taplo not installed", _relative_paths(toml_files))

    result = _run(["taplo", "format", "--check", *_relative_paths(toml_files)])
    if result.exit_code != 0:
        _print_failure_details(result.failed_files, result.stdout, result.stderr)
        return ("fail", result.exit_code, len(toml_files), "taplo", result.failed_files)
    return ("ok", 0, len(toml_files), "tracked *.toml", [])


def _run_terraform_lint() -> CheckResult:
    terraform_files = _iter_tracked_files_by_patterns("terraform/**/*.tf", "terraform/*.tf")
    if not terraform_files:
        return ("skip", 0, 0, "no tracked terraform/*.tf", [])

    terraform_cmd_exit = _require_command("terraform")
    if terraform_cmd_exit != 0:
        return ("skip", 0, len(terraform_files), "terraform not installed", _relative_paths(terraform_files))

    tflint_cmd_exit = _require_command("tflint")
    if tflint_cmd_exit != 0:
        return ("skip", 0, len(terraform_files), "tflint not installed", _relative_paths(terraform_files))

    fmt_result = _run(["terraform", "fmt", "-check", *_relative_paths(terraform_files)])
    if fmt_result.exit_code != 0:
        _print_failure_details(fmt_result.failed_files, fmt_result.stdout, fmt_result.stderr)
        return ("fail", fmt_result.exit_code, len(terraform_files), "terraform fmt", fmt_result.failed_files)

    init_result = _run(["terraform", "-chdir=terraform", "init", "-backend=false"])
    if init_result.exit_code != 0:
        _print_failure_details(init_result.failed_files, init_result.stdout, init_result.stderr)
        return ("fail", init_result.exit_code, len(terraform_files), "terraform init", init_result.failed_files)

    validate_result = _run(["terraform", "-chdir=terraform", "validate"])
    if validate_result.exit_code != 0:
        _print_failure_details(validate_result.failed_files, validate_result.stdout, validate_result.stderr)
        return ("fail", validate_result.exit_code, len(terraform_files), "terraform validate", validate_result.failed_files)

    tflint_env = {
        "TF_VAR_loader_user_rsa_public_key": "dummy",
        "TF_VAR_dbt_user_rsa_public_key": "dummy",
        "TF_VAR_streamlit_user_rsa_public_key": "dummy",
    }
    tflint_result = _run(["tflint", "--chdir=terraform"], extra_env=tflint_env)
    if tflint_result.exit_code != 0:
        _print_failure_details(tflint_result.failed_files, tflint_result.stdout, tflint_result.stderr)
        return ("fail", tflint_result.exit_code, len(terraform_files), "tflint", tflint_result.failed_files)
    return ("ok", 0, len(terraform_files), "tracked terraform/*.tf", [])


def _run_named_check(name: str, args: argparse.Namespace) -> CheckResult:
    if name == "python":
        return _run_python_checks(args)
    if name == "yaml":
        return _run_yaml_lint()
    if name == "shell":
        return _run_shell_lint()
    if name == "markdown":
        return _run_markdown_lint()
    if name == "docker":
        return _run_docker_lint()
    if name == "toml":
        return _run_toml_lint()
    if name == "terraform":
        return _run_terraform_lint()

    return ("fail", 2, 0, f"unknown check: {name}", [])


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
    parser.add_argument(
        "--only",
        nargs="+",
        choices=CHECK_ORDER,
        help="Run only selected checks. Defaults to all checks in a fixed order.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show each underlying command while running checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    global VERBOSE
    VERBOSE = args.verbose

    selected_checks = list(args.only) if args.only else list(CHECK_ORDER)
    for check_name in selected_checks:
        started_at = time.perf_counter()
        status, exit_code, target_count, detail, failed_files = _run_named_check(check_name, args)
        _report_step_result(check_name, started_at, status, target_count, detail)
        if status == "fail":
            return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
