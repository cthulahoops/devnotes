---
name: fetch-remote-sessions
description: Fetch assistant session data from a remote sandbox host via scp, normalize sandbox project paths, and place files into local Claude/Codex session directories.
---

# Fetch Remote Sessions

Use this skill when the user asks for remote session sync, especially with phrasing like:

- `Fetch session data from '<host>'`

## Inputs

- Required: remote ssh target (`<host>`, usually `user@host`)
- Optional: local dev root path (default: `~/coding`)

## Workflow

1. Confirm target host and local dev root.
2. Run the bundled script:

```bash
opencode-plugin/skills/fetch-remote-sessions/scripts/fetch_remote_sessions.sh "<host>" "<local-dev-directory>"
```

3. Report:
   - discovered remote Claude project roots
   - discovered remote Codex date directories
   - copied counts
   - any skipped/failed copies

## What the script does

- Inspects remote directories before copying:
  - `~/.claude/projects`
  - `~/.codex/sessions`
- Copies discovered data via `scp` into local:
  - `~/.claude/projects`
  - `~/.codex/sessions`
- Normalizes sandbox project root naming for Claude projects:
  - remote prefix `/home/sandbox-user/project/<repo>`
  - local prefix `<local-dev-directory>/<repo>`
- Normalizes embedded paths inside copied `*.jsonl` files:
  - `/home/sandbox-user/project/...` -> `<local-dev-directory>/...`

## Safety and behavior notes

- This is additive sync only; it does not delete local files.
- If ssh/scp access fails, stop and report the failing command.
- Keep output concise and factual.
