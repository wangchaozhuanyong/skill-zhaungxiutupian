#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_walkthrough_continuity.py"
AUTO_ASSET_GENERATOR = ROOT / "scripts" / "generate_auto_project_assets.py"
SEGMENTED_ASSEMBLER = ROOT / "scripts" / "assemble_segmented_ai_walkthrough_clips.py"
CONTINUOUS_RENDERER = ROOT / "scripts" / "render_continuous_video_project.py"
STATIC_RENDERER = ROOT / "scripts" / "render_static_image_project.py"
CONTINUOUS_SOURCE_TYPES = {"real_video", "3d_walkthrough", "continuous_ai_video"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def collect_video_files(path: Path | None) -> list[Path]:
    if not path or not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in VIDEO_EXTS else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTS)


def collect_image_files(path: Path | None) -> list[Path]:
    if not path or not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in IMAGE_EXTS else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def has_segmented_clips(config: dict[str, Any]) -> bool:
    clips_dir = resolve_path(config.get("source_clips_dir") or config.get("clip_dir") or config.get("ai_clips_dir"))
    return len(collect_video_files(clips_dir)) >= 2


def has_static_images(config: dict[str, Any]) -> bool:
    source_type = str(config.get("source_type", ""))
    images_dir = resolve_path(config.get("source_images_dir"))
    return source_type in {"static_images", "static_images_no_depth"} and bool(collect_image_files(images_dir))


def has_continuous_video(config: dict[str, Any]) -> bool:
    source_type = str(config.get("source_type", ""))
    source_video = resolve_path(config.get("source_video"))
    if source_type in CONTINUOUS_SOURCE_TYPES:
        return bool(source_video and source_video.exists())
    return bool(source_video and source_video.exists() and not has_segmented_clips(config))


def has_any_renderable_source(config: dict[str, Any]) -> bool:
    return has_continuous_video(config) or has_segmented_clips(config) or has_static_images(config)


def auto_generation_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("auto_generate_assets")) or str(config.get("source_policy", "")).lower() == "auto_generate"


def generated_config_path(config: dict[str, Any], config_path: Path) -> Path:
    project_id = str(config.get("project_id", config_path.parent.name))
    return ROOT / "output" / f"{project_id}_generated_project.json"


def auto_report_path(config: dict[str, Any], config_path: Path) -> Path:
    project_id = str(config.get("project_id", config_path.parent.name))
    return ROOT / "output" / f"{project_id}_auto_assets_report.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a full house custom ad project from project.json.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-downgrade", action="store_true", help="Override config allow_downgrade")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    if not has_any_renderable_source(config) and auto_generation_enabled(config):
        print("自动素材生成模式：已启用")
        print(f"自动生成模式：{config.get('auto_generation_mode', 'best_effort')}")
        print("用户是否提供素材：否")
        print("素材来源：自动生成")
        proc = run([sys.executable, str(AUTO_ASSET_GENERATOR), "--config", str(config_path)], check=False)
        next_config_path = generated_config_path(config, config_path)
        if proc.returncode != 0 or not next_config_path.exists():
            report = read_json(auto_report_path(config, config_path))
            status = str(report.get("status") or "GENERATOR_NOT_READY")
            print(status)
            if report.get("error"):
                print(report["error"])
            print("自动素材生成没有产出可渲染素材。不会要求用户上传 source_video。")
            if status == "SESSION_VIDEO_PROVIDER_NOT_AVAILABLE":
                providers = report.get("session_video_provider_order") or ["codex_video", "hyperframes"]
                print(f"当前会话未暴露可调用视频 provider：{', '.join(str(item) for item in providers)}。")
                print("这不是要求 OPENAI_API_KEY / FAL_KEY；API 只在明确切换到 api_unattended 模式时使用。")
            if status == "L3_GENERATOR_NOT_READY":
                print("strict_true_walkthrough 模式只允许 L3 单条连续视频，不会自动降级 L2/L1。")
            return 10
        config_path = next_config_path.resolve()
        config = load_config(config_path)
        print(f"使用自动生成项目配置：{config_path}")

    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    report = ROOT / "output" / f"{output_name}_continuity_report.md"

    validate_cmd = [
        sys.executable,
        str(VALIDATOR),
        "--config",
        str(config_path),
        "--output",
        str(report),
    ]
    allow_downgrade = bool(config.get("allow_downgrade", False)) or args.allow_downgrade
    if not allow_downgrade:
        validate_cmd.append("--fail-on-overclaim")

    validation = run(validate_cmd, check=False)
    if validation.returncode == 3 and not has_any_renderable_source(config):
        print("没有找到可渲染素材。已生成连续性报告。")
        print(report)
        return 2
    if validation.returncode == 3:
        print(
            "项目目标高于当前素材能力，已停止渲染。请查看 continuity_report.md，或明确 allow_downgrade=true。",
            file=sys.stderr,
        )
        return 3
    if validation.returncode != 0:
        return validation.returncode
    if args.validate_only:
        return 0

    if has_continuous_video(config):
        cmd = [sys.executable, str(CONTINUOUS_RENDERER), "--config", str(config_path)]
        if allow_downgrade:
            cmd.append("--allow-downgrade")
        return run(cmd, check=False).returncode

    if has_segmented_clips(config):
        return run([sys.executable, str(SEGMENTED_ASSEMBLER), "--config", str(config_path)], check=False).returncode

    if has_static_images(config):
        if STATIC_RENDERER.exists():
            return run([sys.executable, str(STATIC_RENDERER), "--config", str(config_path)], check=False).returncode
        print("当前项目只有静态图素材，但还没有通用 L1 静态关键帧/伪漫游渲染器。")
        print("请使用 gpt-image-2 生成关键帧后接入 L1 renderer，或改用已有图片展示脚本。")
        print(report)
        return 4

    print("没有找到可渲染素材。已生成连续性报告。")
    print(report)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
