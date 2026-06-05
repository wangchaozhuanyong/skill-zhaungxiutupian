#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    import sys

    sys.path.insert(0, str(DEPS))
OUT_DIR = ROOT / "output"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
L_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
VISUAL_SAMPLE_COUNT = 32
SAMPLE_LEVEL_PASS_SCORE = 85.0
SAMPLE_LEVEL_SEVERE_SCORE = 70.0
SEMANTIC_POSITIVE_CHECKS = [
    "电视墙是否一致",
    "沙发是否一致",
    "餐桌是否一致",
    "地面材质是否一致",
    "柜体颜色是否一致",
    "灯光色温是否一致",
    "空间比例是否一致",
    "镜头路径是否连续",
    "是否达到样片发布级",
]
SEMANTIC_NEGATIVE_CHECKS = ["是否存在明显换房"]


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


def file_hash(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def review_path_from_config(config: dict[str, Any], output_name: str) -> Path | None:
    value = config.get("manual_semantic_review_file")
    if isinstance(value, str) and value.strip():
        return resolve_path(value)
    return OUT_DIR / f"{output_name}_semantic_review.md"


def line_value(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}\s*[:：]\s*(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def selected_choice(line: str) -> str:
    checked_yes = re.search(r"\[[xX✓✔]\]\s*是", line) is not None
    checked_no = re.search(r"\[[xX✓✔]\]\s*否", line) is not None
    checked_pass = re.search(r"\[[xX✓✔]\]\s*通过", line) is not None
    checked_fail = re.search(r"\[[xX✓✔]\]\s*不通过", line) is not None
    if checked_yes:
        return "是"
    if checked_no:
        return "否"
    if checked_pass:
        return "通过"
    if checked_fail:
        return "不通过"
    value = line.split("：", 1)[-1].split(":", 1)[-1].strip()
    if value.startswith("是"):
        return "是"
    if value.startswith("否"):
        return "否"
    if value.startswith("通过"):
        return "通过"
    if value.startswith("不通过"):
        return "不通过"
    return ""


def review_check_value(text: str, label: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(rf"^(?:[-*]\s*)?{re.escape(label)}\s*[:：]", line):
            return selected_choice(line)
    return ""


def sample_level_score_value(text: str) -> float | None:
    raw = line_value(text, "样片级专项评分")
    if not raw:
        return None
    score_part = raw.split("/", 1)[0].strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)", score_part)
    if not match:
        return None
    value = float(match.group(1))
    if value < 0 or value > 100:
        return None
    return value


def semantic_review_status(config: dict[str, Any], project_id: str, output_name: str, source_video: Path | None) -> dict[str, Any]:
    path = review_path_from_config(config, output_name)
    result: dict[str, Any] = {
        "semantic_review_file": str(path) if path else "",
        "semantic_review_file_exists": bool(path and path.exists()),
        "semantic_review_file_valid": False,
        "semantic_review_errors": [],
        "semantic_review_checks": {},
        "semantic_review_reviewer": "",
        "semantic_review_date": "",
        "semantic_review_conclusion": "",
        "semantic_review_source_hash": "",
        "semantic_review_expected_source_hash": file_hash(source_video),
        "sample_level_score": None,
        "sample_level_score_passed": False,
        "sample_level_score_severe": False,
    }
    errors: list[str] = result["semantic_review_errors"]
    if not path:
        errors.append("未配置人工空间语义复核文件。")
        return result
    if not path.exists():
        errors.append(f"人工空间语义复核文件不存在：{path}")
        return result

    text = path.read_text(encoding="utf-8", errors="replace")
    score = sample_level_score_value(text)
    result["sample_level_score"] = score
    result["sample_level_score_passed"] = bool(score is not None and score >= SAMPLE_LEVEL_PASS_SCORE)
    result["sample_level_score_severe"] = bool(score is not None and score < SAMPLE_LEVEL_SEVERE_SCORE)
    if score is None:
        errors.append("样片级专项评分未填写或格式无效。")
    elif score < SAMPLE_LEVEL_PASS_SCORE:
        errors.append(f"样片级专项评分 {score:g} 低于 {SAMPLE_LEVEL_PASS_SCORE:g}，不得通过 L4。")
    if score is not None and score < SAMPLE_LEVEL_SEVERE_SCORE:
        errors.append(f"样片级专项评分 {score:g} 低于 {SAMPLE_LEVEL_SEVERE_SCORE:g}，必须考虑降级。")

    file_project_id = line_value(text, "项目 ID")
    if file_project_id != project_id:
        errors.append(f"复核文件项目 ID 不匹配：{file_project_id or '未填写'} != {project_id}")

    reviewer = line_value(text, "人工复核人")
    review_date = line_value(text, "复核日期")
    result["semantic_review_reviewer"] = reviewer
    result["semantic_review_date"] = review_date
    if not reviewer:
        errors.append("人工复核人未填写。")
    if not review_date:
        errors.append("复核日期未填写。")

    review_hash = line_value(text, "源视频 hash")
    expected_hash = result["semantic_review_expected_source_hash"]
    result["semantic_review_source_hash"] = review_hash
    if expected_hash and review_hash != expected_hash:
        errors.append("复核文件源视频 hash 与当前 source_video 不匹配。")
    if not expected_hash:
        errors.append("当前没有可校验的 source_video hash。")

    checks: dict[str, str] = {}
    for label in SEMANTIC_POSITIVE_CHECKS:
        value = review_check_value(text, label)
        checks[label] = value
        if value != "是":
            errors.append(f"{label} 未勾选“是”。")
    for label in SEMANTIC_NEGATIVE_CHECKS:
        value = review_check_value(text, label)
        checks[label] = value
        if value != "否":
            errors.append(f"{label} 必须勾选“否”。")
    result["semantic_review_checks"] = checks

    conclusion = review_check_value(text, "复核结论")
    result["semantic_review_conclusion"] = conclusion
    if conclusion != "通过":
        errors.append("复核结论未勾选“通过”。")

    result["semantic_review_file_valid"] = len(errors) == 0
    return result


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


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def get_duration(path: Path) -> float:
    proc = run([ffmpeg_exe(), "-hide_banner", "-i", str(path)])
    text = "\n".join([proc.stdout, proc.stderr])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def extract_frame(src: Path, timestamp: float, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = run(
        [
            ffmpeg_exe(),
            "-y",
            "-ss",
            f"{max(0.0, timestamp):.3f}",
            "-i",
            str(src),
            "-frames:v",
            "1",
            "-update",
            "1",
            "-q:v",
            "2",
            str(out),
        ]
    )
    return proc.returncode == 0 and out.exists() and out.stat().st_size > 512


def extract_video_frames(video: Path, frame_dir: Path, output_name: str, samples: int) -> list[Path]:
    duration = get_duration(video)
    if duration <= 0.0:
        return []
    start = 0.12 if duration <= 0.6 else 0.25
    end = max(start, duration - start)
    if samples == 1:
        times = [duration / 2]
    else:
        step = (end - start) / max(1, samples - 1)
        times = [start + i * step for i in range(samples)]
    frames: list[Path] = []
    for index, timestamp in enumerate(times):
        out = frame_dir / f"{output_name}_frame_{index:02d}.jpg"
        if extract_frame(video, timestamp, out):
            frames.append(out)
    return frames


def extract_clip_frames(clip_files: list[Path], frame_dir: Path, output_name: str, samples: int) -> list[Path]:
    if not clip_files:
        return []
    per_clip = max(1, math.ceil(samples / len(clip_files)))
    frames: list[Path] = []
    for clip_index, clip in enumerate(clip_files):
        duration = get_duration(clip)
        if duration <= 0.0:
            continue
        clip_samples = min(per_clip, samples - len(frames))
        start = 0.12 if duration <= 0.6 else 0.25
        end = max(start, duration - start)
        for sample_index in range(clip_samples):
            if clip_samples == 1:
                timestamp = duration / 2
            else:
                timestamp = start + (end - start) * sample_index / max(1, clip_samples - 1)
            out = frame_dir / f"{output_name}_clip_{clip_index:02d}_{sample_index:02d}.jpg"
            if extract_frame(clip, timestamp, out):
                frames.append(out)
            if len(frames) >= samples:
                return frames
    return frames


def image_frames(image_files: list[Path], frame_dir: Path, output_name: str, samples: int) -> list[Path]:
    try:
        from PIL import Image
    except Exception:
        return []
    chosen = image_files[:samples]
    frames: list[Path] = []
    frame_dir.mkdir(parents=True, exist_ok=True)
    for index, image_path in enumerate(chosen):
        out = frame_dir / f"{output_name}_image_{index:02d}.jpg"
        try:
            with Image.open(image_path) as img:
                img.convert("RGB").save(out, quality=90)
            frames.append(out)
        except Exception:
            continue
    return frames


def make_contact_sheet(frames: list[Path], sheet_path: Path) -> str:
    if not frames:
        return ""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return ""
    thumbs = []
    for frame in frames:
        try:
            with Image.open(frame) as img:
                thumb = img.convert("RGB")
                thumb.thumbnail((216, 384), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (216, 384), (18, 18, 18))
                canvas.paste(thumb, ((216 - thumb.width) // 2, (384 - thumb.height) // 2))
                thumbs.append((frame.name, canvas))
        except Exception:
            continue
    if not thumbs:
        return ""
    cols = 4
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (216 * cols, 384 * rows), (16, 16, 16))
    draw = ImageDraw.Draw(sheet)
    for index, (name, thumb) in enumerate(thumbs):
        x = (index % cols) * 216
        y = (index // cols) * 384
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + 215, y + 383), outline=(54, 54, 54), width=1)
        draw.text((x + 8, y + 8), f"{index + 1}", fill=(238, 238, 238))
        draw.text((x + 8, y + 28), name[:24], fill=(180, 180, 180))
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=92)
    return str(sheet_path)


def frame_metrics(frames: list[Path]) -> dict[str, Any]:
    base = {
        "sampled_frame_count": len(frames),
        "scene_change_count": 0,
        "avg_frame_delta": 0.0,
        "max_frame_delta": 0.0,
        "max_delta_from_frame": 0,
        "max_delta_to_frame": 0,
        "hard_cut_risk": "unknown",
        "motion_continuity_risk": "unknown",
    }
    if len(frames) < 2:
        return base
    try:
        import numpy as np
        from PIL import Image
    except Exception:
        return base
    arrays = []
    for frame in frames:
        try:
            with Image.open(frame) as img:
                arr = np.asarray(img.convert("RGB").resize((160, 284))).astype(np.float32) / 255.0
                gray = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
                arrays.append(gray)
        except Exception:
            continue
    if len(arrays) < 2:
        return base
    deltas = [float(np.mean(np.abs(arrays[i] - arrays[i - 1]))) for i in range(1, len(arrays))]
    avg_delta = float(np.mean(deltas))
    max_delta = float(np.max(deltas))
    max_delta_index = int(np.argmax(deltas)) if deltas else 0
    scene_changes = sum(1 for item in deltas if item >= 0.24)
    if scene_changes >= 3 or max_delta >= 0.40:
        hard_risk = "high"
    elif scene_changes >= 1 or max_delta >= 0.28:
        hard_risk = "medium"
    else:
        hard_risk = "low"
    if hard_risk == "high" or avg_delta >= 0.18:
        motion_risk = "high"
    elif hard_risk == "medium" or avg_delta >= 0.11:
        motion_risk = "medium"
    else:
        motion_risk = "low"
    return {
        "sampled_frame_count": len(arrays),
        "scene_change_count": scene_changes,
        "avg_frame_delta": round(avg_delta, 4),
        "max_frame_delta": round(max_delta, 4),
        "max_delta_from_frame": max_delta_index + 1,
        "max_delta_to_frame": max_delta_index + 2,
        "hard_cut_risk": hard_risk,
        "motion_continuity_risk": motion_risk,
    }


def make_delta_pair_sheet(frames: list[Path], metrics: dict[str, Any], sheet_path: Path) -> str:
    from_index = int(metrics.get("max_delta_from_frame", 0) or 0) - 1
    to_index = int(metrics.get("max_delta_to_frame", 0) or 0) - 1
    if from_index < 0 or to_index < 0 or from_index >= len(frames) or to_index >= len(frames):
        return ""
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return ""
    panels = []
    for label, frame in [("before", frames[from_index]), ("after", frames[to_index])]:
        try:
            with Image.open(frame) as img:
                thumb = img.convert("RGB")
                thumb.thumbnail((360, 640), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (360, 640), (16, 16, 16))
                canvas.paste(thumb, ((360 - thumb.width) // 2, (640 - thumb.height) // 2))
                draw = ImageDraw.Draw(canvas)
                draw.rectangle((0, 0, 359, 639), outline=(66, 66, 66), width=2)
                draw.text((12, 12), f"{label}: {frame.name[:32]}", fill=(235, 235, 235))
                panels.append(canvas)
        except Exception:
            continue
    if len(panels) != 2:
        return ""
    sheet = Image.new("RGB", (720, 640), (12, 12, 12))
    sheet.paste(panels[0], (0, 0))
    sheet.paste(panels[1], (360, 0))
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(sheet_path, quality=92)
    return str(sheet_path)


def collect_visual_evidence(
    *,
    video_files: list[Path],
    clip_files: list[Path],
    image_files: list[Path],
    is_single_video: bool,
    is_multi_clip: bool,
    is_static: bool,
    output_name: str,
    keyframes_output: Path | None,
    sample_count: int,
) -> dict[str, Any]:
    frame_dir = OUT_DIR / f"{output_name}_continuity_frames"
    sheet_path = keyframes_output or OUT_DIR / f"{output_name}_continuity_keyframes.jpg"
    pair_sheet_path = OUT_DIR / f"{output_name}_max_delta_pair.jpg"
    note = ""
    frames: list[Path] = []
    source = "none"

    try:
        if is_single_video and video_files:
            source = "single_video"
            frames = extract_video_frames(video_files[0], frame_dir, output_name, sample_count)
            note = "已从单条视频抽帧检查。"
        elif is_multi_clip and clip_files:
            source = "multi_clip"
            frames = extract_clip_frames(clip_files, frame_dir, output_name, sample_count)
            note = "已从多个 clip 抽帧；多 clip 拼接仍默认不能升级为 L4。"
        elif is_static and image_files:
            source = "static_images"
            frames = image_frames(image_files, frame_dir, output_name, sample_count)
            note = "已从静态图生成关键帧证据；静态图不能通过真正 walkthrough 检查。"
        else:
            note = "没有可抽帧的视频、clip 或图片。"
    except Exception as exc:
        note = f"视觉证据抽取失败：{exc}"
        frames = []

    metrics = frame_metrics(frames)
    sheet = make_contact_sheet(frames, sheet_path)
    pair_sheet = make_delta_pair_sheet(frames, metrics, pair_sheet_path)
    visual_available = bool(sheet) and metrics["sampled_frame_count"] >= 2
    metrics.update(
        {
            "keyframe_sheet": sheet,
            "max_delta_pair_sheet": pair_sheet,
            "visual_evidence_available": visual_available,
            "visual_evidence_source": source,
            "visual_evidence_note": note,
        }
    )
    return metrics


def assess(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    project_id = str(config.get("project_id", args.project_id or "walkthrough_continuity_check"))
    output_name = str(config.get("output_name", project_id))
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
    semantic_review = semantic_review_status(config, project_id, output_name, video)
    semantic_review_passed = bool(semantic_review["semantic_review_file_valid"])
    sample_score_passed = bool(semantic_review["sample_level_score_passed"])

    requested_multi_clip = source_type in {"segmented_ai_clips", "multi_ai_clips"}
    is_static = bool(image_files) or source_type in {"static_images", "static_images_no_depth"}
    is_multi_clip = len(clip_files) >= 2
    is_single_video = len(video_files) == 1 and not is_multi_clip
    readiness_status = "ready"
    if requested_multi_clip and len(clip_files) < 2:
        readiness_status = "L2_not_ready"
    clip_labels = [
        str(item.get("label", item.get("filename", "")))
        for item in config.get("clips", config.get("clip_specs", []))
        if isinstance(item, dict)
    ]

    keyframes_output = resolve_path(args.keyframes_output) if args.keyframes_output else None
    visual = collect_visual_evidence(
        video_files=video_files,
        clip_files=clip_files,
        image_files=image_files,
        is_single_video=is_single_video,
        is_multi_clip=is_multi_clip,
        is_static=is_static,
        output_name=output_name,
        keyframes_output=keyframes_output,
        sample_count=max(2, int(args.sample_count or VISUAL_SAMPLE_COUNT)),
    )

    level = "L0"
    reasons: list[str] = []

    if source_type == "static_images_no_depth":
        level = "L0"
        reasons.append("只有静态图且未声明具备纵深，不能做漫游。")
    elif source_type == "static_images" and not image_files and not is_multi_clip and not is_single_video:
        level = "L0"
        reasons.append("声明为静态图项目，但没有找到可审查的图片素材。")
    elif requested_multi_clip and len(clip_files) < 2:
        level = "L0"
        reasons.append(
            f"声明为 L2 分段 AI 漫游，但只找到 {len(clip_files)} 个 clip；至少需要 2 个 AI video clip。"
        )
    elif is_static and not is_multi_clip and not is_single_video:
        level = "L1"
        reasons.append("素材是静态图片或静态关键帧运镜，最高只能标注为样片风格伪漫游。")
    elif is_multi_clip:
        level = "L2"
        reasons.append("素材是多个独立 AI video clip 拼接，默认只能标注为 AI 分段空间漫游。")
    elif is_single_video:
        l4_visual_ok = (
            visual["visual_evidence_available"]
            and visual["hard_cut_risk"] != "high"
            and visual["motion_continuity_risk"] != "high"
        )
        l4_base_gate_ok = all_l4_checks_passed(config) and l4_visual_ok
        if source_type in {"real_video", "3d_walkthrough", "continuous_ai_video"} or config.get("single_continuous_video"):
            if l4_base_gate_ok and semantic_review_passed and sample_score_passed:
                level = "L4"
                reasons.append("素材是单条连续视频，基础视觉门禁、人工空间语义复核文件和样片级专项评分均支持 L4。")
            elif l4_base_gate_ok:
                level = "L3"
                reasons.append("素材是单条连续视频，已达到 L4 基础视觉门禁候选；最终 L4 仍需有效的人工空间语义复核文件和 >=85 的样片级专项评分。")
            else:
                level = "L3"
                reasons.append("素材是单条连续视频，可能达到真正空间漫游；L4 还需要全部连续性检查、低硬切风险和人工空间语义复核。")
        else:
            level = "L3"
            reasons.append("素材是单条视频，但来源未完全声明；可作为 L3 候选，L4 需要来源、连续性和视觉证据确认。")
    else:
        reasons.append("未找到可用静态图、clip 或连续视频素材。")

    if requested_multi_clip and len(clip_files) < 2:
        reasons.append("L2 目标素材未就绪；不能把空目录或单个 clip 标注为 AI 分段空间漫游。")
    elif requested_multi_clip:
        reasons.append("多个独立 AI clip 即使有动态，也不能默认称为真正 walkthrough 或样片级连续空间漫游。")
    if is_static:
        reasons.append("静态图运镜不能升级为真正 walkthrough。")
    if expected_level(config) == "L4" and not visual["visual_evidence_available"]:
        reasons.append("目标为 L4，但没有可审查的关键帧视觉证据。")
    if expected_level(config) == "L4" and visual["hard_cut_risk"] == "high":
        reasons.append("目标为 L4，但关键帧差异显示硬切/空间断裂风险高。")
    if expected_level(config) == "L4" and not semantic_review_passed:
        reasons.append("目标为 L4，但人工空间语义复核文件未通过；最终样片级命名需要有效复核记录。")
        reasons.extend(str(item) for item in semantic_review["semantic_review_errors"])
    if expected_level(config) == "L4" and not sample_score_passed:
        reasons.append("目标为 L4，但样片级专项评分未达到 85 分硬门槛。")
    if expected_level(config) == "L4" and bool(semantic_review["sample_level_score_severe"]):
        reasons.append("样片级专项评分低于 70 分，必须降级处理。")
    if expected_level(config) == "L4" and bool(config.get("manual_semantic_review_passed")) and not semantic_review_passed:
        reasons.append("project.json 中的 manual_semantic_review_passed=true 不能单独作为 L4 通过依据。")

    allowed, forbidden = labels_for_level(level)
    exp = expected_level(config)
    passes_expected = exp is None or L_ORDER[level] >= L_ORDER[exp]
    if exp == "L4":
        passes_expected = (
            passes_expected
            and level == "L4"
            and visual["visual_evidence_available"]
            and visual["hard_cut_risk"] != "high"
            and semantic_review_passed
            and sample_score_passed
        )
    if exp and not passes_expected:
        reasons.append(f"目标要求 {exp}，当前只能达到 {level}。")

    fade_status = "unknown"
    if is_multi_clip:
        fade_status = "manual_review_required"
    if bool(config.get("script_adds_fade_in_out")):
        fade_status = "added_by_assembly_script"

    manual_review_required = bool(
        is_multi_clip
        or (exp in {"L3", "L4"} and not visual["visual_evidence_available"])
        or (exp == "L4" and level != "L4")
        or visual["hard_cut_risk"] in {"medium", "high"}
        or (exp == "L4" and not semantic_review_passed)
        or (exp == "L4" and not sample_score_passed)
    )
    if exp == "L4":
        l4_base_candidate = bool(
            is_single_video
            and all_l4_checks_passed(config)
            and visual["visual_evidence_available"]
            and visual["hard_cut_risk"] != "high"
            and visual["motion_continuity_risk"] != "high"
        )
        l4_gate_result = "candidate" if l4_base_candidate else "failed"
    else:
        l4_gate_result = "not_applicable"

    return {
        "project_id": project_id,
        "target_video_type": config.get("target_video_type", ""),
        "expected_capability_level": exp or "",
        "assessed_capability_level": level,
        "passes_expected_level": passes_expected,
        "source_type": source_type,
        "is_single_continuous_video": is_single_video,
        "is_multi_clip": is_multi_clip,
        "is_static_image_motion": is_static,
        "readiness_status": readiness_status,
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
        "manual_review_required": manual_review_required,
        "semantic_review_required": exp == "L4" or level == "L4",
        "manual_semantic_review_passed": semantic_review_passed,
        "l4_gate_result": l4_gate_result,
        **semantic_review,
        **visual,
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
    keyframe_sheet = result["keyframe_sheet"] or "未生成"
    max_delta_pair_sheet = result["max_delta_pair_sheet"] or "未生成"
    semantic_errors = "\n".join(f"- {item}" for item in result["semantic_review_errors"]) or "- 无"
    semantic_checks = "\n".join(
        f"| {key} | {value or '未勾选'} |" for key, value in result["semantic_review_checks"].items()
    ) or "| 未提供 | 未勾选 |"
    sample_score = result["sample_level_score"]
    sample_score_text = "未填写" if sample_score is None else f"{float(sample_score):g} / 100"
    return f"""# Walkthrough Continuity Report

项目：{result['project_id']}

## 结论

- 当前 capability level：{result['assessed_capability_level']}
- 目标 capability level：{result['expected_capability_level'] or '未声明'}
- 是否达到目标等级：{yes(result['passes_expected_level'])}
- 是否单条连续视频：{yes(result['is_single_continuous_video'])}
- 是否多 clip 拼接：{yes(result['is_multi_clip'])}
- 是否静态图运镜：{yes(result['is_static_image_motion'])}
- 素材就绪状态：{result['readiness_status']}
- 是否允许称为真正 walkthrough：{yes(result['assessed_capability_level'] in {'L3', 'L4'})}
- 是否允许称为样片级连续空间漫游：{yes(result['assessed_capability_level'] == 'L4')}
- 是否需要人工复核：{yes(result['manual_review_required'])}
- 是否需要空间语义人工复核：{yes(result['semantic_review_required'])}
- 空间语义人工复核是否通过：{yes(result['manual_semantic_review_passed'])}
- L4 基础门禁结果：{result['l4_gate_result']}
- clip 数量：{result['clip_count']}
- 图片数量：{result['image_count']}
- 视频数量：{result['video_count']}
- fade in/out 检查：{result['fade_in_out']}

## 视觉证据

- 视觉证据可用：{yes(result['visual_evidence_available'])}
- 视觉证据来源：{result['visual_evidence_source']}
- 关键帧拼图：`{keyframe_sheet}`
- 最大跳变帧对：`{max_delta_pair_sheet}`
- 抽帧数量：{result['sampled_frame_count']}
- 场景跳变数量：{result['scene_change_count']}
- 平均帧差：{result['avg_frame_delta']}
- 最大帧差：{result['max_frame_delta']}
- 最大跳变帧：{result['max_delta_from_frame']} -> {result['max_delta_to_frame']}
- 硬切风险：{result['hard_cut_risk']}
- 运动连续性风险：{result['motion_continuity_risk']}
- 说明：{result['visual_evidence_note']}

## 人工空间语义复核

- 复核文件：`{result['semantic_review_file'] or '未配置'}`
- 复核文件存在：{yes(result['semantic_review_file_exists'])}
- 复核文件有效：{yes(result['semantic_review_file_valid'])}
- 人工复核人：{result['semantic_review_reviewer'] or '未填写'}
- 复核日期：{result['semantic_review_date'] or '未填写'}
- 复核结论：{result['semantic_review_conclusion'] or '未填写'}
- 源视频 hash 匹配：{yes(bool(result['semantic_review_source_hash']) and result['semantic_review_source_hash'] == result['semantic_review_expected_source_hash'])}
- 样片级专项评分：{sample_score_text}
- 样片级专项评分达标：{yes(result['sample_level_score_passed'])}
- 样片级专项评分严重不足：{yes(result['sample_level_score_severe'])}

| 复核项 | 选择 |
|---|---|
{semantic_checks}

复核问题：

{semantic_errors}

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
- 同一空间、连续视差、少硬切、材质灯光比例稳定、基础视觉门禁、有效人工空间语义复核文件和样片级专项评分 >= 85 均通过，才可能达到 L4。
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
    parser.add_argument("--keyframes-output", help="Optional keyframe contact sheet path")
    parser.add_argument("--sample-count", type=int, default=VISUAL_SAMPLE_COUNT, help="Number of frames/images to sample for visual evidence")
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
