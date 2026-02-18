---
description: Build day devlog from sessions for a date
---

Generate a project devlog for date `$1` (format `YYYY-MM-DD`) and project slug `$2` (default to `ttcg` if omitted).

Process:

1. Load and use the `sessions-discovery` skill and run `python tools/list-sessions.py $1 --match $2` (default `$2` to `ttcg`) to find session transcripts.
2. For every discovered session, use the `session-summary` subagent to produce a concise summary.
3. Write one file per session to `summaries/$1-<sessionId>.md`.
4. Synthesize all per-session summaries into `notes/$1.md` with:
   - memorable lessons,
   - snippets/facts,
   - links to key references.
5. Keep the note engaging and memory-friendly, and include a short UTC timeline.

If `$1` is missing or invalid, stop and ask for a valid `YYYY-MM-DD` date.
