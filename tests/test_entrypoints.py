"""Exercise installed console scripts without authenticating or reading user data."""

import subprocess
import sys
from pathlib import Path

import pytest


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
    executable = Path(sys.executable).parent / command
    result = subprocess.run(
        [str(executable), *args], capture_output=True, text=True, timeout=15, check=False
    )
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


@pytest.mark.parametrize("command", ["mct", "meeting-cost"])
def test_installed_script_rejects_unknown_command(command):
    executable = Path(sys.executable).parent / command
    result = subprocess.run(
        [str(executable), "not-a-command"], capture_output=True, text=True, timeout=15, check=False
    )
    assert result.returncode != 0
    assert "No such command" in result.stderr
