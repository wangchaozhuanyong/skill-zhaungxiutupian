#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))

import requests


from scripts.fal_video_provider import FALQueueVideoProvider, FALVideoGenerationError, load_default_env


NEGATIVE_PROMPT = (
    "hard cuts, multiple shots, scene change, different room, different house, "
    "inconsistent TV wall, inconsistent sofa, inconsistent dining table, changing floor material, "
    "changing cabinet color, warped cabinet lines, distorted perspective, cartoon, CGI look, "
    "low quality, blurry, text, logo, watermark, people, shaky camera, fast camera movement"
)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def style_bible(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("style_bible")
    if isinstance(raw, dict):
        return raw
    return {
        "project_theme": config.get("style", "Italian light luxury open-plan living and dining room"),
        "floor_plan_assumption": "One continuous living-dining room with entry cabinet, TV wall, sofa, dining table, sideboard and window.",
        "fixed_furniture_layout": "TV wall on one long side, sofa opposite TV wall, dining table behind sofa, sideboard beside dining area.",
        "fixed_tv_wall": "Warm grey stone TV wall with deep grey integrated custom cabinets and hidden LED strips.",
        "fixed_sofa": "Low taupe sofa parallel to the TV wall.",
        "fixed_dining_table": "Dark rectangular dining table behind the sofa.",
        "fixed_floor_material": "Glossy warm grey large-format stone tile.",
        "fixed_cabinet_material": "Deep grey matte cabinet doors, warm wood veneer accents, champagne metal detail.",
        "fixed_light_temperature": "Warm 3000K hidden LED and soft daylight.",
        "fixed_camera_path": "Low gimbal camera enters from entry cabinet, slides through the living-dining room, and settles on the TV wall wide shot.",
        "negative_prompt": NEGATIVE_PROMPT,
    }


def style_bible_text(bible: dict[str, Any]) -> str:
    locked = bible.get("locked_visual_elements", [])
    locked_text = ", ".join(str(item) for item in locked) if isinstance(locked, list) else str(locked)
    return (
        "Single continuous shot, one continuous camera movement, no hard cuts. "
        "Same living-dining room from beginning to end. "
        f"Project theme: {bible.get('project_theme')}. "
        f"Floor plan: {bible.get('floor_plan_assumption')}. "
        f"Furniture layout: {bible.get('fixed_furniture_layout')}. "
        f"Same TV wall: {bible.get('fixed_tv_wall')}. "
        f"Same sofa: {bible.get('fixed_sofa')}. "
        f"Same dining table: {bible.get('fixed_dining_table')}. "
        f"Same floor material: {bible.get('fixed_floor_material')}. "
        f"Same cabinet color and material: {bible.get('fixed_cabinet_material')}. "
        f"Same warm LED lighting: {bible.get('fixed_light_temperature')}. "
        f"Camera path: {bible.get('fixed_camera_path')}. "
        f"Locked visual elements: {locked_text}. "
        "Slow stable gimbal movement, vertical 9:16, low saturation luxury interior color, no text, no watermark."
    )


def download_video(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=240) as response:
        response.raise_for_status()
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def write_failure(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate one continuous AI walkthrough video via FAL.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    parser.add_argument("--model", default="", help="FAL video model family")
    parser.add_argument("--resolution", default="720p", choices=["480p", "540p", "720p", "1080p"])
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    backend = (config.get("generation_backends") or {}).get("continuous_ai_video", {})
    model = args.model or str(backend.get("model", "seedance-2.0"))
    duration = int(backend.get("max_duration") or config.get("duration") or 10)
    out_dir = ROOT / "assets" / "generated" / project_id / "continuous_ai_video"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{output_name}_continuous_ai.mp4"
    result_path = out_dir / "generation_result.json"

    load_default_env()
    try:
        provider = FALQueueVideoProvider()
    except FALVideoGenerationError as exc:
        write_failure(
            result_path,
            {
                "status": "GENERATOR_NOT_READY",
                "backend": "continuous_ai_video",
                "provider": "fal",
                "model": model,
                "error": str(exc),
            },
        )
        print(f"GENERATOR_NOT_READY: continuous_ai_video {exc}")
        return 2

    bible = style_bible(config)
    prompt = style_bible_text(bible)
    try:
        generated = provider.generate(
            prompt=prompt,
            model=model,
            duration=duration,
            aspect_ratio="9:16",
            resolution=args.resolution,
            negative_prompt=str(bible.get("negative_prompt", NEGATIVE_PROMPT)),
            audio=False,
        )
    except Exception as exc:
        write_failure(
            result_path,
            {
                "status": "GENERATION_FAILED",
                "backend": "continuous_ai_video",
                "provider": "fal",
                "model": model,
                "error": str(exc),
            },
        )
        print(f"GENERATION_FAILED: {exc}")
        return 4
    video_url = generated.get("video")
    if not video_url:
        write_failure(
            result_path,
            {
                "status": "GENERATION_FAILED",
                "backend": "continuous_ai_video",
                "provider": "fal",
                "model": model,
                "error": "provider returned no video URL",
            },
        )
        print("GENERATION_FAILED: provider returned no video URL")
        return 5
    download_video(str(video_url), out)
    result_path.write_text(
        json.dumps(
            {
                "status": "READY",
                "generated_source_type": "continuous_ai_video",
                "generated_capability_level": "L3",
                "source_video": str(out),
                "asset_origin": "auto_generated",
                "provider": "fal",
                "model": model,
                "duration": duration,
                "note": "单条连续 AI video 只能进入 L3 候选；L4 仍需连续性报告、视觉证据、专项评分和人工复核。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(out)
    print(result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
