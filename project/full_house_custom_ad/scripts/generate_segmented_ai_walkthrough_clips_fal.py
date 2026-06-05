#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
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


DEFAULT_CLIP_DIR = ROOT / "ai_clips" / "segmented_ai_walkthrough_19s"
ASSEMBLER = ROOT / "scripts" / "assemble_segmented_ai_walkthrough_clips.py"
NEGATIVE_PROMPT = (
    "cartoon, animation, CGI look, low quality, blurry, distorted room, "
    "distorted wide angle, warped cabinet lines, messy clutter, harsh lighting, "
    "over saturated colors, cheap decoration, red yellow promotional text, "
    "subtitles, logo, watermark, people, shaky handheld camera, fast cuts, "
    "flicker, unrealistic furniture, inconsistent floor, inconsistent cabinet, "
    "different house, different room, changing furniture layout"
)

DEFAULT_STYLE_BIBLE = {
    "project_theme": "145㎡ Italian light luxury open-plan living and dining room",
    "floor_plan_assumption": "One continuous large horizontal living-dining space with entry cabinet, TV wall, sofa, dining table, sideboard and floor-to-ceiling window.",
    "fixed_furniture_layout": "TV wall on one long side, sofa opposite TV wall, dining table behind sofa, sideboard beside dining area, entry cabinet on the entrance side.",
    "fixed_tv_wall": "Warm grey stone TV wall with integrated dark grey custom cabinets and hidden LED strips.",
    "fixed_sofa": "Low modern taupe sofa, aligned parallel to the TV wall.",
    "fixed_dining_table": "Rectangular dining table with slim dark chairs, located between living room and sideboard.",
    "fixed_floor_material": "Glossy warm grey large-format stone tile with clean reflections.",
    "fixed_cabinet_material": "Deep grey matte cabinet doors, warm wood veneer accents, champagne metal detail.",
    "fixed_light_temperature": "Warm 3000K hidden LED and soft daylight, low saturation, clean shadows.",
    "fixed_camera_path": "Low gimbal camera enters from entry cabinet, opens to living room, slides across dining area, then closes on cabinet material detail.",
    "locked_visual_elements": [
        "same TV wall",
        "same sofa",
        "same dining table",
        "same floor reflection",
        "same cabinet color",
        "same warm LED lighting",
    ],
}


@dataclass(frozen=True)
class ClipPrompt:
    filename: str
    duration: int
    label: str
    prompt: str


DEFAULT_CLIPS = [
    ClipPrompt(
        "01_entry_wall_cabinet.mp4",
        4,
        "玄关门墙柜一体入场",
        "Camera begins beside the integrated entry wall cabinet and slowly enters the same open-plan living-dining room.",
    ),
    ClipPrompt(
        "02_living_room_opening.mp4",
        4,
        "客厅空间打开",
        "Camera slowly moves forward into the same living room, revealing the fixed TV wall, sofa and floor-to-ceiling window.",
    ),
    ClipPrompt(
        "03_dining_kitchen_slide.mp4",
        5,
        "餐厨横移漫游",
        "Camera slides laterally from the same sofa area toward the dining table and sideboard, keeping the same floor, cabinet and lighting language.",
    ),
    ClipPrompt(
        "04_bedroom_closet_walk.mp4",
        4,
        "柜体系统近景",
        "Camera glides along a matching tall cabinet system and built-in storage wall, preserving the same warm grey cabinet material and LED lighting.",
    ),
    ClipPrompt(
        "05_material_light_close.mp4",
        5,
        "材质灯光收尾",
        "Slow cinematic close-up along the same wood veneer, stone texture, hidden LED strip and precise cabinet gaps, then settles on a clean cabinet wall.",
    ),
]


def load_config(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_generation_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def style_bible_from_config(config: dict[str, Any]) -> dict[str, Any]:
    bible = dict(DEFAULT_STYLE_BIBLE)
    incoming = config.get("style_bible")
    if isinstance(incoming, dict):
        bible.update(incoming)
    return bible


def style_bible_text(style_bible: dict[str, Any]) -> str:
    locked = style_bible.get("locked_visual_elements", [])
    locked_text = ", ".join(str(item) for item in locked) if isinstance(locked, list) else str(locked)
    return (
        "Style Bible for all clips. Every clip must belong to the same home and same visual system. "
        f"Project theme: {style_bible.get('project_theme')}. "
        f"Floor plan: {style_bible.get('floor_plan_assumption')}. "
        f"Furniture layout: {style_bible.get('fixed_furniture_layout')}. "
        f"TV wall: {style_bible.get('fixed_tv_wall')}. "
        f"Sofa: {style_bible.get('fixed_sofa')}. "
        f"Dining table: {style_bible.get('fixed_dining_table')}. "
        f"Floor material: {style_bible.get('fixed_floor_material')}. "
        f"Cabinet material: {style_bible.get('fixed_cabinet_material')}. "
        f"Light temperature: {style_bible.get('fixed_light_temperature')}. "
        f"Camera path: {style_bible.get('fixed_camera_path')}. "
        f"Locked visual elements: {locked_text}. "
        "Do not change house, layout, floor material, cabinet color, TV wall, sofa, dining table or lighting between clips."
    )


def clips_from_config(config: dict[str, Any]) -> list[ClipPrompt]:
    raw = config.get("clips", config.get("clip_specs"))
    if not isinstance(raw, list):
        return DEFAULT_CLIPS
    clips: list[ClipPrompt] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename", "")).strip()
        if not filename:
            continue
        clips.append(
            ClipPrompt(
                filename=filename,
                duration=int(item.get("duration", 4)),
                label=str(item.get("label", filename)),
                prompt=str(item.get("prompt", item.get("label", filename))),
            )
        )
    return clips or DEFAULT_CLIPS


def download_video(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def generate_clip(provider, clip: ClipPrompt, style_bible: dict[str, Any], model: str, resolution: str, out_dir: Path) -> Path:
    out = out_dir / clip.filename
    if out.exists() and out.stat().st_size > 1024:
        print(f"skip existing {clip.filename}")
        return out
    prompt = (
        f"{style_bible_text(style_bible)} "
        f"Clip task: {clip.prompt} "
        "Vertical 9:16, luxury interior video, slow stable gimbal movement, low camera height, "
        "low saturation warm grey color grading, clean floor reflection, hidden LED lighting, no text, no watermark."
    )
    print(f"generating segmented AI clip {clip.filename} ({clip.duration}s)", flush=True)
    result = provider.generate(
        prompt=prompt,
        model=model,
        duration=clip.duration,
        aspect_ratio="9:16",
        resolution=resolution,
        negative_prompt=str(style_bible.get("negative_prompt", NEGATIVE_PROMPT)),
        audio=False,
    )
    if not result.get("success"):
        raise RuntimeError(f"{clip.filename}: {result.get('error')}")
    video_url = result.get("video")
    if not video_url:
        raise RuntimeError(f"{clip.filename}: provider returned no video URL")
    download_video(video_url, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate segmented AI walkthrough clips via FAL.")
    parser.add_argument("--config", help="Project JSON config")
    parser.add_argument("--clips-dir", help="Output clip directory")
    parser.add_argument("--model", default="seedance-2.0", help="FAL video model family")
    parser.add_argument("--resolution", default="720p", choices=["480p", "540p", "720p", "1080p"])
    parser.add_argument("--no-assemble", action="store_true", help="Only generate clips; do not assemble final video")
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if args.config else None
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name if config_path else "segmented_ai_walkthrough"))
    backend = (config.get("generation_backends") or {}).get("segmented_ai_clips", {})
    model = str(backend.get("model") or args.model)
    out_dir = (
        resolve_path(args.clips_dir)
        or resolve_path(config.get("source_clips_dir"))
        or (ROOT / "assets" / "generated" / project_id / "segmented_ai_clips" if config_path else DEFAULT_CLIP_DIR)
    )
    assert out_dir is not None
    result_path = out_dir / "generation_result.json"

    load_default_env()
    try:
        provider = FALQueueVideoProvider()
    except FALVideoGenerationError as exc:
        write_generation_result(
            result_path,
            {
                "status": "GENERATOR_NOT_READY",
                "generated_source_type": "segmented_ai_clips",
                "generated_capability_level": "L2",
                "source_clips_dir": str(out_dir),
                "clip_count": 0,
                "asset_origin": "auto_generated",
                "provider": "fal",
                "model": model,
                "error": str(exc),
            },
        )
        print(f"GENERATOR_NOT_READY: {exc}")
        print("Add it to one of these files:")
        print(f"- {ROOT / '.env'}")
        print(f"- {REPO / '.env'}")
        print(f"- {Path.home() / '.hermes' / '.env'}")
        print("Format: FAL_KEY=your_real_fal_key")
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    style_bible = style_bible_from_config(config)
    try:
        for clip in clips_from_config(config):
            generate_clip(provider, clip, style_bible, model, args.resolution, out_dir)
    except Exception as exc:
        clip_count = len([p for p in out_dir.glob("*") if p.is_file() and p.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}])
        write_generation_result(
            result_path,
            {
                "status": "GENERATION_FAILED",
                "generated_source_type": "segmented_ai_clips",
                "generated_capability_level": "L2",
                "source_clips_dir": str(out_dir),
                "clip_count": clip_count,
                "asset_origin": "auto_generated",
                "provider": "fal",
                "model": model,
                "error": str(exc),
            },
        )
        print(f"GENERATION_FAILED: {exc}")
        return 4

    clip_count = len([p for p in out_dir.glob("*") if p.is_file() and p.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}])
    write_generation_result(
        result_path,
        {
            "status": "READY" if clip_count >= 2 else "L2_NOT_READY",
            "generated_source_type": "segmented_ai_clips",
            "generated_capability_level": "L2",
            "source_clips_dir": str(out_dir),
            "clip_count": clip_count,
            "asset_origin": "auto_generated",
            "provider": "fal",
            "model": model,
            "note": "多个独立 AI clip 只能标注为 L2 AI 分段空间漫游，不得默认称为 L3/L4。",
        },
    )

    if not args.no_assemble:
        cmd = [sys.executable, str(ASSEMBLER)]
        if config_path:
            cmd += ["--config", str(config_path)]
        else:
            cmd += ["--clips-dir", str(out_dir)]
        subprocess.run(cmd, cwd=str(REPO), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
