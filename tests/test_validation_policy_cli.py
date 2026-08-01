import json

from coding_tablet.cli import main
from coding_tablet.network import NetworkPlan
from coding_tablet.registry import RiskLevel, ToolRegistry, ToolSpec
from coding_tablet.shell import ShellAdapter, ShellPolicy
from coding_tablet.actions import Observation


def test_registry_validates_required_fields():
    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            "echo",
            "Echo input",
            RiskLevel.SAFE,
            {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False},
        ),
        lambda text: Observation(True, "ok", {"text": text}),
    )

    missing = registry.call("echo")
    wrong_type = registry.call("echo", text=123)
    ok = registry.call("echo", text="hello")

    assert missing.ok is False
    assert "missing required fields" in missing.data["error"]
    assert wrong_type.ok is False
    assert ok.ok is True


def test_shell_policy_blocks_dangerous_command():
    result = ShellAdapter(True, policy=ShellPolicy()).run("rm -rf /tmp/example")
    assert result.ok is False
    assert result.summary == "shell command blocked"


def test_network_plan_validates_addresses():
    invalid = NetworkPlan(dns_servers=["not-ip"], ipv4="2001:db8::1/64").preview()
    valid = NetworkPlan(dns_servers=["1.1.1.1"], ipv4="192.0.2.10/24", ipv6="2001:db8::1/64").preview()

    assert invalid.ok is False
    assert invalid.data["errors"]
    assert valid.ok is True


def test_cli_tools_email_device_and_swarm(capsys):
    assert main(["tools"]) == 0
    tools = json.loads(capsys.readouterr().out)
    assert any(tool["name"] == "notepad.write" for tool in tools)

    assert main(["email", "--to", "user@example.com", "--subject", "Hi", "--body", "Body"]) == 0
    email = json.loads(capsys.readouterr().out)
    assert email["summary"] == "email draft preview created"

    assert main(["device", "click", "--target", "button"]) == 0
    device = json.loads(capsys.readouterr().out)
    assert device["data"]["mode"] == "dry-run"

    assert main(["swarm", "goal", "--step", "inspect"] ) == 0
    swarm = json.loads(capsys.readouterr().out)
    assert swarm["data"]["ready"] == ["step-1"]
