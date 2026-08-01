from coding_tablet.device import DeviceAction, DeviceActionType
from coding_tablet.swarm import TaskStatus
from coding_tablet.toolkit import CodingTablet


def test_swarm_plan_tracks_ready_steps():
    plan = CodingTablet().plan_swarm("ship a feature")
    first = plan.add_step("inspect files")
    second = plan.add_step("write patch", depends_on=(first.id,))

    assert [step.id for step in plan.next_ready_steps()] == [first.id]
    first.status = TaskStatus.COMPLETE
    assert [step.id for step in plan.next_ready_steps()] == [second.id]


def test_device_action_is_dry_run_preview():
    result = DeviceAction(DeviceActionType.CLICK, target="submit button").preview()
    assert result.ok is True
    assert result.data["mode"] == "dry-run"
    assert result.data["action_type"] == "click"
