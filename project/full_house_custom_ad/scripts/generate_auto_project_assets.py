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
STRICT_TRUE_WALKTHROUGH = "strict_true_walkthrough"
BEST_EFFORT = "best_effort"
VALID_MODES = {STRICT_TRUE_WALKTHROUGH, BEST_EFFORT}
CAPABILITY_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


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


def normalize_mode(config: dict[str, Any]) -> str:
    raw = str(config.get("auto_generation_mode", "")).strip().lower()
    if raw in VALID_MODES:
        return raw
    if raw in {"strict", "true_walkthrough", "l3_only"}:
        return STRICT_TRUE_WALKTHROUGH
    if raw in {"best", "fallback", "highest_executable"}:
        return BEST_EFFORT

    target_type = str(config.get("target_video_type", "")).lower()
    target_level = str(config.get("target_capability_level") or config.get("capability_level") or "").upper()
    allow_auto_downgrade = config.get("allow_auto_downgrade")
    if allow_auto_downgrade is False:
        return STRICT_TRUE_WALKTHROUGH
    if target_type in {"true_walkthrough", "walkthrough", "sample_level_walkthrough"} and target_level in {"L3", "L4"}:
        return STRICT_TRUE_WALKTHROUGH
    return BEST_EFFORT


def normalize_order(config: dict[str, Any], mode: str) -> list[str]:
    if mode == STRICT_TRUE_WALKTHROUGH:
        return ["continuous_ai_video"]
    raw = config.get("auto_generation_order", DEFAULT_ORDER)
    if not isinstance(raw, list) or not raw:
        return DEFAULT_ORDER
    return [str(item) for item in raw]


def target_capability(config: dict[str, Any], mode: str) -> str:
    raw = str(config.get("target_capability_level") or config.get("capability_level") or "").upper()
    if raw in CAPABILITY_RANK:
        return raw
    return "L3" if mode == STRICT_TRUE_WALKTHROUGH else "L1"


def is_downgraded(target_level: str, generated_level: str) -> bool:
    return CAPABILITY_RANK.get(generated_level, 0) < CAPABILITY_RANK.get(target_level, 0)


def generation_result_path(project_id: str, step: str) -> Path:
    subdir = {
        "continuous_ai_video": "continuous_ai_video",
        "segmented_ai_clips": "segmented_ai_clips",
        "static_keyframes": "static_keyframes",
    }.get(step, step)
    return ROOT / "assets" / "generated" / project_id / subdir / "generation_result.json"


def remove_stale_result(project_id: str, step: str) -> None:
    path = generation_result_path(project_id, step)
    if path.exists():
        path.unlink()


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
    mode = normalize_mode(config)
    target_level = target_capability(config, mode)
    attempts: list[dict[str, Any]] = []

    if has_existing_source(config):
        write_generated_project(
            config,
            generated_project,
            {
                "auto_generation_status": "EXISTING_SOURCE",
                "auto_generation_mode": mode,
                "auto_generation_attempted": False,
                "asset_origin": "existing_source",
            },
        )
        report.write_text(
            json.dumps(
                {
                    "status": "EXISTING_SOURCE",
                    "project_id": project_id,
                    "auto_generation_mode": mode,
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
                    "auto_generation_mode": mode,
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

    order = normalize_order(config, mode)
    allow_auto_downgrade = bool(config.get("allow_auto_downgrade", mode != STRICT_TRUE_WALKTHROUGH))

    for step in order:
        if not backend_enabled(config, step):
            attempts.append({"backend": step, "status": "SKIPPED", "reason": "backend disabled"})
            continue

        if step == "continuous_ai_video":
            remove_stale_result(project_id, step)
            proc = run([sys.executable, str(CONTINUOUS_GENERATOR), "--config", str(config_path)])
            result = read_json(generation_result_path(project_id, step))
            attempts.append({"backend": step, "returncode": proc.returncode, **result})
            source_video = resolve_path(result.get("source_video"))
            if proc.returncode == 0 and result.get("status") == "READY" and source_video and source_video.exists():
                generated_level = "L3"
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "continuous_ai_video",
                        "source_video": str(source_video),
                        "capability_level": generated_level,
                        "target_capability_level": target_level,
                        "generated_capability_level": generated_level,
                        "generated_source_type": "continuous_ai_video",
                        "generated_source_video": str(source_video),
                        "generated_assets_dir": str(source_video.parent),
                        "asset_origin": "auto_generated",
                        "auto_generation_attempted": True,
                        "auto_generation_success": True,
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                        "auto_generation_path": step,
                        "auto_generation_mode": mode,
                        "auto_downgraded": is_downgraded(target_level, generated_level),
                        "allow_auto_downgrade": allow_auto_downgrade,
                        "auto_generation_failure_reason": "",
                    },
                )
                print(generated_project)
                return 0

        elif step == "segmented_ai_clips":
            remove_stale_result(project_id, step)
            proc = run([sys.executable, str(SEGMENTED_GENERATOR), "--config", str(config_path), "--no-assemble"])
            result = read_json(generation_result_path(project_id, step))
            attempts.append({"backend": step, "returncode": proc.returncode, **result})
            clips_dir = resolve_path(result.get("source_clips_dir"))
            if proc.returncode == 0 and result.get("status") == "READY" and len(collect_files(clips_dir, VIDEO_EXTS)) >= 2:
                generated_level = "L2"
                auto_downgraded = is_downgraded(target_level, generated_level)
                if auto_downgraded and not allow_auto_downgrade:
                    attempts[-1]["status"] = "BLOCKED_BY_NO_DOWNGRADE"
                    attempts[-1]["reason"] = "generated L2 but allow_auto_downgrade=false"
                    continue
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "segmented_ai_clips",
                        "source_clips_dir": str(clips_dir),
                        "capability_level": generated_level,
                        "target_capability_level": target_level,
                        "generated_capability_level": generated_level,
                        "generated_source_type": "segmented_ai_clips",
                        "generated_assets_dir": str(clips_dir),
                        "asset_origin": "auto_generated",
                        "auto_generation_attempted": True,
                        "auto_generation_success": True,
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                        "auto_generation_path": step,
                        "auto_generation_mode": mode,
                        "auto_downgraded": auto_downgraded,
                        "allow_auto_downgrade": allow_auto_downgrade,
                        "auto_generation_failure_reason": "",
                    },
                )
                print(generated_project)
                return 0

        elif step == "static_keyframes":
            remove_stale_result(project_id, step)
            proc = run([sys.executable, str(STATIC_IMAGE_GENERATOR), "--config", str(config_path)])
            keyframe_dir = static_keyframe_dir(project_id)
            result = read_json(generation_result_path(project_id, step))
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
            if proc.returncode == 0 and result.get("status") == "READY" and images:
                generated_level = "L1"
                auto_downgraded = is_downgraded(target_level, generated_level)
                if auto_downgraded and not allow_auto_downgrade:
                    attempts[-1]["status"] = "BLOCKED_BY_NO_DOWNGRADE"
                    attempts[-1]["reason"] = "generated L1 but allow_auto_downgrade=false"
                    continue
                write_generated_project(
                    config,
                    generated_project,
                    {
                        "source_type": "static_images",
                        "source_images_dir": str(keyframe_dir),
                        "capability_level": generated_level,
                        "target_capability_level": target_level,
                        "generated_capability_level": generated_level,
                        "generated_source_type": "static_images",
                        "generated_assets_dir": str(keyframe_dir),
                        "asset_origin": "auto_generated",
                        "auto_generation_attempted": True,
                        "auto_generation_success": True,
                        "auto_generation_status": "READY",
                        "auto_generation_backend": step,
                        "auto_generation_path": step,
                        "auto_generation_mode": mode,
                        "auto_downgraded": auto_downgraded,
                        "allow_auto_downgrade": allow_auto_downgrade,
                        "auto_generation_failure_reason": "",
                        "shots": result.get("shots", []),
                    },
                )
                print(generated_project)
                return 0

            if proc.returncode != 0 and not (keyframe_dir / "prompt_pack.md").exists():
                run([sys.executable, str(STATIC_PROMPT_PACK), "--config", str(config_path)])

        else:
            attempts.append({"backend": step, "status": "SKIPPED", "reason": "unknown backend"})

    status = "L3_GENERATOR_NOT_READY" if mode == STRICT_TRUE_WALKTHROUGH else "GENERATOR_NOT_READY"
    error = (
        "strict_true_walkthrough requires continuous_ai_video, but no L3 generator produced a renderable single continuous video."
        if mode == STRICT_TRUE_WALKTHROUGH
        else "No configured generator produced renderable L3, L2 or L1 assets."
    )
    report_payload = {
        "status": status,
        "project_id": project_id,
        "output_name": output_name,
        "auto_generation_mode": mode,
        "allow_auto_downgrade": allow_auto_downgrade,
        "target_capability_level": target_level,
        "error": error,
        "missing_or_unavailable_backends": order,
        "attempts": attempts,
        "note": "自动素材生成模式不会要求用户第一轮上传 source_video；strict_true_walkthrough 不会降级 L2/L1，best_effort 才允许用较低等级兜底。",
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(status)
    print(report)
    return 10


if __name__ == "__main__":
    raise SystemExit(main())
