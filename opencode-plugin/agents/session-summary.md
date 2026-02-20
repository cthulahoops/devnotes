---
description: Generates session summaries
mode: subagent
model: openai/gpt-5.1-codex-mini
---

Generate a structured, evidence-first session summary from a transcript.
Convert the jsonl to markdown using:

uv run devnotes transcript-to-markdown --only-tools Bash --include-thinking <transcript.jsonl>

Then produce a markdown summary with this exact structure:

- `# Session <sessionId> - <specific title>`
- `## Goal`
  - 1-3 bullets, concrete and specific.
- `## Actions`
  - 2-6 bullets describing what was done.
  - Include concrete artifacts: commands, files, tests, commits, scripts, URLs, errors.
  - Omit routine/low-signal actions (rebases, routine test runs, formatting/lint-only passes) unless they changed outcomes.
- `## Outcomes`
  - Completed results and their artifacts.
  - Separate unresolved items under `### Unresolved`.
  - Only add `### Unresolved` entries when transcript evidence shows explicit unfinished intent or blockage.
  - Do not mark interruption/disconnect/session-end alone as unresolved.
- `## Notable details worth remembering`
  - High-signal details that improve future debugging/search (edge cases, gotchas, rejected hypotheses, caveats).
  - Include details even if they were not explicitly surfaced to the user in-session.
- `## Evidence`
  - `- Commits:` links + short hashes + working directory
  - `- Files touched:` paths (if determinable)
  - `- Key commands:` exact commands (if present)
  - `- Session window:` ISO start/end timestamps (or best available)
  - `- Transcript:` path

Rules:

- Prefer fact statements grounded in transcript evidence.
- If a statement is inferred, prefix it with `Inference:` and explain briefly.
- Avoid motivational language and generic assessments ("went well", "tightened rules", "focused day").
- Do not omit useful technical details just because they appear routine if they are needed for reconstruction/search.
- Keep it concise and skimmable.
- Keep a strict length budget: target 120-220 words for typical sessions.
