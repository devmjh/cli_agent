# CLI Agent

Agentic CLI (Codex-style) with enterprise-first guardrails:

- Default-deny permissions (`read`, `write`, `shell`, `net`)
- Workspace-restricted file IO
- OpenAI GPT-4o adapter via API key from environment
- Swappable LLM adapter layer
- Interactive chat and one-shot run modes

## Features (v1)

- `cli-agent chat` interactive REPL with slash commands
- `cli-agent run "<goal>"` non-interactive agent run
- `cli-agent doctor` environment and connectivity checks
- `cli-agent config ...` persistent TOML settings

Slash commands in chat:

- `/help`
- `/exit`
- `/model gpt-4o`
- `/status`
- `/allow <read|write|shell|net>`
- `/deny <read|write|shell|net>`
- `/workspace <path>`
- `/run [goal]`
- `/diff`
- `/reset`

## Install (Windows-friendly)

From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

On Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Secrets and environment

Create `~/.env`:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o
# Optional corporate gateway/base URL
# OPENAI_BASE_URL=https://your-corporate-gateway/v1
```

CLI also reads process env vars directly.

## Usage

```bash
cli-agent doctor
cli-agent config show
cli-agent chat
cli-agent run "Summarize README and suggest improvements"
```

With auto-approve for permitted tools:

```bash
cli-agent run "List files and read README" --yes
```

## Permission model

Default is deny for all capabilities.

- `read`: file reads/listing (restricted to workspace)
- `write`: file writes/patching (restricted to workspace)
- `shell`: subprocess tool execution
- `net`: reserved for future tooling (disabled in v1)

The LLM network call itself is part of core operation, not a user-invoked `net` tool.

Session overrides via slash commands:

- `/allow shell`
- `/deny write`

## Config and logs

Config path uses `platformdirs`:

- Windows: `%USERPROFILE%\\AppData\\Local\\cli-agent\\cli-agent\\config.toml` (platform-dependent)
- Linux/macOS: under `~/.config` by default

Logs are JSONL under the platform log directory.

## Architecture

- `cli_agent/cli.py` Typer entrypoint
- `cli_agent/repl.py` interactive chat and slash routing
- `cli_agent/config.py` config load/save
- `cli_agent/permissions.py` default-deny permissions and session overrides
- `cli_agent/workspace.py` safe workspace path checks
- `cli_agent/tools/*` filesystem/shell/git helpers
- `cli_agent/llm/openai_adapter.py` OpenAI-compatible adapter
- `cli_agent/agent/loop.py` one-tool-per-turn run loop

## Notes

- v1 supports one tool call per model turn and max iteration cap.
- `apply_patch` tool supports a minimal unified diff format for safe MVP patching.
