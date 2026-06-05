#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))


QUEUE_BASE = "https://queue.fal.run"
MODEL_ALIASES = {
    "seedance-2.0": "bytedance/seedance-2.0/text-to-video",
    "seedance-2.0-text-to-video": "bytedance/seedance-2.0/text-to-video",
    "bytedance/seedance-2.0": "bytedance/seedance-2.0/text-to-video",
    "seedance-2.0-fast": "bytedance/seedance-2.0/fast/text-to-video",
    "seedance-2.0-fast-text-to-video": "bytedance/seedance-2.0/fast/text-to-video",
}


class FALVideoGenerationError(RuntimeError):
    pass


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


def normalize_model(model: str) -> str:
    cleaned = (model or "seedance-2.0").strip()
    return MODEL_ALIASES.get(cleaned, cleaned)


def duration_value(duration: int | float | str) -> str:
    if isinstance(duration, str):
        raw = duration.strip()
        return raw if raw else "auto"
    value = int(round(float(duration)))
    if value < 4:
        value = 4
    if value > 15:
        value = 15
    return str(value)


def extract_video_url(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("video"),
        payload.get("output"),
        payload.get("file"),
        payload.get("result"),
    ]
    for item in candidates:
        if isinstance(item, str) and item.startswith("http"):
            return item
        if isinstance(item, dict):
            url = item.get("url") or item.get("download_url")
            if isinstance(url, str) and url.startswith("http"):
                return url
    data = payload.get("data")
    if isinstance(data, dict):
        return extract_video_url(data)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                url = extract_video_url(item)
                if url:
                    return url
    return ""


class FALQueueVideoProvider:
    def __init__(self, api_key: str | None = None, *, timeout: int = 240, poll_interval: float = 5.0, max_wait: int = 900) -> None:
        load_default_env()
        self.api_key = (api_key or os.environ.get("FAL_KEY") or "").strip()
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_wait = max_wait
        if not self.api_key or self.api_key == "your_fal_api_key_here":
            raise FALVideoGenerationError("FAL_KEY is not configured.")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate(
        self,
        *,
        prompt: str,
        model: str,
        duration: int | float | str,
        aspect_ratio: str,
        resolution: str,
        negative_prompt: str = "",
        audio: bool = False,
        seed: int | None = None,
    ) -> dict[str, Any]:
        endpoint = normalize_model(model)
        full_prompt = prompt
        if negative_prompt:
            full_prompt = f"{prompt} Avoid: {negative_prompt}"
        arguments: dict[str, Any] = {
            "prompt": full_prompt,
            "resolution": resolution,
            "duration": duration_value(duration),
            "aspect_ratio": aspect_ratio,
            "generate_audio": bool(audio),
        }
        if seed is not None:
            arguments["seed"] = int(seed)

        try:
            import requests
        except Exception as exc:
            raise FALVideoGenerationError(f"requests is not importable in this Python environment: {exc}") from exc

        submit = requests.post(
            f"{QUEUE_BASE}/{endpoint}",
            headers=self.headers,
            data=json.dumps(arguments),
            timeout=self.timeout,
        )
        if submit.status_code >= 400:
            raise FALVideoGenerationError(f"FAL submit error {submit.status_code}: {submit.text[:1200]}")
        submitted = submit.json()
        status_url = submitted.get("status_url")
        response_url = submitted.get("response_url")
        request_id = submitted.get("request_id", "")
        if not status_url or not response_url:
            raise FALVideoGenerationError(f"FAL submit response missing status_url/response_url: {submitted}")

        started = time.time()
        status_payload: dict[str, Any] = {}
        while time.time() - started <= self.max_wait:
            status_response = requests.get(f"{status_url}?logs=1", headers=self.headers, timeout=self.timeout)
            if status_response.status_code >= 400:
                raise FALVideoGenerationError(f"FAL status error {status_response.status_code}: {status_response.text[:1200]}")
            status_payload = status_response.json()
            status = status_payload.get("status")
            if status == "COMPLETED":
                break
            if status in {"FAILED", "ERROR"}:
                raise FALVideoGenerationError(f"FAL generation failed: {status_payload}")
            print(f"fal status {status or 'UNKNOWN'} request_id={request_id}", flush=True)
            time.sleep(self.poll_interval)
        else:
            raise FALVideoGenerationError(f"FAL generation timed out after {self.max_wait}s: request_id={request_id}")

        result_response = requests.get(response_url, headers=self.headers, timeout=self.timeout)
        if result_response.status_code >= 400:
            raise FALVideoGenerationError(f"FAL result error {result_response.status_code}: {result_response.text[:1200]}")
        result = result_response.json()
        video_url = extract_video_url(result)
        if not video_url:
            raise FALVideoGenerationError(f"FAL result did not include a video URL: {result}")
        return {
            "success": True,
            "video": video_url,
            "request_id": request_id,
            "endpoint": endpoint,
            "arguments": arguments,
            "status": status_payload,
            "result": result,
        }
