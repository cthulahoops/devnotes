# Agent Workflow Notes

## Command Execution

- Run project commands with `uv run <command>`.
- Do not call project CLIs directly (for example `devnotes-list-sessions`); use `uv run devnotes-list-sessions`.

## Project Commands

- `uv run devnotes`
- `uv run devnotes-build-site`
- `uv run devnotes-list-sessions <YYYY-MM-DD> [--match <text>] [--exclude <text>] [--include-agent] [--projects-root <path>] [--codex-sessions-root <path>]`
- `uv run devnotes-transcript-to-markdown`
