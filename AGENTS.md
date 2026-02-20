# Agent Workflow Notes

## Command Execution

- Run project commands with `uv run <command>`.
- Do not call project CLIs directly (for example `devlog-list-sessions`); use `uv run devlog-list-sessions`.

## Project Commands

- `uv run devlog-notes`
- `uv run devlog-build-site`
- `uv run devlog-list-sessions <YYYY-MM-DD> [--match <text>] [--exclude <text>] [--include-agent] [--projects-root <path>] [--codex-sessions-root <path>]`
- `uv run devlog-transcript-to-markdown`
