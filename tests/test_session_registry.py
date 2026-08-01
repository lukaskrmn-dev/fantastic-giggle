import json

from coding_tablet.registry import RiskLevel, ToolRegistry, ToolSpec
from coding_tablet.session import ActionRequest, SessionRuntime
from coding_tablet.actions import Observation
from coding_tablet.toolkit import CodingTablet


def test_registry_lists_specs_and_calls_tool():
    registry = ToolRegistry()
    registry.register(ToolSpec("echo", "Echo input", RiskLevel.SAFE), lambda text: Observation(True, "ok", {"text": text}))

    assert registry.specs()[0]["name"] == "echo"
    assert registry.call("echo", text="hello").data == {"text": "hello"}


def test_session_runtime_requires_approval_and_writes_trace(tmp_path):
    registry = ToolRegistry()
    registry.register(ToolSpec("danger", "Dangerous action", RiskLevel.HIGH, requires_approval=True), lambda: Observation(True, "done", {}))
    runtime = SessionRuntime(registry, tmp_path, session_id="test-session")

    started = runtime.start("test goal")
    denied = runtime.request(ActionRequest("danger"))
    approved = runtime.request(ActionRequest("danger"), approved=True)

    assert started.ok is True
    assert denied.ok is False
    assert denied.summary == "approval required"
    assert approved.ok is True
    lines = (tmp_path / "sessions" / "test-session" / "trace.jsonl").read_text().splitlines()
    assert [json.loads(line)["phase"] for line in lines] == ["start", "approval_required", "act", "observe"]


def test_toolkit_registry_contains_default_tools():
    specs = CodingTablet(workspace=".unused").registry().specs()
    names = {spec["name"] for spec in specs}
    assert {"shell.run", "browser.open", "notepad.write", "network.preview"}.issubset(names)
