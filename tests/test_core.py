from pathlib import Path

import pytest

from coding_tablet.network import NetworkPlan
from coding_tablet.notepad import Notepad
from coding_tablet.shell import ShellAdapter


def test_shell_requires_explicit_allow():
    result = ShellAdapter().run("echo should-not-run")
    assert result.ok is False
    assert result.summary == "shell execution is disabled"


def test_notepad_stays_inside_workspace(tmp_path: Path):
    pad = Notepad(tmp_path)
    result = pad.write("notes/todo.txt", "ship scaffold")
    assert result.ok is True
    assert pad.read("notes/todo.txt").data["text"] == "ship scaffold"

    with pytest.raises(ValueError):
        pad.write("../escape.txt", "nope")


def test_network_plan_is_dry_run():
    result = NetworkPlan(dns_servers=["1.1.1.1"], ipv4="192.0.2.10/24").preview()
    assert result.ok is True
    assert result.data["mode"] == "dry-run"
    assert result.data["dns_servers"] == ["1.1.1.1"]
