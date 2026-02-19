from __future__ import annotations

import re
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
    raise RuntimeError("No templates directory found for devlog-notes")
  return resolved


def _resolve_assets_dir() -> Path:
  resolved = _first_existing([Path.cwd() / "assets", PACKAGE_ASSETS_DIR, REPO_ROOT / "assets"])
  if resolved is None:
    raise RuntimeError("No assets directory found for devlog-notes")
  return resolved


NOTES_DIR = _resolve_notes_dir()
TEMPLATES_DIR = _resolve_templates_dir()
ASSETS_DIR = _resolve_assets_dir()

md = MarkdownIt("commonmark")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app = FastAPI(title="Devlog Notes")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


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


def _read_notes() -> list[Note]:
  notes: list[Note] = []
  if not NOTES_DIR.exists():
    return notes

  for path in sorted(NOTES_DIR.glob("*.md")):
    slug = path.stem
    try:
      parsed_date = date.fromisoformat(slug)
    except ValueError:
      continue

    raw = path.read_text(encoding="utf-8")
    title = _extract_title(raw, slug)
    excerpt = _extract_excerpt(raw)
    html = md.render(raw)
    notes.append(Note(slug=slug, note_date=parsed_date, title=title, excerpt=excerpt, html=html))

  notes.sort(key=lambda note: note.note_date, reverse=True)
  return notes


def _find_note_or_404(slug: str) -> Note:
  notes = _read_notes()
  for note in notes:
    if note.slug == slug:
      return note
  raise HTTPException(status_code=404, detail="Note not found")


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
  notes = _read_notes()
  return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={"notes": notes[:5]},
  )


@app.get("/archive/", response_class=HTMLResponse)
def archive(request: Request) -> HTMLResponse:
  return templates.TemplateResponse(
    request=request,
    name="archive.html",
    context={"notes": _read_notes()},
  )


@app.get("/notes/{slug}/", response_class=HTMLResponse)
def note_detail(slug: str, request: Request) -> HTMLResponse:
  return templates.TemplateResponse(
    request=request,
    name="note.html",
    context={"note": _find_note_or_404(slug)},
  )


def _env_flag(name: str, default: bool = False) -> bool:
  value = os.getenv(name)
  if value is None:
    return default
  return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
  uvicorn.run(
    "devlog_notes.serve:app",
    host="127.0.0.1",
    port=8000,
    reload=_env_flag("DEVLOG_NOTES_RELOAD", default=False),
  )


if __name__ == "__main__":
  main()
