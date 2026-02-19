from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
TEMPLATES_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"

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


def main() -> None:
  uvicorn.run("serve:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
  main()
