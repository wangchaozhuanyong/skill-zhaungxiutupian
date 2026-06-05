#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
L_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}


def load_config(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None, *, base: Path = ROOT) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def collect_files(path: Path | None, exts: set[str]) -> list[Path]:
    if not path or not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in exts else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def source_from_config(config: dict[str, Any], key: str) -> Path | None:
    value = config.get(key)
    return resolve_path(value) if isinstance(value, str) and value.strip() else None


def expected_level(config: dict[str, Any]) -> str | None:
    level = str(config.get("capability_level", "")).upper()
    return level if level in L_ORDER else None


def continuity_checks(config: dict[str, Any]) -> dict[str, bool]:
    raw = config.get("continuity_checks", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def all_l4_checks_passed(config: dict[str, Any]) -> bool:
    checks = continuity_checks(config)
    required = [
        "same_space_path",
        "minimal_hard_cuts",
        "continuous_parallax",
        "material_light_consistency",
        "publish_ready_realism",
    ]
    return all(checks.get(key) is True for key in required)


def labels_for_level(level: str) -> tuple[list[str], list[str]]:
    if level == "L0":
        return ["图片展示型"], ["伪空间漫游", "真正 walkthrough", "样片级连续空间漫游"]
    if level == "L1":
        return ["样片风格伪漫游", "高级伪空间漫游"], ["真正 walkthrough", "样片级连续空间漫游"]
    if level == "L2":
        return ["AI 分段空间漫游型", "segmented AI walkthrough"], ["真正 walkthrough", "样片级连续空间漫游"]
    if level == "L3":
        return ["真正空间漫游", "真正 walkthrough"], ["样片级连续空间漫游，除非 L4 检查通过"]
    return ["样片级连续空间漫游", "sample-level continuous walkthrough"], []


def assess(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    source_type = args.source_type or str(config.get("source_type", "auto"))
    video = resolve_path(args.video) if args.video else source_from_config(config, "source_video")
    images_dir = resolve_path(args.images_dir) if args.images_dir else source_from_config(config, "source_images_dir")
    clips_dir = (
        resolve_path(args.clips_dir)
        if args.clips_dir
        else source_from_config(config, "source_clips_dir")
        or source_from_config(config, "clip_dir")
        or source_from_config(config, "ai_clips_dir")
    )

    image_files = collect_files(images_dir, IMAGE_EXTS)
    clip_files = collect_files(clips_dir, VIDEO_EXTS)
    video_files = collect_files(video, VIDEO_EXTS)

    is_static = bool(image_files) or source_type in {"static_images", "static_images_no_depth"}
    is_multi_clip = len(clip_files) > 1 or source_type in {"segmented_ai_clips", "multi_ai_clips"}
    is_single_video = len(video_files) == 1 and not is_multi_clip
    clip_labels = [
        str(item.get("label", item.get("filename", "")))
        for item in config.get("clips", config.get("clip_specs", []))
        if isinstance(item, dict)
    ]

    level = "L0"
    reasons: list[str] = []

    if source_type == "static_images_no_depth":
        level = "L0"
        reasons.append("只有静态图且未声明具备纵深，不能做漫游。")
    elif is_static and not is_multi_clip and not is_single_video:
        level = "L1"
        reasons.append("素材是静态图片或静态关键帧运镜，最高只能标注为样片风格伪漫游。")
    elif is_multi_clip:
        level = "L2"
        reasons.append("素材是多个独立 AI video clip 拼接，默认只能标注为 AI 分段空间漫游。")
    elif is_single_video:
        if source_type in {"real_video", "3d_walkthrough", "continuous_ai_video"} or config.get("single_continuous_video"):
            level = "L4" if all_l4_checks_passed(config) else "L3"
            reasons.append("素材是单条连续视频，可能达到真正空间漫游；L4 需要连续性检查全部通过。")
        else:
            level = "L3"
            reasons.append("素材是单条视频，但来源未完全声明；可作为 L3 候选，L4 需要人工/配置确认。")
    else:
        reasons.append("未找到可用静态图、clip 或连续视频素材。")

    allowed, forbidden = labels_for_level(level)
    exp = expected_level(config)
    passes_expected = exp is None or L_ORDER[level] >= L_ORDER[exp]
    if exp and not passes_expected:
        reasons.append(f"目标要求 {exp}，当前只能达到 {level}。")

    fade_status = "unknown"
    if is_multi_clip:
        fade_status = "manual_review_required"
    if bool(config.get("script_adds_fade_in_out")):
        fade_status = "added_by_assembly_script"

    return {
        "project_id": config.get("project_id", args.project_id or "walkthrough_continuity_check"),
        "target_video_type": config.get("target_video_type", ""),
        "expected_capability_level": exp or "",
        "assessed_capability_level": level,
        "passes_expected_level": passes_expected,
        "source_type": source_type,
        "is_single_continuous_video": is_single_video,
        "is_multi_clip": is_multi_clip,
        "is_static_image_motion": is_static,
        "clip_count": len(clip_files),
        "image_count": len(image_files),
        "video_count": len(video_files),
        "clips_dir": str(clips_dir) if clips_dir else "",
        "images_dir": str(images_dir) if images_dir else "",
        "video": str(video) if video else "",
        "clip_labels": clip_labels,
        "fade_in_out": fade_status,
        "continuity_checks": continuity_checks(config),
        "allowed_labels": allowed,
        "forbidden_labels": forbidden,
        "reasons": reasons,
    }


def report_markdown(result: dict[str, Any]) -> str:
    def yes(value: bool) -> str:
        return "是" if value else "否"

    checks = result["continuity_checks"]
    check_rows = "\n".join(f"| {key} | {yes(bool(value))} |" for key, value in checks.items()) or "| 未提供 | 否 |"
    allowed = "\n".join(f"- {label}" for label in result["allowed_labels"])
    forbidden = "\n".join(f"- {label}" for label in result["forbidden_labels"])
    reasons = "\n".join(f"- {item}" for item in result["reasons"])
    labels = "\n".join(f"- {label}" for label in result["clip_labels"]) or "- 未提供"
    return f"""# Walkthrough Continuity Report

项目：{result['project_id']}

## 结论

- 当前 capability level：{result['assessed_capability_level']}
- 目标 capability level：{result['expected_capability_level'] or '未声明'}
- 是否达到目标等级：{yes(result['passes_expected_level'])}
- 是否单条连续视频：{yes(result['is_single_continuous_video'])}
- 是否多 clip 拼接：{yes(result['is_multi_clip'])}
- 是否静态图运镜：{yes(result['is_static_image_motion'])}
- clip 数量：{result['clip_count']}
- 图片数量：{result['image_count']}
- 视频数量：{result['video_count']}
- fade in/out 检查：{result['fade_in_out']}

## 允许标记为

{allowed}

## 不允许标记为

{forbidden}

## 连续性检查

| 检查项 | 是否通过 |
|---|---|
{check_rows}

## clip 标签

{labels}

## 原因

{reasons}

## 固定规则

- 静态图生成视频不得通过真正 walkthrough 检查。
- 多个独立 AI clip 拼接不得自动通过样片级检查。
- 真实连续视频、专业 3D 漫游导出或单条连续 AI video，才可能达到 L3。
- 同一空间、连续视差、少硬切、材质灯光比例稳定并达到发布级真实感，才可能达到 L4。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate walkthrough continuity and capability level.")
    parser.add_argument("--config", help="Project JSON config")
    parser.add_argument("--video", help="Single video source")
    parser.add_argument("--clips-dir", help="Directory of AI video clips")
    parser.add_argument("--images-dir", help="Directory of static images/keyframes")
    parser.add_argument(
        "--source-type",
        choices=[
            "auto",
            "static_images",
            "static_images_no_depth",
            "segmented_ai_clips",
            "multi_ai_clips",
            "real_video",
            "3d_walkthrough",
            "continuous_ai_video",
        ],
        default=None,
    )
    parser.add_argument("--project-id")
    parser.add_argument("--output", help="Output markdown report path")
    parser.add_argument("--json-output", help="Optional JSON report path")
    parser.add_argument("--fail-on-overclaim", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if args.config else None
    config = load_config(config_path)
    result = assess(args, config)

    output = resolve_path(args.output) if args.output else OUT_DIR / f"{result['project_id']}_continuity_report.md"
    assert output is not None
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report_markdown(result), encoding="utf-8")

    if args.json_output:
        json_path = resolve_path(args.json_output)
        assert json_path is not None
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(output)
    if args.fail_on_overclaim and not result["passes_expected_level"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
