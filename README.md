# coding-tablet

`coding-tablet` is an open-source control plane that gives small local AI models
(such as Llama, TinyLlama, Phi, Gemma, or Qwen variants) a simple, auditable way
to operate a computer-like workspace.

The project starts with a safe Python SDK and CLI that expose practical tools:

- run shell commands through Linux shells, PowerShell, or `cmd` adapters;
- fetch and inspect web pages in a browser-like session;
- read, write, and edit notepad-style text files inside a workspace;
- describe target operating-system profiles for Linux, Windows, macOS, and
  ChromeOS;
- model network configuration intent for DNS, IPv4, and IPv6 before applying it;
- return structured observations that are easy for small models to parse;
- draft email messages for human review without sending them;
- integrate all tools through one `CodingTablet` facade for model runtimes;
- plan multi-agent computer-use work with a small, auditable swarm planner;
- preview GUI/device actions such as click, type, hotkey, wait, and screenshot.

> Status: initial repository scaffold. The default runtime is intentionally
> conservative: shell commands are executed only when explicitly enabled, and
> network configuration is represented as a dry-run plan.

## Why this exists

Small models are often good at following short instructions but need a compact,
consistent interface for desktop tasks. `coding-tablet` aims to be that interface:
a tablet-like layer of tools with predictable schemas, guardrails, and logs.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
coding-tablet --help
```

Run a shell command explicitly:

```bash
coding-tablet shell --allow "echo hello"
```

Open a web page as text and extract readable links:

```bash
coding-tablet web https://example.com
```

Write a note in the default workspace:

```bash
coding-tablet note ideas.txt "Build a browser automation adapter next."
```

Draft a local email preview without sending it:

```python
from coding_tablet import CodingTablet

tablet = CodingTablet()
print(tablet.draft_email(["user@example.com"], "Hello", "Draft body").to_dict())
```

Preview a network configuration plan:

```bash
coding-tablet network --dns 1.1.1.1 --ipv4 192.0.2.10/24 --gateway 192.0.2.1
```

Start an auditable session trace:

```bash
coding-tablet session "research and summarize a topic"
```

Run an approved tool action inside a traced session:

```bash
coding-tablet session "write a note" --tool notepad.write --input '{"name":"todo.txt","text":"Next step"}'
```

List model-facing tools with risk metadata and input schemas:

```bash
coding-tablet tools
```

Preview email, device, and swarm actions:

```bash
coding-tablet email --to user@example.com --subject "Hello" --body "Draft only"
coding-tablet device click --target "submit button"
coding-tablet swarm "research and implement a task" --step "open references"
```

## Kimi-style inspiration

The architecture is intentionally inspired by recent computer-use agent patterns:

- **live computer sessions**: keep state such as browser history and workspace files;
- **agent swarms / claw groups**: split larger work into role-based task steps;
- **visual-agent future path**: normalize GUI actions now so real screenshot/click/type
  backends can be added later;
- **human approval gates**: preview risky actions, email sending, and network changes
  before any privileged adapter applies them.

Create a swarm plan from Python:

```python
from coding_tablet import CodingTablet

tablet = CodingTablet()
plan = tablet.plan_swarm("Research, build, and review a small website")
plan.add_step("Open references in the browser", role="operator")
plan.add_step("Review the final files", role="reviewer", depends_on=("step-1",))
print(plan.preview().to_dict())
```

## Runtime architecture

The next layer is a `SessionRuntime` that turns tools into auditable
plan-act-observe workflows. A runtime has a tool registry, writes `trace.jsonl`
events, and returns approval requests when risky tools are called without
explicit approval.

Model integrations can use the registry to show a compact list of callable tools
to Llama/TinyLlama-style runtimes, then feed each proposed action back through
the same approval and tracing path. Tool inputs are validated against a compact
JSON-schema subset before handlers run. Minimal Ollama and OpenAI-compatible
client interfaces are included as the first provider adapters.

## Design principles

1. **Small-model friendly**: short commands, JSON-compatible observations, and
   deterministic error messages.
2. **Safe by default**: command execution requires explicit opt-in and network
   changes are dry-run plans until an adapter implements privileged changes.
3. **Portable**: adapters model Linux, Windows, macOS, and ChromeOS separately.
4. **Composable**: every capability is a tool that can be called by an agent,
   CLI, HTTP service, or test harness.

## Roadmap

- [ ] Add Playwright-based visual browser automation.
- [ ] Connect `DeviceAction` previews to real screenshot/click/type backends.
- [x] Add persistent session logs.
- [ ] Add session replay.
- [x] Add minimal provider adapters for local LLM runtimes.
- [x] Add compact input validation for registered tools.
- [ ] Add robust prompt templates for tool selection and self-review.
- [ ] Add SMTP/IMAP adapters behind explicit human approval gates.
- [ ] Add real OS-specific network configuration backends behind confirmations.
- [ ] Add desktop app sandbox profiles for common training/evaluation tasks.

## License

This project is licensed under the GNU General Public License v3.0. See
[`LICENSE`](LICENSE).
