#!/usr/bin/env python3
"""Generate a webcomic image from git diff/log text piped via stdin."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "google/gemini-3-pro-image-preview"
DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_LOG_DIR = ".devnotes/webcomic-runs"
MAX_PROMPT_CHARS = 100_000
DEFAULT_PROMPT_PREFIX = (
    "Create a webcomic that explains the new feature as clearly and entertainingly as possible."
)
DEFAULT_TITLE_SLUG = "webcomic"


@dataclass(frozen=True)
class RunConfig:
    model: str
    aspect_ratio: str
    prompt: str
    stdin_text: str
    output: Path | None
    run_date: str
    title: str | None
    log_dir: Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model.")
    parser.add_argument(
        "--aspect-ratio",
        default=DEFAULT_ASPECT_RATIO,
        help="Image aspect ratio.",
    )
    parser.add_argument(
        "--additional-prompt",
        default="",
        help="Additional prompt instructions appended to the base prompt.",
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Date used for automatic image naming (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Title text used for automatic image naming (slugified).",
    )
    parser.add_argument(
        "--output",
        default="",
        help=(
            "Explicit output image path. When omitted, saves to "
            "images/{date}-{title-or-webcomic}.<ext>."
        ),
    )
    parser.add_argument(
        "--log-dir",
        default=DEFAULT_LOG_DIR,
        help="Directory where per-run prompt/request/response logs are written.",
    )
    return parser.parse_args(argv)


def validate_date(value: str) -> str:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid --date value {value!r}; expected YYYY-MM-DD.") from exc
    return value


def build_prompt(stdin_text: str, additional_prompt: str) -> str:
    prompt = f"{DEFAULT_PROMPT_PREFIX}\n\n{stdin_text.strip()}"
    extra = additional_prompt.strip()
    if not extra:
        return prompt
    return f"{prompt}\n\nAdditional instructions:\n{extra}"


def ensure_prompt_limit(prompt: str) -> None:
    if len(prompt) > MAX_PROMPT_CHARS:
        raise RuntimeError(
            f"Prompt too long ({len(prompt)} chars). Max allowed is {MAX_PROMPT_CHARS}."
        )


def parse_data_url(image_url: str) -> tuple[str, str]:
    if not image_url.startswith("data:image") or "," not in image_url:
        raise RuntimeError("Unexpected image URL format.")
    header, b64_data = image_url.split(",", 1)
    if ";base64" not in header:
        raise RuntimeError("Image response is not base64 encoded.")
    mime_type = header[5:].split(";", 1)[0]
    return mime_type, b64_data


def extension_for_mime(mime_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if mime_type not in mapping:
        raise RuntimeError(f"Unsupported image mime type: {mime_type}")
    return mapping[mime_type]


def slugify(text: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower())
    normalized = normalized.strip("-")
    return normalized or DEFAULT_TITLE_SLUG


def resolve_requested_output(output: Path | None, run_date: str, title: str | None) -> Path:
    if output is not None:
        return output
    stem = slugify(title or "")
    return Path("images") / f"{run_date}-{stem}"


def resolve_output_path(base_output: Path, mime_type: str) -> Path:
    expected_suffix = extension_for_mime(mime_type)
    current_suffix = base_output.suffix.lower()
    if not current_suffix:
        return base_output.with_suffix(expected_suffix)
    if current_suffix != expected_suffix:
        return base_output.with_suffix(expected_suffix)
    return base_output


def build_payload(model: str, prompt: str, aspect_ratio: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": aspect_ratio},
    }


def request_image(api_key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.devnotes",
            "X-Title": "Devnotes Webcomic Generator",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def extract_image(response_data: dict) -> tuple[str, bytes]:
    choices = response_data.get("choices") or []
    if not choices:
        raise RuntimeError("No choices in OpenRouter response.")
    message = choices[0].get("message", {})
    images = message.get("images") or []
    if not images:
        raise RuntimeError("No images found in model response.")
    image_url = images[0].get("image_url", {}).get("url", "")
    mime_type, b64_data = parse_data_url(image_url)
    return mime_type, base64.b64decode(b64_data)


def extract_caption(response_data: dict) -> str:
    choices = response_data.get("choices") or []
    if not choices:
        return ""
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str):
        return ""
    return content.strip()


def create_run_dir(base_dir: Path, title: str | None) -> Path:
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    suffix = slugify(title or "")
    run_dir = base_dir / f"{stamp}-{suffix}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def save_run_artifacts(
    run_dir: Path,
    *,
    prompt: str,
    payload: dict,
    response_data: dict | None,
    meta: dict,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(run_dir / "request.json", payload)
    if response_data is not None:
        write_json(run_dir / "response.json", response_data)
    write_json(run_dir / "meta.json", meta)


def run(config: RunConfig, api_key: str) -> tuple[Path, str, str]:
    ensure_prompt_limit(config.prompt)
    payload = build_payload(model=config.model, prompt=config.prompt, aspect_ratio=config.aspect_ratio)
    stdin_hash = hashlib.sha256(config.stdin_text.encode("utf-8")).hexdigest()
    run_dir = create_run_dir(config.log_dir, config.title)

    meta: dict[str, str | int] = {
        "status": "started",
        "model": config.model,
        "aspect_ratio": config.aspect_ratio,
        "run_date": config.run_date,
        "title": config.title or "",
        "stdin_char_count": len(config.stdin_text),
        "stdin_sha256": stdin_hash,
    }
    save_run_artifacts(
        run_dir,
        prompt=config.prompt,
        payload=payload,
        response_data=None,
        meta=meta,
    )

    response_data: dict | None = None
    try:
        response_data = request_image(api_key=api_key, payload=payload)
        mime_type, image_bytes = extract_image(response_data)
        base_output = resolve_requested_output(config.output, config.run_date, config.title)
        output_path = resolve_output_path(base_output, mime_type)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        caption = extract_caption(response_data)

        meta.update(
            {
                "status": "success",
                "mime_type": mime_type,
                "output_path": str(output_path),
            }
        )
        save_run_artifacts(
            run_dir,
            prompt=config.prompt,
            payload=payload,
            response_data=response_data,
            meta=meta,
        )
        return output_path, mime_type, caption
    except Exception as exc:  # noqa: BLE001
        meta.update(
            {
                "status": "error",
                "error": str(exc),
            }
        )
        save_run_artifacts(
            run_dir,
            prompt=config.prompt,
            payload=payload,
            response_data=response_data,
            meta=meta,
        )
        raise


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("Missing OPENROUTER_API_KEY in environment.", file=sys.stderr)
        return 1

    stdin_text = sys.stdin.read()
    if not stdin_text.strip():
        print(
            "No input on stdin. Pipe `git show` or `git log -p` into this command.",
            file=sys.stderr,
        )
        return 1

    try:
        run_date = validate_date(args.date)
        prompt = build_prompt(stdin_text=stdin_text, additional_prompt=args.additional_prompt)
        output = Path(args.output) if args.output.strip() else None
        title = args.title.strip() or None
        config = RunConfig(
            model=args.model,
            aspect_ratio=args.aspect_ratio,
            prompt=prompt,
            stdin_text=stdin_text,
            output=output,
            run_date=run_date,
            title=title,
            log_dir=Path(args.log_dir),
        )
        output_path, mime_type, caption = run(config=config, api_key=api_key)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Saved comic image to: {output_path.resolve()}")
    if output and output.suffix.lower() != output_path.suffix.lower():
        print(
            f"Adjusted output extension to match response mime type ({mime_type}).",
            file=sys.stderr,
        )
    if caption:
        print("Model caption:")
        print(caption)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
