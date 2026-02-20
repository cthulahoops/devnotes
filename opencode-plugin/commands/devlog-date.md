---
description: Build day devlog from sessions for a date
---

Generate a devlog for date `$1` (format `YYYY-MM-DD`) across all non-client work. Optional project slug `$2` may be provided to narrow scope.

Process:

1. Load and use the `sessions-discovery` skill and run `devlog-list-sessions $1 --exclude clients` unless the user explicitly asks to include client work. If `$2` is provided, add `--match $2` to narrow scope.
2. For every discovered session, use the `session-summary` subagent to produce a concise summary.
3. Write one file per session to `summaries/$1-<sessionId>.md`.
4. Synthesize all per-session summaries into `notes/$1.md` using the exact structure below. Optimize for future retrieval, not storytelling.

Required output format for `notes/$1.md`:

- Title: specific and content-bearing. Never use generic labels like "non-client work", "misc", or "summary".
  - Good title pattern: `<YYYY-MM-DD> - <top 2-4 concrete themes or artifacts>`
  - Example: `2026-01-29 - objective final-state fixes, sprite automation, shell quoting hardening`
- `## What I actually did`
  - 3-8 bullets, each starting with a strong verb.
  - Include concrete objects: file paths, commit hashes, script names, test names, commands, URLs, issue IDs.
  - No vague bullets ("worked on tooling", "investigated bug") without specifics.
  - Collapse routine/low-signal actions (rebases, routine test runs, formatting/lint-only passes) unless they changed outcomes.
- `## Notable details worth remembering`
  - Include 2-6 high-signal details that are easy to forget but useful later.
  - Prefer details that change decisions/debugging speed (edge cases, command semantics, environment gotchas, rejected hypotheses, safety caveats).
  - Keep each item concrete and attributable to a session artifact.
- `## Open loops / unresolved`
  - Include only explicitly unresolved work: unknowns, pending confirmations, and what evidence is still needed.
  - Do not treat interruption/disconnect/session-end alone as an open loop.
  - Mark an item unresolved only if there is transcript evidence of intended follow-up or blocked completion.
  - If none, write `- None`.
- `## Evidence and references`
  - Group by type where possible: commits, session summaries, transcripts, PRs, docs reviewed.
  - Every major claim in the note must map to at least one reference.
- `## UTC timeline`
  - Use 3-8 compact entries: `HH:MM-HH:MM - action + artifact`.
  - Exclude trivial housekeeping unless it materially changed direction/outcome.

Quality rules:

- Be precise, terse, and evidence-linked.
- Use a compact note budget: target 220-450 words for normal days; 120-260 words for low-activity days.
- Avoid motivational/thematic prose, personality framing, and generic "lessons learned" language.
- Distinguish fact vs inference:
  - Facts are directly supported by transcripts/commits/commands.
  - Inferences must be labeled `Inference:` and include why they are inferred.
- Preserve uncertainty. Do not present guesses as facts.
- If a detail is interesting but was not explicitly surfaced to the user during sessions, still include it in `Notable details worth remembering`.
- If there are fewer than 2 sessions or weak signal, produce a shorter note rather than filler content.

If `$1` is missing or invalid, stop and ask for a valid `YYYY-MM-DD` date.
