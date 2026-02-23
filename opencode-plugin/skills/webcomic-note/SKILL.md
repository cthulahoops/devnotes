---
name: webcomic-note
description: Generate a daily-note webcomic from git patches and insert it directly under the note title.
---

# Webcomic Note

Use this skill when the user wants a webcomic added to `notes/YYYY-MM-DD.md`.

## Inputs

- Target date (`YYYY-MM-DD`)
- Optional style direction from the user (for example: "depict the developer as a lizard")

## Workflow

1. Identify the most interesting change from the day.
   - Prefer concrete shipped work (commit/PR level changes).
   - Use `git show` when a single commit is most interesting.
   - Use `git log -p` when a multi-commit story is more representative.
2. Generate the comic by piping literal git patch output into the CLI:

```bash
git show <commit> | uv run devnotes generate-webcomic --date <YYYY-MM-DD> --title "<title>"
```

or

```bash
git log -p --since "<YYYY-MM-DD> 00:00" --until "<YYYY-MM-DD> 23:59" | uv run devnotes generate-webcomic --date <YYYY-MM-DD> --title "<title>"
```

3. If the user supplied style direction, pass:

```bash
--additional-prompt "<user instructions>"
```

4. Use the generated output path under `images/` and insert this markdown immediately after the note H1:

```md
![<title>](/images/<filename.ext>)
```

5. If an image markdown line already exists directly under the H1 and points to `/images/`, replace it instead of adding a duplicate.

## Guardrails

- Do not invent patch content; always use literal command output.
- Keep the title brief and specific, because it is used for filename slugging.
- If generation fails, report the error and do not edit the note.
