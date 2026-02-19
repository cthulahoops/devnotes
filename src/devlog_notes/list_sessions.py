#!/usr/bin/env python3
"""List Claude project sessions with activity on a target date.

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


def parse_args() -> argparse.Namespace:
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
        "--include-agent",
        action="store_true",
        help="Include agent-*.jsonl session files",
    )
    return parser.parse_args()


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


def print_results(hits: list[str]) -> None:
    for path in hits:
        print(path)


def main() -> int:
    args = parse_args()
    date = validate_date(args.date)
    projects_root = os.path.expanduser(args.projects_root)

    roots = discover_project_roots(projects_root, args.match, args.exclude)
    if not roots:
        print(
            "No project roots found under "
            f"{projects_root!r} for --match {args.match!r} and --exclude {args.exclude!r}.",
            file=sys.stderr,
        )
        return 1

    hits = discover_sessions(roots, date, include_agent=args.include_agent)
    print_results(hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
