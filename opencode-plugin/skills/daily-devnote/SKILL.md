---
name: daily-devnote
description: Structure a concise, evidence-linked daily devnote with clear sections, quality rules, and uncertainty handling.
---

# Daily Devnote Structure

Use this skill when drafting or editing a single day note in `notes/YYYY-MM-DD.md`.

If asked to replace a note, don't read the old version, just overwrite with new content.

## Required output format

- Title (Markdown H1): first line must be a Markdown H1 (`# ...`) that is specific, evidence-grounded, and interesting without hype. Emphasize the single most interesting thing from the day.
  - Required format: `# <YYYY-MM-DD> - <title>`
  - Preferred style: measured hook + concrete technical payoff.
  - Recommended pattern: `<problem signal>, but <higher-impact engineering outcome>`
  - Good examples:
    - `# 2026-02-16 - The room-session bug was real, but the bigger win was safer campaign logic`
    - `# 2026-01-29 - Shell quoting looked minor, but it prevented deployment-footgun failures`
  - Avoid:
    - Generic labels (`non-client work`, `misc`, `summary`)
    - All-caps or emotional hype (`SHOCKING`, `INSANE`, `EVERYTHING CHANGED`)
    - Vague claims without artifacts (`made things better`)
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
  - Mark an item unresolved when there is evidence of intended follow-up or blocked completion in transcripts, commits, PRs, or issues.
  - If none, write `- None`.
- `## UTC timeline`
  - Use 3-8 compact entries: `HH:MM-HH:MM - action + artifact`.
  - Rounded timestamps are preferred for readability.
  - Exclude trivial housekeeping unless it materially changed direction/outcome.

## References

Put the references inline where relevant, and link to the reference.

Use absolute links only.

For summary links specifically, use absolute server paths (for example, `/summary/<file>.md`) rather than full URLs.

Required link styles:

- PRs must always use: `[PR #<number>](https://github.com/<org>/<repo>/pull/<number>)`
- Commit hashes must always be clickable links, and the linked text should be the short hash:
  - Example: [`a1b2c3d`](https://github.com/<org>/<repo>/commit/a1b2c3d4e5f6...)
- Conversation links must use a very short id label:
  - Example: `[edf](/summary/<file>.md)`


Don't include a references and evidence section.

## Quality rules

- Be precise, terse, and evidence-linked.
- Use a compact note budget: target 220-450 words for normal days; 120-260 words for low-activity days.
- Avoid motivational/thematic prose, personality framing, and generic "lessons learned" language.
- Distinguish fact vs inference:
  - Facts are directly supported by transcripts/commits/commands.
  - Inferences must be labeled `Inference:` and include why they are inferred.
- Preserve uncertainty. Do not present guesses as facts.
- If a detail is interesting but was not explicitly surfaced to the user during sessions, still include it in `Notable details worth remembering`.
- If there are fewer than 2 sessions or weak signal, produce a shorter note rather than filler content.
- Title tone should be curiosity with credibility: journalistic hook, engineering substance.

Ignore any sessions which don't involve interesting work. In particular ignore anything that's just summarising.
