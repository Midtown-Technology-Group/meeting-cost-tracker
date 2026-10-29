"""Exercise installed console scripts without authenticating or reading user data."""

import os
import subprocess
import sysconfig
from pathlib import Path

import pytest


def _script_path(command):
    suffix = ".exe" if os.name == "nt" else ""
    return Path(sysconfig.get_path("scripts")) / (command + suffix)


@pytest.mark.parametrize("platform_name, suffix", [("posix", ""), ("nt", ".exe")])
def test_script_path_uses_install_scripts_directory(monkeypatch, tmp_path, platform_name, suffix):
    from types import SimpleNamespace

    monkeypatch.setattr(sysconfig, "get_path", lambda name: str(tmp_path / "Scripts"))
    monkeypatch.setitem(globals(), "os", SimpleNamespace(name=platform_name))
    assert _script_path("mct") == tmp_path / "Scripts" / ("mct" + suffix)


@pytest.mark.parametrize("command", ["mct", "meeting-cost"])
@pytest.mark.parametrize(
    "args, expected",
    [
        (["--help"], "Analyze meeting costs"),
        (["--version"], "version 0.1.0"),
        (["analyze", "--help"], "--weeks"),
    ],
)
def test_installed_script_dispatches(command, args, expected):
    executable = _script_path(command)
    result = subprocess.run(
        [str(executable), *args], capture_output=True, text=True, timeout=15, check=False
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


@pytest.mark.parametrize("command", ["mct", "meeting-cost"])
def test_installed_script_rejects_unknown_command(command):
    executable = _script_path(command)
    result = subprocess.run(
        [str(executable), "not-a-command"], capture_output=True, text=True, timeout=15, check=False
    )
    assert result.returncode != 0
    assert "No such command" in result.stderr
