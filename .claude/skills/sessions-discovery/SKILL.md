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

- Use a small Python script from Bash for robust JSONL scanning.
- Do not rely only on `sessions-index.json` if it does not include the target date.

Example scanner pattern:

```bash
python - <<'PY'
import glob, json, os
base = os.path.expanduser('~/.claude/projects/-home-akelly-coding-ttcg')
date = '2026-02-06'

rows = []
for fp in glob.glob(os.path.join(base, '*.jsonl')):
    sid = os.path.basename(fp).replace('.jsonl', '')
    if sid.startswith('agent-'):
        continue
    count = 0
    first = None
    last = None
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            ts = obj.get('timestamp') or obj.get('snapshot', {}).get('timestamp')
            if isinstance(ts, str):
                if first is None or ts < first:
                    first = ts
                if last is None or ts > last:
                    last = ts
                if ts.startswith(date):
                    count += 1
    if count:
        rows.append((sid, fp, count, first, last))

for sid, fp, count, first, last in sorted(rows):
    print(f"{sid}\t{count}\t{first}\t{last}\t{fp}")
PY
```

## Required output format

Return compact, structured bullets:

- project root used
- target date
- discovered session count
- one bullet per session including:
  - `sessionId`
  - `path`
  - `activityCountOnDate`
  - `firstTimestamp`
  - `lastTimestamp`

If nothing is found, state that clearly and suggest the exact root/date combination that was checked.

## Quality checks

- Verify date format before scanning.
- Ensure all returned paths exist.
- Prefer deterministic ordering by `sessionId`.
- Keep output factual and concise.
