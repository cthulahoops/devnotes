# Devlog Generation

Use this skill to produce high-signal daily devlogs from local assistant session data, git history, and PR metadata.

## When to use

- User asks for a daily/weekly progress summary.
- User wants a polished update from multiple session logs.
- User wants references and evidence links.

## Primary objective

Produce a concise, accurate log entry in `notes/YYYY-MM-DD.md` with:

1. What was shipped
2. Key decisions and rationale
3. Timeline
4. References (session logs, PRs, commits)
5. Open follow-ups

## Inputs

- Date to summarize (default: explicit date from user)
- Project filter (e.g. `ttcg`)
- Session roots:
  - `~/.claude/projects/*<project>*`
  - `~/.codex/sessions/YYYY/MM/DD`
- Optional repo path for git/gh validation

## Workflow

### 1) Discover relevant sessions quickly

- Find matching project session files.
- Filter to the target date.
- Keep a list of candidate session paths.

### 2) Use parallel subagents for first-pass summaries (important)

Run multiple subagents concurrently for speed and coverage:

- One subagent per candidate session or per small batch.
- Use lightweight models for extraction/summarization tasks.
- Ask each subagent to return structured output only:
  - session path/id
  - start/end timestamps
  - key actions
  - decisions/tradeoffs
  - artifacts (commits, PRs, files)

Then run one synthesis pass to merge and deduplicate.

### 3) Validate with source-of-truth checks

- Confirm PR states and metadata via `gh pr view`.
- Confirm commit existence and branch context via `git log`/`git branch`.
- Resolve contradictions explicitly (for example, session claim vs repo reality).

### 4) Draft the devlog entry

Write `notes/YYYY-MM-DD.md` with this template:

```md
# YYYY-MM-DD — <project> day summary

<1-2 sentence headline>

## What I shipped
- ...

## Key decisions and rationale
- ...

## Timeline (UTC)
- HH:MM–HH:MM: ...

## References
- session file paths
- PR URLs
- commit SHAs

## Open follow-ups
- ...
```

### 5) Quality bar

- Prefer concrete outcomes over activity descriptions.
- Include only claims with references.
- Keep tone factual and concise.
- Call out uncertainty when evidence is partial.

## Suggested subagent prompts

### Per-session extraction prompt

```text
Read this session transcript and extract:
1) start/end times
2) concrete actions taken
3) decisions and rationale
4) produced artifacts (commits/PRs/files)
5) unresolved follow-ups
Return as compact bullets, no prose.
```

### Synthesis prompt

```text
Merge these per-session bullets into one day summary with:
- shipped outcomes
- key decisions
- UTC timeline
- references list
- open follow-ups
Avoid duplicates and preserve only evidence-backed claims.
```

## Notes on model strategy

- Be aggressive about parallelism for summarization tasks.
- Use light models for extraction; reserve heavier models for final synthesis and ambiguity resolution.
- If there are many sessions, do map-reduce style summarization:
  - map: many small parallel summaries
  - reduce: one final merged narrative
