#!/usr/bin/env python3
"""Convert a Claude-style session JSONL transcript into conversation markdown."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Turn:
    index: int
    role: str
    timestamp: str | None
    body: str


@dataclass
class ParseResult:
    turns: list[Turn]
    first_timestamp: str | None
    last_timestamp: str | None
    session_ids: set[str]
    models: set[str]
    versions: set[str]
    cwd_values: set[str]
    branches: set[str]
    role_counts: dict[str, int]
    usage_counts: dict[str, int]
    usage_records: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read a session transcript JSONL and output markdown conversation."
    )
    parser.add_argument("input", type=Path, help="Input transcript JSONL path")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output markdown file path (defaults to stdout)",
    )
    parser.add_argument(
        "--include-thinking",
        action="store_true",
        help="Include hidden thinking blocks when present",
    )
    parser.add_argument(
        "--include-tools",
        action="store_true",
        help="Include tool use/result entries",
    )
    parser.add_argument(
        "--exclude-tools",
        action="append",
        default=[],
        metavar="TOOL",
        help='Exclude tool(s) when including tools (example: --exclude-tools "tool:Read")',
    )
    parser.add_argument(
        "--only-tools",
        action="append",
        default=[],
        metavar="TOOL",
        help='Include only specific tool(s) (example: --only-tools "tool:Read")',
    )
    return parser.parse_args()


def normalize_role(raw_role: str | None, fallback: str) -> str:
    role = (raw_role or fallback or "unknown").strip().lower()
    if role == "assistant":
        return "Assistant"
    if role == "user":
        return "User"
    if role == "system":
        return "System"
    return role.capitalize() or "Unknown"


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks = [coerce_text(v) for v in value]
        return "\n".join(chunk for chunk in chunks if chunk.strip())
    if isinstance(value, dict):
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        if "content" in value:
            return coerce_text(value["content"])
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def normalize_tool_name(name: str) -> str:
    normalized = name.strip()
    if normalized.lower().startswith("tool:"):
        normalized = normalized[5:]
    return normalized


def extract_body(
    content: Any,
    include_thinking: bool,
    include_tools: bool,
    only_tools: set[str],
    excluded_tools: set[str],
    globally_excluded_tool_use_ids: set[str],
    globally_included_tool_use_ids: set[str],
) -> str:
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return coerce_text(content).strip()

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            text = coerce_text(item).strip()
            if text:
                parts.append(text)
            continue

        item_type = item.get("type")
        if item_type == "text":
            text = coerce_text(item.get("text")).strip()
            if text:
                parts.append(text)
            continue

        if item_type == "thinking":
            if include_thinking:
                thinking = coerce_text(item.get("thinking")).strip()
                if thinking:
                    parts.append(f"```thinking\n{thinking}\n```")
            continue

        if item_type == "tool_use":
            if include_tools:
                raw_name = str(item.get("name", "unknown_tool"))
                name = normalize_tool_name(raw_name)
                tool_use_id = item.get("id")
                if only_tools and name not in only_tools:
                    if isinstance(tool_use_id, str) and tool_use_id:
                        globally_excluded_tool_use_ids.add(tool_use_id)
                    continue
                if name in excluded_tools:
                    if isinstance(tool_use_id, str) and tool_use_id:
                        globally_excluded_tool_use_ids.add(tool_use_id)
                    continue

                if isinstance(tool_use_id, str) and tool_use_id:
                    globally_included_tool_use_ids.add(tool_use_id)
                payload = item.get("input")
                rendered = json.dumps(payload, ensure_ascii=False, indent=2)
                parts.append(f"```tool:{name}\n{rendered}\n```")
            continue

        if item_type == "tool_result":
            if include_tools:
                tool_use_id = item.get("tool_use_id")
                if (
                    isinstance(tool_use_id, str)
                    and tool_use_id in globally_excluded_tool_use_ids
                ):
                    continue
                if only_tools and (
                    not isinstance(tool_use_id, str)
                    or tool_use_id not in globally_included_tool_use_ids
                ):
                    continue
                result = coerce_text(item.get("content")).strip()
                if result:
                    parts.append(f"```tool_result\n{result}\n```")
            continue

        text = coerce_text(item).strip()
        if text:
            parts.append(text)

    return "\n\n".join(parts).strip()


def iter_turns(
    input_path: Path,
    include_thinking: bool,
    include_tools: bool,
    only_tools: set[str],
    excluded_tools: set[str],
) -> ParseResult:
    turns: list[Turn] = []
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    session_ids: set[str] = set()
    models: set[str] = set()
    versions: set[str] = set()
    cwd_values: set[str] = set()
    branches: set[str] = set()
    role_counts: dict[str, int] = {}
    usage_counts: dict[str, int] = {}
    usage_records = 0
    globally_excluded_tool_use_ids: set[str] = set()
    globally_included_tool_use_ids: set[str] = set()

    def add_usage(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                add_usage(next_prefix, nested)
            return
        if isinstance(value, bool):
            return
        if isinstance(value, int):
            usage_counts[prefix] = usage_counts.get(prefix, 0) + value

    with input_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            raw = line.strip()
            if not raw:
                continue

            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(
                    f"Skipping invalid JSON line {line_no}: {exc}",
                    file=sys.stderr,
                )
                continue

            event_timestamp = event.get("timestamp")
            if isinstance(event_timestamp, str):
                if first_timestamp is None or event_timestamp < first_timestamp:
                    first_timestamp = event_timestamp
                if last_timestamp is None or event_timestamp > last_timestamp:
                    last_timestamp = event_timestamp

            session_id = event.get("sessionId")
            if isinstance(session_id, str) and session_id:
                session_ids.add(session_id)
            version = event.get("version")
            if isinstance(version, str) and version:
                versions.add(version)
            cwd = event.get("cwd")
            if isinstance(cwd, str) and cwd:
                cwd_values.add(cwd)
            branch = event.get("gitBranch")
            if isinstance(branch, str) and branch:
                branches.add(branch)

            event_type = event.get("type")
            if event_type not in {"user", "assistant"}:
                continue

            message = event.get("message")
            if not isinstance(message, dict):
                continue

            model = message.get("model")
            if isinstance(model, str) and model:
                models.add(model)
            usage = message.get("usage")
            if isinstance(usage, dict):
                usage_records += 1
                add_usage("", usage)

            role = normalize_role(message.get("role"), event_type)
            body = extract_body(
                message.get("content"),
                include_thinking=include_thinking,
                include_tools=include_tools,
                only_tools=only_tools,
                excluded_tools=excluded_tools,
                globally_excluded_tool_use_ids=globally_excluded_tool_use_ids,
                globally_included_tool_use_ids=globally_included_tool_use_ids,
            )
            if not body:
                continue

            role_counts[role] = role_counts.get(role, 0) + 1
            timestamp = event.get("timestamp") or message.get("timestamp")
            turns.append(
                Turn(index=len(turns) + 1, role=role, timestamp=timestamp, body=body)
            )

    return ParseResult(
        turns=turns,
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        session_ids=session_ids,
        models=models,
        versions=versions,
        cwd_values=cwd_values,
        branches=branches,
        role_counts=role_counts,
        usage_counts=usage_counts,
        usage_records=usage_records,
    )


def quote_yaml(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_markdown(source: Path, result: ParseResult) -> str:
    lines: list[str] = []
    turns = result.turns

    lines.append("---")
    lines.append(f"source: {quote_yaml(str(source))}")
    lines.append(f"messages: {len(turns)}")
    if result.first_timestamp:
        lines.append(f"first_timestamp: {quote_yaml(result.first_timestamp)}")
    if result.last_timestamp:
        lines.append(f"last_timestamp: {quote_yaml(result.last_timestamp)}")

    if result.session_ids:
        lines.append("session_ids:")
        for session_id in sorted(result.session_ids):
            lines.append(f"  - {quote_yaml(session_id)}")
    if result.models:
        lines.append("models:")
        for model in sorted(result.models):
            lines.append(f"  - {quote_yaml(model)}")
    if result.versions:
        lines.append("versions:")
        for version in sorted(result.versions):
            lines.append(f"  - {quote_yaml(version)}")
    if result.cwd_values:
        lines.append("cwd:")
        for cwd in sorted(result.cwd_values):
            lines.append(f"  - {quote_yaml(cwd)}")
    if result.branches:
        lines.append("git_branches:")
        for branch in sorted(result.branches):
            lines.append(f"  - {quote_yaml(branch)}")

    lines.append("role_counts:")
    for role in sorted(result.role_counts):
        lines.append(f"  {role}: {result.role_counts[role]}")

    if result.usage_counts or result.usage_records:
        lines.append("usage:")
        lines.append(f"  records: {result.usage_records}")
        for key in sorted(result.usage_counts):
            lines.append(f"  {key}: {result.usage_counts[key]}")
    lines.append("---")
    lines.append("")

    lines.append("# Conversation")
    lines.append("")
    lines.append(f"- Source: `{source}`")
    lines.append(f"- Messages: {len(turns)}")
    lines.append("")

    for turn in turns:
        title = f"## {turn.index}. {turn.role}"
        if turn.timestamp:
            title += f" ({turn.timestamp})"
        lines.append(title)
        lines.append("")
        lines.append(turn.body)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    excluded_tools = {
        normalize_tool_name(tool_name)
        for tool_name in args.exclude_tools
        if normalize_tool_name(tool_name)
    }
    only_tools = {
        normalize_tool_name(tool_name)
        for tool_name in args.only_tools
        if normalize_tool_name(tool_name)
    }
    include_tools = args.include_tools or bool(excluded_tools) or bool(only_tools)

    result = iter_turns(
        input_path,
        include_thinking=args.include_thinking,
        include_tools=include_tools,
        only_tools=only_tools,
        excluded_tools=excluded_tools,
    )
    markdown = render_markdown(input_path, result)

    if args.output:
        output_path = args.output.expanduser()
        output_path.write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
