#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import requests

OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def load_default_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(REPO / ".env")
    load_dotenv(Path.home() / ".hermes" / ".env")


class ImageGenerationError(RuntimeError):
    pass


class OpenAIImageProvider:
    def __init__(self, api_key: str | None = None, *, timeout: int = 240) -> None:
        load_default_env()
        self.api_key = (api_key or os.environ.get("OPENAI_API_KEY") or "").strip()
        self.timeout = timeout
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ImageGenerationError("OPENAI_API_KEY is not configured.")

    def generate(
        self,
        *,
        prompt: str,
        output_path: Path,
        model: str,
        size: str,
        quality: str,
        background: str = "opaque",
        output_format: str = "png",
    ) -> dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "n": 1,
            "background": background,
            "output_format": output_format,
        }
        response = requests.post(
            OPENAI_IMAGE_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise ImageGenerationError(f"OpenAI image API error {response.status_code}: {response.text[:1000]}")
        data = response.json()
        items = data.get("data") or []
        if not items:
            raise ImageGenerationError("OpenAI image API returned no image data.")
        item = items[0]
        if item.get("b64_json"):
            output_path.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            image_response = requests.get(item["url"], timeout=self.timeout)
            image_response.raise_for_status()
            output_path.write_bytes(image_response.content)
        else:
            raise ImageGenerationError("OpenAI image API returned no b64_json or url.")
        return {
            "model": model,
            "size": size,
            "quality": quality,
            "background": background,
            "output_format": output_format,
            "output_path": str(output_path),
            "revised_prompt": item.get("revised_prompt", ""),
            "usage": data.get("usage", {}),
        }
