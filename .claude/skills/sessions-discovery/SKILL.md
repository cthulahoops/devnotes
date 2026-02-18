---
name: sessions-discovery
description: Discover assistant sessions with activity on a target date for a project.
---

# Sessions Discovery

Use this skill to produce a reliable list of session transcript files to summarize.

## When to use

- User asks for a date-based summary/devlog.
- You need to find which sessions had activity on a specific day.
- You need deterministic session paths before launching summarization agents.

## Inputs

- `date` in `YYYY-MM-DD` format (required)
- `project` identifier (for example `ttcg`) (required)

## Session roots

- Primary: `~/.claude/projects/*<project>*`
- Each root typically contains:
  - `sessions-index.json`
  - many `*.jsonl` session transcripts

## Discovery workflow

1. Resolve candidate roots under `~/.claude/projects/` that match the project identifier.
2. Within each candidate root, scan all `*.jsonl` session files.
3. Treat a session as active on the date when any JSON line includes a `timestamp` (or snapshot timestamp) starting with the target `YYYY-MM-DD`.
4. Exclude non-session helper files unless explicitly needed (for example, skip `agent-*.jsonl` unless they clearly represent the user-requested project sessions).
5. Return a sorted list of discovered sessions with minimal metadata.

## Preferred implementation approach

- Use `tools/list-sessions.py` for robust JSONL scanning.
- Do not rely only on `sessions-index.json` if it does not include the target date.

Primary command pattern:

```bash
python tools/list-sessions.py 2026-02-06 --match <project-slug>
```

Useful options:

- `--projects-root <path>` to override `~/.claude/projects`
- `--include-agent` to include `agent-*.jsonl` transcripts

## Required output format

Return only a newline-separated list of session file paths.

- One absolute path per line.
- No additional headers, metadata, or commentary.
- If no sessions are found, return an empty result.

## Quality checks

- Verify date format before scanning.
- Ensure all returned paths exist.
- Prefer deterministic ordering by `sessionId`.
- Keep output factual and concise.
- If `tools/list-sessions.py` is available, prefer it over ad-hoc one-off scanner snippets.
