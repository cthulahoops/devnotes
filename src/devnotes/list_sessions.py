#!/usr/bin/env python3
"""List assistant sessions with activity on a target date.

Example:
  python tools/list-sessions.py 2026-02-06 --exclude clients

Optional narrowing:
  python tools/list-sessions.py 2026-02-06 --match ttcg --exclude clients
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List session transcripts with activity on YYYY-MM-DD."
    )
    parser.add_argument("date", help="Target date in YYYY-MM-DD format")
    parser.add_argument(
        "--match",
        default="",
        help="Filter project directory names by substring (eg. ttcg)",
    )
    parser.add_argument(
        "--exclude",
        default="",
        help="Exclude project directory names by substring (opposite of --match)",
    )
    parser.add_argument(
        "--projects-root",
        default="~/.claude/projects",
        help="Base Claude projects directory (default: ~/.claude/projects)",
    )
    parser.add_argument(
        "--codex-sessions-root",
        default="~/.codex/sessions",
        help="Base Codex sessions directory (default: ~/.codex/sessions)",
    )
    parser.add_argument(
        "--include-agent",
        action="store_true",
        help="Include agent-*.jsonl session files",
    )
    return parser.parse_args(argv)


def validate_date(value: str) -> str:
    try:
        dt.datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date '{value}'. Expected YYYY-MM-DD.", file=sys.stderr)
        raise SystemExit(2)
    return value


def discover_project_roots(projects_root: str, match: str, exclude: str) -> list[str]:
    pattern = os.path.join(projects_root, "*")
    roots = [p for p in glob.glob(pattern) if os.path.isdir(p)]
    if match:
        needle = match.lower()
        roots = [p for p in roots if needle in os.path.basename(p).lower()]
    if exclude:
        blocked = exclude.lower()
        roots = [p for p in roots if blocked not in os.path.basename(p).lower()]
    return sorted(roots)


def date_in_line(line: str, date: str) -> bool:
    # Fast string checks; avoids JSON parsing every line.
    return f'"timestamp":"{date}' in line or f'"timestamp": "{date}' in line


def session_has_date(path: str, date: str) -> bool:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if date_in_line(line, date):
                return True
    return False


def date_only(iso_like: str | None) -> str | None:
    if not iso_like or len(iso_like) < 10:
        return None
    return iso_like[:10]


def indexed_allowed_sessions(
    root: str, date: str, include_agent: bool
) -> set[str] | None:
    """Return session IDs likely to include the target date.

    Uses sessions-index.json if available; returns None on parse/read failures.
    """
    index_path = os.path.join(root, "sessions-index.json")
    if not os.path.isfile(index_path):
        return None

    try:
        import json

        with open(index_path, "r", encoding="utf-8", errors="ignore") as handle:
            payload = json.load(handle)
    except Exception:
        return None

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return None

    allowed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        session_id = entry.get("sessionId")
        if not isinstance(session_id, str):
            continue
        if (not include_agent) and session_id.startswith("agent-"):
            continue

        created = date_only(entry.get("created"))
        modified = date_only(entry.get("modified"))

        # If index metadata is incomplete, keep the session in scope.
        if created is None or modified is None:
            allowed.add(session_id)
            continue

        if created <= date <= modified:
            allowed.add(session_id)

    return allowed


def discover_sessions(roots: list[str], date: str, include_agent: bool) -> list[str]:
    hits: list[str] = []
    for root in roots:
        allowed_ids = indexed_allowed_sessions(root, date, include_agent)
        if allowed_ids is not None and not allowed_ids:
            # Index can be stale; avoid false negatives.
            allowed_ids = None
        for path in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
            session_id = os.path.basename(path)[: -len(".jsonl")]
            if (not include_agent) and session_id.startswith("agent-"):
                continue
            if allowed_ids is not None and session_id not in allowed_ids:
                continue

            if not session_has_date(path, date):
                continue
            hits.append(path)

    hits.sort()
    return hits


def codex_date_dir(codex_root: str, date: str) -> str:
    year, month, day = date.split("-")
    return os.path.join(codex_root, year, month, day)


def codex_session_cwd(path: str) -> str | None:
    """Return cwd from the first session_meta event in a Codex transcript."""
    try:
        import json

        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if '"type":"session_meta"' not in line and '"type": "session_meta"' not in line:
                    continue
                payload = json.loads(line)
                body = payload.get("payload")
                if not isinstance(body, dict):
                    return None
                cwd = body.get("cwd")
                if isinstance(cwd, str) and cwd:
                    return cwd
                return None
    except Exception:
        return None
    return None


def codex_cwd_allowed(path: str, match: str, exclude: str) -> bool:
    if not match and not exclude:
        return True
    cwd = codex_session_cwd(path)
    if not cwd:
        # If metadata is unavailable, keep behavior permissive.
        return True

    cwd_lc = cwd.lower()
    if match and match.lower() not in cwd_lc:
        return False
    if exclude and exclude.lower() in cwd_lc:
        return False
    return True


def discover_codex_sessions(codex_root: str, date: str, match: str, exclude: str) -> list[str]:
    day_dir = codex_date_dir(codex_root, date)
    if not os.path.isdir(day_dir):
        return []

    hits: list[str] = []
    for path in sorted(glob.glob(os.path.join(day_dir, "*.jsonl"))):
        if not codex_cwd_allowed(path, match, exclude):
            continue
        if not session_has_date(path, date):
            continue
        hits.append(path)
    return hits


def print_results(hits: list[str]) -> None:
    for path in hits:
        print(path)


def run(
    *,
    date: str,
    match: str = "",
    exclude: str = "",
    projects_root: str = "~/.claude/projects",
    codex_sessions_root: str = "~/.codex/sessions",
    include_agent: bool = False,
) -> int:
    date = validate_date(date)
    projects_root = os.path.expanduser(projects_root)
    codex_sessions_root = os.path.expanduser(codex_sessions_root)

    roots = discover_project_roots(projects_root, match, exclude)
    claude_hits = discover_sessions(roots, date, include_agent=include_agent) if roots else []
    codex_hits = discover_codex_sessions(codex_sessions_root, date, match, exclude)
    hits = sorted(claude_hits + codex_hits)

    if not hits and not roots and not os.path.isdir(codex_date_dir(codex_sessions_root, date)):
        print(
            "No Claude project roots found under "
            f"{projects_root!r} and no Codex date directory found under {codex_sessions_root!r}.",
            file=sys.stderr,
        )
        return 1

    print_results(hits)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(
        date=args.date,
        match=args.match,
        exclude=args.exclude,
        projects_root=args.projects_root,
        codex_sessions_root=args.codex_sessions_root,
        include_agent=args.include_agent,
    )


if __name__ == "__main__":
    raise SystemExit(main())
