from __future__ import annotations

import base64
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devnotes import generate_webcomic


class GenerateWebcomicTests(unittest.TestCase):
    def test_build_prompt_with_additional_instructions(self) -> None:
        prompt = generate_webcomic.build_prompt("diff --git a b", "depict the developer as a lizard")
        self.assertIn("Create a webcomic", prompt)
        self.assertIn("diff --git a b", prompt)
        self.assertIn("Additional instructions:", prompt)
        self.assertIn("depict the developer as a lizard", prompt)

    def test_resolve_requested_output_defaults_to_images_date_slug(self) -> None:
        path = generate_webcomic.resolve_requested_output(None, "2026-02-23", "My Cool Fix")
        self.assertEqual(path, Path("images/2026-02-23-my-cool-fix"))

    def test_resolve_requested_output_uses_fallback_slug(self) -> None:
        path = generate_webcomic.resolve_requested_output(None, "2026-02-23", None)
        self.assertEqual(path, Path("images/2026-02-23-webcomic"))

    def test_resolve_output_path_sets_suffix_for_mime(self) -> None:
        output = generate_webcomic.resolve_output_path(Path("images/2026-02-23-fix"), "image/png")
        self.assertEqual(output.suffix, ".png")

    def test_extract_image_errors_without_images(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "No images found"):
            generate_webcomic.extract_image({"choices": [{"message": {}}]})

    def test_main_requires_api_key_in_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                code = generate_webcomic.main([])
        self.assertEqual(code, 1)
        self.assertIn("Missing OPENROUTER_API_KEY in environment.", stderr.getvalue())

    def test_run_writes_image_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            cwd = Path(tempdir)
            response_data = {
                "choices": [
                    {
                        "message": {
                            "content": "comic caption",
                            "images": [
                                {
                                    "image_url": {
                                        "url": "data:image/png;base64,"
                                        + base64.b64encode(b"pngdata").decode("ascii")
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
            config = generate_webcomic.RunConfig(
                model="model-x",
                aspect_ratio="16:9",
                prompt="prompt text",
                stdin_text="git show output",
                output=cwd / "images" / "comic",
                run_date="2026-02-23",
                title="Interesting Change",
                log_dir=cwd / ".devnotes" / "webcomic-runs",
            )

            with patch("devnotes.generate_webcomic.request_image", return_value=response_data):
                output_path, mime_type, caption = generate_webcomic.run(config=config, api_key="token")

            self.assertEqual(mime_type, "image/png")
            self.assertEqual(caption, "comic caption")
            self.assertEqual(output_path.suffix, ".png")
            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"pngdata")

            run_dirs = [p for p in config.log_dir.iterdir() if p.is_dir()]
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]
            self.assertTrue((run_dir / "prompt.txt").exists())
            self.assertTrue((run_dir / "request.json").exists())
            self.assertTrue((run_dir / "response.json").exists())
            self.assertTrue((run_dir / "meta.json").exists())


if __name__ == "__main__":
    unittest.main()
