"""Command-line interface for coding-tablet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .device import DeviceAction, DeviceActionType
from .email_client import DraftEmail
from .network import NetworkPlan
from .session import ActionRequest
from .swarm import SwarmPlan
from .toolkit import CodingTablet
from .notepad import Notepad
from .shell import ShellAdapter
from .web import open_page


def _print(observation) -> None:
    print(json.dumps(observation.to_dict(), indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coding-tablet")
    subparsers = parser.add_subparsers(dest="command", required=True)

    shell = subparsers.add_parser("shell", help="Run a shell command when --allow is set.")
    shell.add_argument("command_text")
    shell.add_argument("--allow", action="store_true", help="Actually execute the command.")
    shell.add_argument("--timeout", type=int, default=30)

    web = subparsers.add_parser("web", help="Fetch a web page and extract text.")
    web.add_argument("url")

    note = subparsers.add_parser("note", help="Write a note inside the workspace.")
    note.add_argument("name")
    note.add_argument("text")
    note.add_argument("--workspace", type=Path, default=Path(".coding-tablet"))

    network = subparsers.add_parser("network", help="Preview network configuration intent.")
    network.add_argument("--dns", action="append", default=[])
    network.add_argument("--ipv4")
    network.add_argument("--ipv6")
    network.add_argument("--gateway")

    session = subparsers.add_parser("session", help="Start a traced session or run one approved action.")
    session.add_argument("goal")
    session.add_argument("--workspace", type=Path, default=Path(".coding-tablet"))
    session.add_argument("--tool")
    session.add_argument("--input", default="{}", help="JSON object passed to the tool.")
    session.add_argument("--approved", action="store_true")
    session.add_argument("--session-id")
    session.add_argument("--log", action="store_true", help="Print the session trace after running.")

    tools = subparsers.add_parser("tools", help="List model-facing tool specs.")
    tools.add_argument("--workspace", type=Path, default=Path(".coding-tablet"))

    email = subparsers.add_parser("email", help="Preview an email draft without sending it.")
    email.add_argument("--to", action="append", required=True)
    email.add_argument("--cc", action="append", default=[])
    email.add_argument("--subject", required=True)
    email.add_argument("--body", required=True)

    device = subparsers.add_parser("device", help="Preview a GUI/device action.")
    device.add_argument("action", choices=[item.value for item in DeviceActionType])
    device.add_argument("--target")
    device.add_argument("--value")

    swarm = subparsers.add_parser("swarm", help="Preview a basic swarm plan.")
    swarm.add_argument("goal")
    swarm.add_argument("--step", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "shell":
        _print(ShellAdapter(args.allow, args.timeout).run(args.command_text))
    elif args.command == "web":
        _print(open_page(args.url))
    elif args.command == "note":
        _print(Notepad(args.workspace).write(args.name, args.text))
    elif args.command == "network":
        _print(NetworkPlan(args.dns, args.ipv4, args.ipv6, args.gateway).preview())
    elif args.command == "session":
        tablet = CodingTablet(workspace=args.workspace)
        runtime = tablet.session(session_id=args.session_id)
        started = runtime.start(args.goal)
        if args.tool:
            payload = json.loads(args.input)
            _print(runtime.request(ActionRequest(args.tool, payload), approved=args.approved))
        elif args.log:
            print(runtime.trace_path.read_text(encoding="utf-8"), end="")
        else:
            _print(started)
    elif args.command == "tools":
        print(json.dumps(CodingTablet(workspace=args.workspace).registry().specs(), indent=2, sort_keys=True))
    elif args.command == "email":
        _print(DraftEmail(args.to, args.subject, args.body, args.cc).preview())
    elif args.command == "device":
        _print(DeviceAction(DeviceActionType(args.action), target=args.target, value=args.value).preview())
    elif args.command == "swarm":
        plan = SwarmPlan(args.goal)
        plan.add_role("operator", "Use available tools to make progress.", ("shell", "browser", "notepad"))
        for step in args.step:
            plan.add_step(step)
        _print(plan.preview())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
