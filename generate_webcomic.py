#!/usr/bin/env python3
"""Generate a webcomic image from git diff/log text piped via stdin."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "google/gemini-3-pro-image-preview"
DEFAULT_OUTPUT = "webcomic_pr48_objective_fix"
PROMPT_PREFIX = "Create a webcomic that explains the new feature as clearly and entertainingly as possible"


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_prompt(stdin_text: str) -> str:
    return f"{PROMPT_PREFIX}\n\n{stdin_text}"


def parse_data_url(image_url: str) -> tuple[str, str]:
    if not image_url.startswith("data:image") or "," not in image_url:
        raise RuntimeError("Unexpected image URL format")
    header, b64_data = image_url.split(",", 1)
    if ";base64" not in header:
        raise RuntimeError("Image response is not base64 encoded")
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


def resolve_output_path(base_output: Path, mime_type: str) -> Path:
    expected_suffix = extension_for_mime(mime_type)
    current_suffix = base_output.suffix.lower()
    if not current_suffix:
        return base_output.with_suffix(expected_suffix)
    if current_suffix != expected_suffix:
        return base_output.with_suffix(expected_suffix)
    return base_output


def request_image(api_key: str, model: str, prompt: str, aspect_ratio: str) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": aspect_ratio},
    }

    body = json.dumps(payload).encode("utf-8")
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.devlog",
            "X-Title": "Git Patch Webcomic Generator",
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


def extract_and_save_image(response_data: dict, requested_output_path: Path) -> tuple[Path, str]:
    choices = response_data.get("choices") or []
    if not choices:
        raise RuntimeError("No choices in OpenRouter response")

    message = choices[0].get("message", {})
    images = message.get("images") or []
    if not images:
        raise RuntimeError("No images found in model response")

    image_url = images[0].get("image_url", {}).get("url", "")
    mime_type, b64_data = parse_data_url(image_url)
    output_path = resolve_output_path(requested_output_path, mime_type)
    image_bytes = base64.b64decode(b64_data)
    output_path.write_bytes(image_bytes)
    return output_path, mime_type


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output image path")
    parser.add_argument("--aspect-ratio", default="16:9", help="Image aspect ratio")
    parser.add_argument("--save-prompt", default="webcomic_prompt.txt", help="Where to save the full prompt")
    parser.add_argument("--save-response", default="webcomic_response.json", help="Where to save raw API response")
    args = parser.parse_args()

    env_values = load_env_file(Path(".env"))
    api_key = env_values.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Missing OPENROUTER_API_KEY in .env", file=sys.stderr)
        return 1

    stdin_text = sys.stdin.read()
    if not stdin_text.strip():
        print("No input on stdin. Pipe git log -p or git diff output into this script.", file=sys.stderr)
        return 1

    try:
        prompt = build_prompt(stdin_text)
        Path(args.save_prompt).write_text(prompt, encoding="utf-8")

        response_data = request_image(api_key=api_key, model=args.model, prompt=prompt, aspect_ratio=args.aspect_ratio)
        Path(args.save_response).write_text(json.dumps(response_data, indent=2), encoding="utf-8")

        requested_output_path = Path(args.output)
        output_path, mime_type = extract_and_save_image(response_data, requested_output_path)

        text_reply = ""
        choices = response_data.get("choices") or []
        if choices:
            text_reply = (choices[0].get("message") or {}).get("content") or ""

        if requested_output_path.suffix.lower() != output_path.suffix.lower():
            print(
                f"Adjusted output extension to match response mime type ({mime_type}).",
                file=sys.stderr,
            )
        print(f"Saved comic image to: {output_path.resolve()}")
        if text_reply:
            print("Model caption:")
            print(text_reply)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
