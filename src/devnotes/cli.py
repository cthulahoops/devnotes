from __future__ import annotations

from pathlib import Path

import click

from . import build_notes_site, list_sessions, serve, transcript_to_markdown


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Devnotes command line tools."""


@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option(
    "--reload/--no-reload",
    default=None,
    help="Enable autoreload. If omitted, DEVNOTES_RELOAD controls behavior.",
)
def serve_command(host: str, port: int, reload: bool | None) -> None:
    serve.serve(host=host, port=port, reload=reload)


@cli.command("build-site")
def build_site_command() -> None:
    code = build_notes_site.main()
    if code:
        raise click.exceptions.Exit(code)


@cli.command("list-sessions")
@click.argument("date")
@click.option(
    "--match",
    default="",
    show_default=True,
    help="Filter project directory names by substring.",
)
@click.option(
    "--exclude",
    default="",
    show_default=True,
    help="Exclude project directory names by substring.",
)
@click.option(
    "--projects-root",
    default="~/.claude/projects",
    show_default=True,
    help="Base Claude projects directory.",
)
@click.option(
    "--codex-sessions-root",
    default="~/.codex/sessions",
    show_default=True,
    help="Base Codex sessions directory.",
)
@click.option(
    "--include-agent",
    is_flag=True,
    help="Include agent-*.jsonl session files.",
)
def list_sessions_command(
    date: str,
    match: str,
    exclude: str,
    projects_root: str,
    codex_sessions_root: str,
    include_agent: bool,
) -> None:
    code = list_sessions.run(
        date=date,
        match=match,
        exclude=exclude,
        projects_root=projects_root,
        codex_sessions_root=codex_sessions_root,
        include_agent=include_agent,
    )
    if code:
        raise click.exceptions.Exit(code)


@cli.command("transcript-to-markdown")
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    help="Output markdown file path (defaults to stdout).",
)
@click.option(
    "--include-thinking",
    is_flag=True,
    help="Include hidden thinking blocks when present.",
)
@click.option(
    "--include-tools",
    is_flag=True,
    help="Include tool use/result entries.",
)
@click.option(
    "--exclude-tools",
    multiple=True,
    metavar="TOOL",
    help='Exclude tool(s) when including tools (example: --exclude-tools "tool:Read").',
)
@click.option(
    "--only-tools",
    multiple=True,
    metavar="TOOL",
    help='Include only specific tool(s) (example: --only-tools "tool:Read").',
)
def transcript_to_markdown_command(
    input: Path,
    output: Path | None,
    include_thinking: bool,
    include_tools: bool,
    exclude_tools: tuple[str, ...],
    only_tools: tuple[str, ...],
) -> None:
    args: list[str] = [str(input)]
    if output:
        args.extend(["-o", str(output)])
    if include_thinking:
        args.append("--include-thinking")
    if include_tools:
        args.append("--include-tools")
    for tool_name in exclude_tools:
        args.extend(["--exclude-tools", tool_name])
    for tool_name in only_tools:
        args.extend(["--only-tools", tool_name])

    code = transcript_to_markdown.main(args)
    if code:
        raise click.exceptions.Exit(code)


def main() -> None:
    cli()

