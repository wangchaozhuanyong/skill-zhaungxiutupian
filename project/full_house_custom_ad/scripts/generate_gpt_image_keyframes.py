#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PACK_SCRIPT = ROOT / "scripts" / "write_static_keyframe_prompt_pack.py"
IMAGE_EXT = ".png"

sys.path.insert(0, str(ROOT / "scripts"))
from image_generation_provider import ImageGenerationError, OpenAIImageProvider


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def backend_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("generation_backends", {})
    if isinstance(raw, dict) and isinstance(raw.get("static_keyframes"), dict):
        return raw["static_keyframes"]
    return {}


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def shot_type_from_id(shot_id: str) -> str:
    if "entry" in shot_id:
        return "entry"
    if "living" in shot_id:
        return "living_room_opening"
    if "tv_wall" in shot_id:
        return "tv_wall_focus"
    if "dining" in shot_id:
        return "dining_slide"
    if "material" in shot_id:
        return "material_detail"
    return "final_wide"


def motion_from_shot_type(shot_type: str) -> str:
    return {
        "entry": "edge_push",
        "living_room_opening": "slow_lateral_reveal",
        "tv_wall_focus": "push_to_center",
        "dining_slide": "dining_slide",
        "material_detail": "micro_push",
        "final_wide": "settle",
    }.get(shot_type, "slow_lateral_reveal")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate L1 static keyframes using the OpenAI Image API.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    out_dir = ROOT / "assets" / "generated" / project_id / "static_keyframes"
    prompt_pack = out_dir / "prompt_pack.md"
    generation_plan = out_dir / "generation_plan.json"
    result_path = out_dir / "generation_result.json"

    run([sys.executable, str(PROMPT_PACK_SCRIPT), "--config", str(config_path)])
    plan = read_json(generation_plan)
    prompts = [item for item in plan.get("prompts", []) if isinstance(item, dict)]
    if not prompts:
        write_result(
            result_path,
            {
                "status": "GENERATION_FAILED",
                "generated_source_type": "static_keyframes",
                "generated_capability_level": "L1",
                "source_images_dir": str(out_dir),
                "image_count": 0,
                "asset_origin": "auto_generated",
                "error": "Prompt pack did not contain any prompts.",
            },
        )
        return 3

    backend = backend_config(config)
    model = str(backend.get("model") or "gpt-image-1.5")
    size = str(backend.get("size") or "1024x1536")
    quality = str(backend.get("quality") or "high")
    background = str(backend.get("background") or "opaque")
    output_format = str(backend.get("output_format") or "png")
    minimum_keyframes = int(backend.get("minimum_keyframes") or 4)
    max_keyframes = int(backend.get("max_keyframes") or len(prompts))
    selected = prompts[: max(1, min(max_keyframes, len(prompts)))]

    try:
        provider = OpenAIImageProvider()
    except ImageGenerationError as exc:
        write_result(
            result_path,
            {
                "status": "GENERATOR_NOT_READY",
                "generated_source_type": "static_keyframes",
                "generated_capability_level": "L1",
                "source_images_dir": str(out_dir),
                "image_count": 0,
                "asset_origin": "auto_generated",
                "provider": "openai_images",
                "model": model,
                "prompt_pack": str(prompt_pack),
                "error": str(exc),
                "note": "已生成 prompt pack；配置 OPENAI_API_KEY 后可自动生成图片并进入 L1 renderer。",
            },
        )
        print(f"GENERATOR_NOT_READY: {exc}")
        return 2

    generated: list[dict[str, Any]] = []
    errors: list[str] = []
    for item in selected:
        shot_id = str(item.get("shot_id") or Path(str(item.get("filename", "keyframe"))).stem)
        filename = str(item.get("filename") or f"{shot_id}{IMAGE_EXT}")
        output_path = out_dir / filename
        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            output_path = output_path.with_suffix(IMAGE_EXT)
        if output_path.exists() and output_path.stat().st_size > 1024:
            generated.append({"shot_id": shot_id, "path": str(output_path), "status": "existing"})
            continue
        try:
            result = provider.generate(
                prompt=str(item.get("prompt", "")),
                output_path=output_path,
                model=model,
                size=size,
                quality=quality,
                background=background,
                output_format=output_format,
            )
            generated.append({"shot_id": shot_id, "path": str(output_path), "status": "generated", **result})
            print(output_path)
        except Exception as exc:
            errors.append(f"{shot_id}: {exc}")
            print(f"GENERATION_FAILED {shot_id}: {exc}", file=sys.stderr)

    image_count = len([item for item in generated if Path(str(item.get("path", ""))).exists()])
    status = "READY" if image_count >= minimum_keyframes else "GENERATION_FAILED"
    shots = []
    for item in generated:
        path = Path(str(item.get("path", "")))
        if not path.exists():
            continue
        shot_type = shot_type_from_id(str(item.get("shot_id", "")))
        shots.append(
            {
                "filename": path.name,
                "shot_type": shot_type,
                "motion": motion_from_shot_type(shot_type),
                "label": str(item.get("shot_id", path.stem)),
            }
        )
    write_result(
        result_path,
        {
            "status": status,
            "generated_source_type": "static_images",
            "generated_capability_level": "L1",
            "source_images_dir": str(out_dir),
            "image_count": image_count,
            "asset_origin": "auto_generated",
            "provider": "openai_images",
            "model": model,
            "size": size,
            "quality": quality,
            "prompt_pack": str(prompt_pack),
            "generation_plan": str(generation_plan),
            "minimum_keyframes": minimum_keyframes,
            "shots": shots,
            "generated": generated,
            "errors": errors,
            "note": "静态关键帧最高只能进入 L1 样片风格伪漫游，不得称为真正 walkthrough。",
        },
    )
    print(result_path)
    return 0 if status == "READY" else 4


if __name__ == "__main__":
    raise SystemExit(main())
