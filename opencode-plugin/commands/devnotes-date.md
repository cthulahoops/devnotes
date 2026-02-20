---
description: Build day devnotes from sessions for a date
---

Generate devnotes for date `$1` (format `YYYY-MM-DD`) across all non-client work. Optional project slug `$2` may be provided to narrow scope.

Process:

1. Load and use the `sessions-discovery` skill to discover relevant sessions for date `$1`, optionally narrowed by `$2` when provided.
2. For every discovered session, use the `session-summary` subagent to produce a concise summary.
3. Write one file per session to `summaries/$1-<sessionId>.md`.
4. Load and use the `daily-devnote` skill.
5. Synthesize all per-session summaries into `notes/$1.md` using the `daily-devnote` skill structure. Optimize for future retrieval, not storytelling.

If `$1` is missing or invalid, stop and ask for a valid `YYYY-MM-DD` date.
