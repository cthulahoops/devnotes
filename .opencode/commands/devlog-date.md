---
description: Build day devlog from sessions for a date
---

Generate a devlog for date `$1` (format `YYYY-MM-DD`) across all non-client work. Optional project slug `$2` may be provided to narrow scope.

Process:

1. Load and use the `sessions-discovery` skill and run `python tools/list-sessions.py $1 --exclude clients` unless the user explicitly asks to include client work. If `$2` is provided, add `--match $2` to narrow scope.
2. For every discovered session, use the `session-summary` subagent to produce a concise summary.
3. Write one file per session to `summaries/$1-<sessionId>.md`.
4. Synthesize all per-session summaries into `notes/$1.md` with:
   - memorable lessons,
   - snippets/facts,
   - links to key references.
5. Keep the note engaging and memory-friendly, and include a short UTC timeline.

If `$1` is missing or invalid, stop and ask for a valid `YYYY-MM-DD` date.
