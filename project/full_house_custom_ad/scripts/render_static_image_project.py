#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
VALIDATOR = ROOT / "scripts" / "validate_walkthrough_continuity.py"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
OUT_DIR.mkdir(parents=True, exist_ok=True)


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_resolution(value: str | None) -> tuple[int, int]:
    if not value:
        return 1080, 1920
    match = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", value)
    if not match:
        return 1080, 1920
    return int(match.group(1)), int(match.group(2))


def collect_images(path: Path | None) -> list[Path]:
    if not path or not path.exists():
        return []
    if path.is_file():
        return [path] if path.suffix.lower() in IMAGE_EXTS else []
    return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def infer_shot_type(path: Path, index: int, total: int) -> str:
    name = path.stem.lower()
    keyword_map = [
        ("entry", ["entry", "foyer", "玄关", "入户", "门厅"]),
        ("living_room_opening", ["living", "客厅", "横厅", "沙发", "open"]),
        ("tv_wall_focus", ["tv", "电视", "背景墙", "岩板"]),
        ("dining_slide", ["dining", "餐厅", "餐桌", "餐厨", "sideboard", "餐边柜"]),
        ("material_detail", ["detail", "material", "close", "材质", "细节", "灯带", "柜门", "木饰面"]),
        ("final_wide", ["wide", "final", "大景", "全景", "收尾"]),
    ]
    for shot_type, keywords in keyword_map:
        if any(keyword in name for keyword in keywords):
            return shot_type
    if index == 0:
        return "entry"
    if index == total - 1:
        return "final_wide"
    return "living_room_opening"


def shot_items_from_config(config: dict[str, Any], images: list[Path]) -> list[dict[str, Any]]:
    images_dir = resolve_path(config.get("source_images_dir"))
    raw = config.get("shots")
    items: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename", "")).strip()
            if not filename:
                continue
            path = Path(filename)
            if not path.is_absolute():
                path = (images_dir or ROOT) / path
            if not path.exists() or path.suffix.lower() not in IMAGE_EXTS:
                continue
            items.append(
                {
                    "path": path,
                    "shot_type": str(item.get("shot_type", infer_shot_type(path, index, len(raw)))),
                    "motion": str(item.get("motion", "")),
                    "label": str(item.get("label", path.stem)),
                    "duration": item.get("duration"),
                }
            )
    if items:
        return items
    return [
        {
            "path": image,
            "shot_type": infer_shot_type(image, index, len(images)),
            "motion": "",
            "label": image.stem,
            "duration": None,
        }
        for index, image in enumerate(images)
    ]


def get_duration(path: Path) -> float:
    proc = run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], check=False)
    text = "\n".join([proc.stdout, proc.stderr])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def choose_images_and_duration(config: dict[str, Any], items: list[dict[str, Any]], music: Path | None) -> tuple[list[dict[str, Any]], float, float]:
    per_image = float(config.get("per_image_duration", 4.2) or 4.2)
    requested_duration = float(config.get("duration", 0) or 0)
    music_duration = get_duration(music) if music and music.exists() else 0.0
    total = requested_duration if requested_duration > 0 else music_duration
    if total <= 0:
        total = min(len(items), 8) * per_image
    min_per_image = 2.8
    max_images = max(1, int(total // min_per_image)) if total > 0 else len(items)
    if len(items) > max_images:
        items = items[:max_images]
    duration = max(total / max(1, len(items)), min_per_image)
    total = duration * len(items)
    for item in items:
        if item.get("duration"):
            try:
                item["computed_duration"] = max(float(item["duration"]), min_per_image)
            except (TypeError, ValueError):
                item["computed_duration"] = duration
        else:
            item["computed_duration"] = duration
    total = sum(float(item["computed_duration"]) for item in items)
    return items, duration, total


def motion_profile(shot_type: str, motion: str, index: int) -> tuple[float, float, float, float, float, str]:
    key = motion or shot_type
    profiles = {
        "edge_push": (0.060, 0.08, 0.42, 0.30, 0.34, "柜体边缘推进"),
        "entry": (0.060, 0.08, 0.42, 0.30, 0.34, "玄关入口柜体边缘推进"),
        "slow_lateral_reveal": (0.050, 0.12, 0.58, 0.34, 0.34, "慢横移打开空间"),
        "living_room_opening": (0.050, 0.12, 0.58, 0.34, 0.34, "客厅大景慢横移打开"),
        "push_to_center": (0.065, 0.36, 0.45, 0.32, 0.36, "轻推主视觉"),
        "tv_wall_focus": (0.065, 0.36, 0.45, 0.32, 0.36, "电视墙主视觉轻推"),
        "dining_slide": (0.050, 0.22, 0.64, 0.36, 0.32, "横移经过餐桌"),
        "material_detail": (0.035, 0.44, 0.47, 0.42, 0.40, "材质细节小幅稳定推进"),
        "micro_push": (0.035, 0.44, 0.47, 0.42, 0.40, "小幅稳定推进"),
        "final_wide": (0.018, 0.48, 0.50, 0.35, 0.35, "收尾大景轻微定住"),
        "settle": (0.018, 0.48, 0.50, 0.35, 0.35, "轻微定住"),
    }
    if key in profiles:
        return profiles[key]
    if index % 2 == 0:
        return (0.052, 0.18, 0.55, 0.26, 0.40, "默认慢推横移")
    return (0.052, 0.55, 0.24, 0.38, 0.28, "默认反向横移")


def render_image_clip(
    item: dict[str, Any],
    dst: Path,
    width: int,
    height: int,
    fps: int,
    index: int,
    *,
    fade_to_black: bool = False,
) -> str:
    src = Path(item["path"])
    duration = float(item["computed_duration"])
    frames = max(1, int(round(duration * fps)))
    fade_out = max(0.0, duration - 0.25)
    zoom_amount, start_x, end_x, start_y, end_y, description = motion_profile(
        str(item.get("shot_type", "")), str(item.get("motion", "")), index
    )
    zoompan = (
        "zoompan="
        f"z='1+{zoom_amount:.3f}*on/{frames}':"
        f"x='(iw-iw/zoom)*({start_x:.3f}+({end_x:.3f}-{start_x:.3f})*on/{frames})':"
        f"y='(ih-ih/zoom)*({start_y:.3f}+({end_y:.3f}-{start_y:.3f})*on/{frames})':"
        f"d={frames}:s={width}x{height}:fps={fps}"
    )
    filters = [
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={width * 2}:{height * 2}",
        zoompan,
        "eq=contrast=1.055:saturation=0.88:brightness=-0.004:gamma=0.99",
        "unsharp=5:5:0.32:3:3:0.06",
    ]
    if fade_to_black:
        filters.extend(["fade=t=in:st=0:d=0.18", f"fade=t=out:st={fade_out:.2f}:d=0.25"])
    vf = ",".join(filters)
    run(
        [
            ffmpeg_exe(),
            "-y",
            "-loop",
            "1",
            "-i",
            str(src),
            "-frames:v",
            str(frames),
            "-vf",
            vf,
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(dst),
        ]
    )
    item["motion_description"] = description
    return description


def concat_clips(clips: list[Path], output_name: str, video_only: Path) -> None:
    concat_file = OUT_DIR / f"{output_name}_static_concat.txt"
    concat_file.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
    run([ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(video_only)])


def mux_music(video_only: Path, music: Path | None, final: Path, duration: float) -> str:
    if music and music.exists():
        fade_start = max(0.0, duration - 0.65)
        run(
            [
                ffmpeg_exe(),
                "-y",
                "-i",
                str(video_only),
                "-i",
                str(music),
                "-t",
                f"{duration:.2f}",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-af",
                f"afade=t=in:st=0:d=0.18,afade=t=out:st={fade_start:.2f}:d=0.65,loudnorm=I=-16:LRA=10:TP=-1.5",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                "-shortest",
                "-movflags",
                "+faststart",
                str(final),
            ]
        )
        return f"使用项目音乐：{rel(music)}。未默认循环短音乐。"
    shutil.copy2(video_only, final)
    return "无音乐版；未下载或抓取任何外部音乐。"


def make_preview(final: Path, preview: Path, duration: float, output_name: str) -> None:
    try:
        from PIL import Image
    except Exception:
        return
    frame_dir = OUT_DIR / f"{output_name}_preview_frames"
    frame_dir.mkdir(exist_ok=True)
    count = min(8, max(1, int(math.ceil(duration / 2.8))))
    start = 0.25
    end = max(start, duration - 0.25)
    frames = []
    for i in range(count):
        timestamp = start + (end - start) * i / max(1, count - 1)
        out = frame_dir / f"frame_{i:02d}.jpg"
        run([ffmpeg_exe(), "-y", "-ss", f"{timestamp:.2f}", "-i", str(final), "-frames:v", "1", "-update", "1", "-q:v", "2", str(out)], check=False)
        if not out.exists():
            continue
        with Image.open(out) as img:
            thumb = img.convert("RGB")
            thumb.thumbnail((216, 384), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (216, 384), (16, 16, 16))
            canvas.paste(thumb, ((216 - thumb.width) // 2, (384 - thumb.height) // 2))
            frames.append(canvas)
    if not frames:
        return
    rows = math.ceil(len(frames) / 4)
    sheet = Image.new("RGB", (216 * 4, 384 * rows), (16, 16, 16))
    for index, img in enumerate(frames):
        sheet.paste(img, ((index % 4) * 216, (index // 4) * 384))
    sheet.save(preview, quality=92)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_validator(config_path: Path, images_dir: Path, output_name: str) -> tuple[dict[str, Any], Path]:
    report = OUT_DIR / f"{output_name}_continuity_report.md"
    json_report = OUT_DIR / f"{output_name}_continuity_report.json"
    cmd = [
        sys.executable,
        str(VALIDATOR),
        "--config",
        str(config_path),
        "--images-dir",
        str(images_dir),
        "--source-type",
        "static_images",
        "--output",
        str(report),
        "--json-output",
        str(json_report),
    ]
    run(cmd, check=False)
    data: dict[str, Any] = {}
    if json_report.exists():
        data = json.loads(json_report.read_text(encoding="utf-8"))
    return data, report


def update_manifest(project_id: str, items: list[dict[str, Any]], music: Path | None) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    for item in items:
        image = Path(item["path"])
        key = rel(image)
        entry = manifest.setdefault(key, {})
        entry["hash"] = file_hash(image)
        entry["asset_type"] = "static_image_keyframe"
        entry["shot_type"] = str(item.get("shot_type", ""))
        entry["motion"] = str(item.get("motion") or item.get("motion_description", ""))
        entry["capability_level"] = "L1"
        entry["suitable_for_pseudo_walkthrough"] = True
        entry["suitable_for_true_walkthrough"] = False
        entry["suitable_for_sample_level_walkthrough"] = False
        entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
        entry["last_used"] = date.today().isoformat()
        entry["projects"] = sorted(set(entry.get("projects", [])) | {project_id})
        entry["style_tags"] = sorted(set(entry.get("style_tags", [])) | {"static_keyframe", "pseudo_walkthrough"})
    if music and music.exists():
        key = rel(music)
        entry = manifest.setdefault(key, {})
        entry["hash"] = file_hash(music)
        entry["asset_type"] = "music"
        entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
        entry["last_used"] = date.today().isoformat()
        entry["projects"] = sorted(set(entry.get("projects", [])) | {project_id})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(
    *,
    plan: Path,
    final: Path,
    video_only: Path,
    preview: Path,
    report: Path,
    items: list[dict[str, Any]],
    music: Path | None,
    audio_note: str,
    duration: float,
    per_image_duration: float,
    config: dict[str, Any],
) -> None:
    rows = "\n".join(
        (
            f"| {index + 1} | `{rel(Path(item['path']))}` | {item.get('shot_type', '')} | "
            f"{item.get('motion_description', item.get('motion', ''))} | {float(item['computed_duration']):.2f}s |"
        )
        for index, item in enumerate(items)
    )
    plan.write_text(
        f"""# L1 样片风格伪漫游成片记录

本次视频类型：样片风格伪漫游 / 高级静态关键帧运镜
本次 capability level：L1
素材来源：{config.get('asset_origin', '用户提供 / 本地已有')}
自动素材生成模式：{'启用' if config.get('auto_generated_assets') else '未启用'}
自动生成模式：{config.get('auto_generation_mode', '未启用')}
自动生成路径：{config.get('auto_generation_path', '未启用')}
是否发生自动降级：{'是' if config.get('auto_downgraded') else '否'}
是否允许自动降级：{'是' if config.get('allow_auto_downgrade') else '否'}
是否单条连续视频：否
是否多 clip 拼接：否
是否静态图运镜：是
是否通过连续性检查：仅通过 L1 静态图门禁
是否允许称为真正 walkthrough：否
是否允许称为样片级连续空间漫游：否
如果不能，原因是什么：素材来源是静态图片，本地运镜缺少真实连续视差和同一空间摄影机路径。

## 输入

- 项目：`{config.get('project_id', '')}`
- 图片数量：{len(items)}
- 音乐：`{rel(music) if music else '未提供'}`
- 音频处理：{audio_note}

## 运镜和调色

- 总时长：{duration:.2f} 秒
- 单图时长：{per_image_duration:.2f} 秒
- 运镜：慢推、轻微横移、中心构图收束，模拟看房氛围但不冒充真实 walkthrough。
- 调色：克制通透的高级样板间调色，低饱和暖灰，保留深色柜体重量感和暗部层次。
- 字幕：少字或无字，避免遮挡空间价值。

## 图片顺序

| 序号 | 图片 | shot_type | 运镜 | 时长 |
|---:|---|---|---|---:|
{rows}

## 样片级专项评分

样片级专项评分：不参与 L4 通过判断；静态图最高 L1。
L4 是否通过：否
不通过的原因：静态关键帧运镜没有真实连续视差、连续摄影机路径和同一空间运动证明。
降级后的正确命名：L1 样片风格伪漫游

## 输出

- 最终视频：`{rel(final)}`
- 无音乐/视频版：`{rel(video_only)}`
- 预览拼图：`{rel(preview)}`
- 连续性报告：`{rel(report)}`
- 素材记录：`{rel(MANIFEST_PATH)}`
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an L1 static-image pseudo walkthrough project.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    images_dir = resolve_path(config.get("source_images_dir"))
    images = collect_images(images_dir)
    if not images:
        print("没有找到静态图片素材，无法渲染 L1 伪漫游。", file=sys.stderr)
        return 2

    music = resolve_path(config.get("music"))
    if music and not music.exists():
        print(f"音乐不存在，将输出无指定音乐版：{music}", file=sys.stderr)
        music = None
    items = shot_items_from_config(config, images)
    items, per_image_duration, duration = choose_images_and_duration(config, items, music)
    width, height = parse_resolution(str(config.get("resolution", "1080x1920")))
    fps = int(config.get("fps", 60))
    fade_to_black = bool(config.get("fade_to_black", False))

    first_image_parent = Path(items[0]["path"]).parent
    continuity_report, report_path = run_validator(config_path, images_dir or first_image_parent, output_name)
    if continuity_report.get("assessed_capability_level") not in {"L1", "L0"}:
        print("静态图项目连续性报告异常：未被识别为 L1/L0。", file=sys.stderr)
        return 3

    tmp_clips: list[Path] = []
    for index, item in enumerate(items):
        image = Path(item["path"])
        clip = OUT_DIR / f"tmp_{output_name}_static_{index:02d}.mp4"
        print(
            f"rendering static keyframe {index + 1}/{len(items)}: {image.name} "
            f"({item.get('shot_type', '')})",
            flush=True,
        )
        render_image_clip(item, clip, width, height, fps, index, fade_to_black=fade_to_black)
        tmp_clips.append(clip)

    video_only = OUT_DIR / f"{output_name}_video_only.mp4"
    final = OUT_DIR / f"{output_name}.mp4"
    preview = OUT_DIR / f"{output_name}_preview.jpg"
    plan = OUT_DIR / f"{output_name}_plan.md"
    concat_clips(tmp_clips, output_name, video_only)
    audio_note = mux_music(video_only, music, final, duration)
    make_preview(final, preview, duration, output_name)
    update_manifest(project_id, items, music)
    write_plan(
        plan=plan,
        final=final,
        video_only=video_only,
        preview=preview,
        report=report_path,
        items=items,
        music=music,
        audio_note=audio_note,
        duration=duration,
        per_image_duration=per_image_duration,
        config=config,
    )
    print(final)
    print(preview)
    print(report_path)
    print(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
