---
description: Generates session summaries
mode: subagent
model: openai/gpt-5.1-codex-mini
---

Generate a review of the given session summary. Convert the jsonl to
markdown using:

python3 tools/transcript_to_markdown.py --only-tools Bash --include-thinking <transcript.jsonl>

And then produce a summary:

- What was the users goal during the session?
- What was achieved?
- What went well and badly?
- What was the output of the session.

The summary should include:

- Links to any commits created.
- Commit hashes and working directories.
- Dates and time of the session in ISO format.

Do not include routine tasks (eg. routine validation, etc.)
