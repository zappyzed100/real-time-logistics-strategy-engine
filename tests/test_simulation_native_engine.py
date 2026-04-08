import importlib


def test_preferred_compiler_defaults_to_gpp(monkeypatch):
    monkeypatch.delenv("SIMULATION_NATIVE_COMPILER", raising=False)

    module = importlib.import_module("src.simulation.native_engine")

    assert module._preferred_compiler() == "clang++"


def test_preferred_compiler_uses_environment_override(monkeypatch):
    monkeypatch.setenv("SIMULATION_NATIVE_COMPILER", "clang++")

    module = importlib.import_module("src.simulation.native_engine")

    assert module._preferred_compiler() == "clang++"


def test_compiler_command_uses_lld_for_clang(monkeypatch, tmp_path):
    module = importlib.import_module("src.simulation.native_engine")
    monkeypatch.setenv("SIMULATION_NATIVE_COMPILER", "clang++")

    def fake_which(command: str) -> str | None:
        if command == "clang++":
            return "/usr/bin/clang++"
        if command == "ld.lld":
            return "/usr/bin/ld.lld"
        return None

    monkeypatch.setattr(module.shutil, "which", fake_which)

    command = module._compiler_command(tmp_path / "engine.so", tmp_path / "engine.cpp")

    assert command[0] == "/usr/bin/clang++"
    assert "-fuse-ld=lld" in command


def test_compiler_command_uses_gpp_without_lld(monkeypatch, tmp_path):
    module = importlib.import_module("src.simulation.native_engine")
    monkeypatch.setenv("SIMULATION_NATIVE_COMPILER", "g++")

    def fake_which(command: str) -> str | None:
        if command == "g++":
            return "/usr/bin/g++"
        return None

    monkeypatch.setattr(module.shutil, "which", fake_which)

    command = module._compiler_command(tmp_path / "engine.so", tmp_path / "engine.cpp")

    assert command[0] == "/usr/bin/g++"
    assert "-fuse-ld=lld" not in command
