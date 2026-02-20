from __future__ import annotations

import re
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_TEMPLATES_DIR = PACKAGE_DIR / "templates"
PACKAGE_ASSETS_DIR = PACKAGE_DIR / "assets"


def _first_existing(candidates: Iterable[Path]) -> Path | None:
  for candidate in candidates:
    if candidate.exists():
      return candidate
  return None


def _resolve_notes_dir() -> Path:
  cwd = Path.cwd()
  if (cwd / "notes").is_dir():
    return cwd / "notes"
  if any(cwd.glob("*.md")):
    return cwd
  if (REPO_ROOT / "notes").is_dir():
    return REPO_ROOT / "notes"
  return cwd / "notes"


def _resolve_templates_dir() -> Path:
  resolved = _first_existing([Path.cwd() / "templates", PACKAGE_TEMPLATES_DIR, REPO_ROOT / "templates"])
  if resolved is None:
    raise RuntimeError("No templates directory found for devnotes")
  return resolved


def _resolve_assets_dir() -> Path:
  resolved = _first_existing([Path.cwd() / "assets", PACKAGE_ASSETS_DIR, REPO_ROOT / "assets"])
  if resolved is None:
    raise RuntimeError("No assets directory found for devnotes")
  return resolved


NOTES_DIR = _resolve_notes_dir()
TEMPLATES_DIR = _resolve_templates_dir()
SOURCE_ASSETS_DIR = _resolve_assets_dir()
SITE_DIR = Path.cwd() / "site"
ASSETS_DIR = SITE_DIR / "assets"


@dataclass
class Note:
  slug: str
  note_date: date
  title: str
  excerpt: str
  html: str


def _extract_title(markdown: str, fallback: str) -> str:
  for line in markdown.splitlines():
    if line.startswith("# "):
      return line[2:].strip() or fallback
  return fallback


def _extract_excerpt(markdown: str) -> str:
  lines = markdown.splitlines()
  chunk: list[str] = []
  for line in lines:
    stripped = line.strip()
    if not stripped:
      if chunk:
        break
      continue
    if stripped.startswith("#"):
      continue
    if stripped.startswith("-"):
      continue
    chunk.append(stripped)
  excerpt = " ".join(chunk)
  excerpt = re.sub(r"`([^`]*)`", r"\1", excerpt)
  excerpt = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", excerpt)
  return excerpt[:220] + ("..." if len(excerpt) > 220 else "")


def _strip_leading_h1(html: str) -> str:
  return re.sub(r"^\s*<h1>.*?</h1>\s*", "", html, count=1, flags=re.IGNORECASE | re.DOTALL)


def _strip_leading_date(html: str, note_date: date) -> str:
  candidates = (
    note_date.isoformat(),
    f"{note_date:%B} {note_date.day}, {note_date:%Y}",
  )
  for token in candidates:
    html = re.sub(
      rf"^\s*<p>\s*(?:<(?:em|strong)>)?\s*(?:date:\s*)?{re.escape(token)}\s*(?:</(?:em|strong)>)?\s*</p>\s*",
      "",
      html,
      count=1,
      flags=re.IGNORECASE,
    )
  return html


def _normalize_note_html(html: str, note_date: date) -> str:
  html = _strip_leading_h1(html)
  html = _strip_leading_date(html, note_date)
  return html


def _read_notes(md: MarkdownIt) -> list[Note]:
  notes: list[Note] = []
  if not NOTES_DIR.exists():
    return notes

  for path in sorted(NOTES_DIR.glob("*.md")):
    slug = path.stem
    try:
      parsed_date = date.fromisoformat(slug)
    except ValueError:
      print(f"Skipping {path.name}: expected YYYY-MM-DD.md")
      continue

    raw = path.read_text(encoding="utf-8")
    title = _extract_title(raw, slug)
    excerpt = _extract_excerpt(raw)
    html = _normalize_note_html(md.render(raw), parsed_date)
    notes.append(Note(slug=slug, note_date=parsed_date, title=title, excerpt=excerpt, html=html))

  notes.sort(key=lambda note: note.note_date, reverse=True)
  return notes


def _render_templates(notes: list[Note]) -> None:
  env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
  )

  index_template = env.get_template("index.html")
  archive_template = env.get_template("archive.html")
  note_template = env.get_template("note.html")

  recent = notes[:5]
  (SITE_DIR / "index.html").write_text(index_template.render(notes=recent), encoding="utf-8")

  archive_dir = SITE_DIR / "archive"
  archive_dir.mkdir(parents=True, exist_ok=True)
  (archive_dir / "index.html").write_text(archive_template.render(notes=notes), encoding="utf-8")

  notes_root = SITE_DIR / "notes"
  for note in notes:
    note_dir = notes_root / note.slug
    note_dir.mkdir(parents=True, exist_ok=True)
    (note_dir / "index.html").write_text(note_template.render(note=note), encoding="utf-8")


def _write_assets() -> None:
  ASSETS_DIR.mkdir(parents=True, exist_ok=True)
  for path in SOURCE_ASSETS_DIR.iterdir():
    if path.is_file():
      shutil.copy2(path, ASSETS_DIR / path.name)


def main() -> int:
  md = MarkdownIt("commonmark")

  if SITE_DIR.exists():
    shutil.rmtree(SITE_DIR)
  SITE_DIR.mkdir(parents=True, exist_ok=True)

  notes = _read_notes(md)
  _render_templates(notes)
  _write_assets()

  print(f"Built {len(notes)} notes into {SITE_DIR}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
