---
description: Build day devnotes from sessions for a date
---

Generate devnotes for date `$1` across all non-client work. Optional project slug `$2` may be provided to narrow scope.

Accept flexible date descriptions for `$1` (for example `yesterday`, `today`, `last friday`, `2026-02-20`) and resolve to canonical `YYYY-MM-DD` before running.

Process:

1. Resolve `$1` into a canonical date string `YYYY-MM-DD`.
2. Load and use the `sessions-discovery` skill to discover relevant sessions for the resolved date, optionally narrowed by `$2` when provided.
3. Always exclude both `clients` and `sandbox` projects while listing sessions unless explicitly asked otherwise.
4. For every discovered session, use the `session-summary` subagent to produce a concise summary.
5. Write one file per session to `summaries/<resolvedDate>-<sessionId>.md`.
6. Load and use the `daily-devnote` skill.
7. Synthesize all per-session summaries into `notes/<resolvedDate>.md` using the `daily-devnote` skill structure. Optimize for future retrieval, not storytelling.
8. When the user asks for a comic (or confirms they want one), load and use the `webcomic-note` skill to add a generated image directly under the note title.

If `$1` is missing or cannot be resolved to a valid date, stop and ask for a valid date input.
