#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"
CONTINUOUS_GENERATOR = ROOT / "scripts" / "generate_continuous_ai_walkthrough_fal.py"
SEGMENTED_GENERATOR = ROOT / "scripts" / "generate_segmented_ai_walkthrough_clips_fal.py"
STATIC_IMAGE_GENERATOR = ROOT / "scripts" / "generate_gpt_image_keyframes.py"
STATIC_PROMPT_PACK = ROOT / "scripts" / "write_static_keyframe_prompt_pack.py"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_ORDER = ["continuous_ai_video", "segmented_ai_clips", "static_keyframes"]


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def collect_files(path: Path | None, exts: set[str]) -> list[Path]:
    if not path or not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in exts else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def has_existing_source(config: dict[str, Any]) -> bool:
    source_video = resolve_path(config.get("source_video"))
    clips_dir = resolve_path(config.get("source_clips_dir") or config.get("clip_dir") or config.get("ai_clips_dir"))
    images_dir = resolve_path(config.get("source_images_dir"))
    return bool(
        collect_files(source_video, VIDEO_EXTS)
        or len(collect_files(clips_dir, VIDEO_EXTS)) >= 2
        or collect_files(images_dir, IMAGE_EXTS)
    )


def auto_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("auto_generate_assets")) or str(config.get("source_policy", "")).lower() == "auto_generate"


def backend_enabled(config: dict[str, Any], name: str) -> bool:
    raw = config.get("generation_backends", {})
    if not isinstance(raw, dict):
        return True
    backend = raw.get(name, {})
    if not isinstance(backend, dict):
        return True
    return bool(backend.get("enabled", True))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc


def write_generated_project(config: dict[str, Any], path: Path, updates: dict[str, Any]) -> None:
    next_config = dict(config)
    next_config.update(updates)
    next_config["auto_generated_assets"] = True
    next_config["source_policy"] = "generated"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(next_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def result_paths(config: dict[str, Any], config_path: Path) -> tuple[str, str, Path, Path]:
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    generated_project = OUT_DIR / f"{project_id}_generated_project.json"
    report = OUT_DIR / f"{project_id}_auto_assets_report.json"
    return project_id, output_name, generated_project, report


def static_keyframe_dir(project_id: str) -> Path:
    return ROOT / "assets" / "generated" / project_id / "static_keyframes"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the highest executable source assets for a project.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id, output_name, generated_project, report = result_paths(config, config_path)
    attempts: list[dict[str, Any]] = []

    if has_existing_source(config):
        write_generated_project(config, generated_project, {"auto_generation_status": "EXISTING_SOURCE"})
        report.write_text(
            json.dumps(
                {
                    "status": "EXISTING_SOURCE",
                    "project_id": project_id,
                    "generated_project": str(generated_project),
                    "attempts": attempts,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(generated_project)
        return 0

    if not auto_enabled(config):
        report.write_text(
            json.dumps(
                {
                    "status": "AUTO_GENERATION_DISABLED",
                    "project_id": project_id,
                    "error": "No source assets and auto_generate_assets/source_policy=auto_generate is not enabled.",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("AUTO_GENERATION_DISABLED")
        return 2

    order = config.get("auto_generation_order", DEFAULT_ORDER)
    if not isinstance(order, list) or not order:
        order = DEFAULT_ORDER

    for step in [str(item) for item in order]:
        if not backend_enabled(config, step):
            attempts.append({"backend": step, "status": "SKIPPED", "reason": "backend disabled"})
            continue

        if step == "continuous_ai_video":
            proc = run([sys.executable, str(CONTINUOUS_GENERATOR), "--config", str(config_path)])
            result = read_json(ROOT / "assets" / "generated" / project_id / "continuous_ai_video" / "generation_result.json")
            attempts.append({"backend": step, "returncode": proc.returncode, **result})
            source_video = resolve_path(result.get("source_video"))
            if proc.returncode == 0 and source_video and source_video.exists():
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "continuous_ai_video",
                        "source_video": str(source_video),
                        "capability_level": "L3",
                        "target_capability_level": "L3",
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                    },
                )
                print(generated_project)
                return 0

        elif step == "segmented_ai_clips":
            proc = run([sys.executable, str(SEGMENTED_GENERATOR), "--config", str(config_path), "--no-assemble"])
            result = read_json(ROOT / "assets" / "generated" / project_id / "segmented_ai_clips" / "generation_result.json")
            attempts.append({"backend": step, "returncode": proc.returncode, **result})
            clips_dir = resolve_path(result.get("source_clips_dir"))
            if proc.returncode == 0 and len(collect_files(clips_dir, VIDEO_EXTS)) >= 2:
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "segmented_ai_clips",
                        "source_clips_dir": str(clips_dir),
                        "capability_level": "L2",
                        "target_capability_level": "L2",
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                    },
                )
                print(generated_project)
                return 0

        elif step == "static_keyframes":
            proc = run([sys.executable, str(STATIC_IMAGE_GENERATOR), "--config", str(config_path)])
            keyframe_dir = static_keyframe_dir(project_id)
            result = read_json(keyframe_dir / "generation_result.json")
            images = collect_files(keyframe_dir, IMAGE_EXTS)
            attempts.append(
                {
                    "backend": step,
                    "returncode": proc.returncode,
                    "status": "READY" if images else "STATIC_IMAGE_GENERATION_PENDING",
                    "source_images_dir": str(keyframe_dir),
                    "image_count": len(images),
                    "prompt_pack": str(keyframe_dir / "prompt_pack.md"),
                    **result,
                }
            )
            if images:
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "static_images",
                        "source_images_dir": str(keyframe_dir),
                        "capability_level": "L1",
                        "target_capability_level": "L1",
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                        "shots": result.get("shots", []),
                    },
                )
                print(generated_project)
                return 0

            if proc.returncode != 0 and not (keyframe_dir / "prompt_pack.md").exists():
                run([sys.executable, str(STATIC_PROMPT_PACK), "--config", str(config_path)])

        else:
            attempts.append({"backend": step, "status": "SKIPPED", "reason": "unknown backend"})

    report_payload = {
        "status": "GENERATOR_NOT_READY",
        "project_id": project_id,
        "output_name": output_name,
        "error": "No configured generator produced renderable L3, L2 or L1 assets.",
        "missing_or_unavailable_backends": ["continuous_ai_video", "segmented_ai_clips", "static_keyframes"],
        "attempts": attempts,
        "note": "自动素材生成模式不会要求用户第一轮上传 source_video；需要配置可用生成后端，或用 prompt pack 生成静态关键帧后重跑。",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GENERATOR_NOT_READY")
    print(report)
    return 10


if __name__ == "__main__":
    raise SystemExit(main())
