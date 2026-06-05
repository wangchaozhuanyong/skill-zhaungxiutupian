#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
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
CONTINUOUS_SOURCE_TYPES = {"real_video", "3d_walkthrough", "continuous_ai_video"}
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


def get_duration(path: Path) -> float:
    proc = run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], check=False)
    text = "\n".join([proc.stdout, proc.stderr])
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def pick_font() -> str:
    candidates = [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def drawtext_filter(text: str, start: float, end: float, y: str, size: int, font: str) -> str:
    escaped = escape_drawtext(text)
    enable = f"between(t\\,{start:.2f}\\,{end:.2f})"
    return (
        f"drawtext=fontfile={font}:text='{escaped}':x=(w-text_w)/2:y={y}:"
        f"fontsize={size}:fontcolor=F7F3EA@0.88:shadowcolor=000000@0.28:"
        f"shadowx=2:shadowy=2:enable='{enable}'"
    )


def video_filter(width: int, height: int, fps: int, subtitle_mode: str, duration: float) -> str:
    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos",
        f"crop={width}:{height}",
        f"fps={fps}",
        "setsar=1",
        "eq=contrast=1.055:saturation=0.88:brightness=-0.006:gamma=0.99",
        "unsharp=5:5:0.35:3:3:0.06",
    ]
    font = pick_font()
    if font and subtitle_mode in {"minimal", "brand"}:
        filters.append(drawtext_filter("空间缓缓打开", 0.55, min(3.20, duration), "h*0.76", 42, font))
    if font and subtitle_mode == "brand":
        start = max(0.5, duration - 3.0)
        filters.append(drawtext_filter("高级全屋定制", start, max(start + 0.5, duration - 0.25), "h*0.80", 42, font))
    return ",".join(filters)


def render_video_only(source: Path, video_only: Path, duration: float, width: int, height: int, fps: int, subtitle_mode: str) -> None:
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-i",
        str(source),
        "-t",
        f"{duration:.2f}",
        "-vf",
        video_filter(width, height, fps, subtitle_mode, duration),
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
        str(video_only),
    ]
    run(cmd)


def mux_audio(video_only: Path, source_video: Path, music: Path | None, use_source_audio: bool, final: Path, duration: float) -> str:
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
                "-movflags",
                "+faststart",
                str(final),
            ]
        )
        return f"使用项目音乐：{rel(music)}"
    if use_source_audio:
        run(
            [
                ffmpeg_exe(),
                "-y",
                "-i",
                str(video_only),
                "-i",
                str(source_video),
                "-t",
                f"{duration:.2f}",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0?",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(final),
            ]
        )
        return "使用源视频音频；如果源视频无音轨，则输出无音乐版。"
    shutil.copy2(video_only, final)
    return "无音乐版；未下载或抓取任何外部音乐。"


def make_preview(final: Path, preview: Path, duration: float, output_name: str) -> None:
    try:
        from PIL import Image
    except Exception:
        return
    frame_dir = OUT_DIR / f"{output_name}_preview_frames"
    frame_dir.mkdir(exist_ok=True)
    count = 8
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
    sheet = Image.new("RGB", (216 * 4, 384 * 2), (16, 16, 16))
    for index, img in enumerate(frames):
        sheet.paste(img, ((index % 4) * 216, (index // 4) * 384))
    sheet.save(preview, quality=92)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(
    *,
    project_id: str,
    source_video: Path,
    source_type: str,
    music: Path | None,
    duration: float,
    report: dict[str, Any],
    config: dict[str, Any],
) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    assessed = str(report.get("assessed_capability_level", ""))
    source_key = rel(source_video)
    source_entry = manifest.setdefault(source_key, {})
    source_entry["hash"] = file_hash(source_video)
    source_entry["asset_type"] = source_type
    source_entry["duration"] = round(duration, 2)
    source_entry["capability_level"] = assessed
    source_entry["suitable_for_true_walkthrough"] = L_ORDER_VALUE(assessed) >= 3
    source_entry["suitable_for_sample_level_walkthrough"] = assessed == "L4" and bool(report.get("passes_expected_level"))
    source_entry["usage_count"] = int(source_entry.get("usage_count", 0)) + 1
    source_entry["last_used"] = date.today().isoformat()
    source_entry["projects"] = sorted(set(source_entry.get("projects", [])) | {project_id})
    style = str(config.get("style", "")).strip()
    source_entry["style_tags"] = sorted(set(source_entry.get("style_tags", [])) | {tag for tag in [style, source_type, assessed] if tag})

    if music and music.exists():
        music_key = rel(music)
        music_entry = manifest.setdefault(music_key, {})
        music_entry["hash"] = file_hash(music)
        music_entry["asset_type"] = "music"
        music_entry["usage_count"] = int(music_entry.get("usage_count", 0)) + 1
        music_entry["last_used"] = date.today().isoformat()
        music_entry["projects"] = sorted(set(music_entry.get("projects", [])) | {project_id})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def L_ORDER_VALUE(level: str) -> int:
    return {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(level, 0)


def run_validator(config_path: Path, source_video: Path, source_type: str, output_name: str, allow_downgrade: bool) -> tuple[int, dict[str, Any], Path]:
    report = OUT_DIR / f"{output_name}_continuity_report.md"
    json_report = OUT_DIR / f"{output_name}_continuity_report.json"
    cmd = [
        sys.executable,
        str(VALIDATOR),
        "--config",
        str(config_path),
        "--video",
        str(source_video),
        "--source-type",
        source_type,
        "--output",
        str(report),
        "--json-output",
        str(json_report),
    ]
    if not allow_downgrade:
        cmd.append("--fail-on-overclaim")
    proc = run(cmd, check=False)
    data: dict[str, Any] = {}
    if json_report.exists():
        data = json.loads(json_report.read_text(encoding="utf-8"))
    return proc.returncode, data, report


def write_plan(
    *,
    plan: Path,
    final: Path,
    video_only: Path,
    preview: Path,
    report_path: Path,
    continuity_report: dict[str, Any],
    config: dict[str, Any],
    source_video: Path,
    music: Path | None,
    audio_note: str,
    duration: float,
    width: int,
    height: int,
    fps: int,
    source_type: str,
) -> None:
    expected = str(continuity_report.get("expected_capability_level", config.get("capability_level", "")))
    assessed = str(continuity_report.get("assessed_capability_level", ""))
    downgraded = bool(expected and assessed and L_ORDER_VALUE(assessed) < L_ORDER_VALUE(expected))
    downgrade_name = {
        "L0": "图片展示型",
        "L1": "样片风格伪漫游",
        "L2": "AI 分段空间漫游型",
        "L3": "真正空间漫游型",
        "L4": "样片级连续空间漫游型",
    }.get(assessed, "未确认")
    plan.write_text(
        f"""# 连续空间漫游成片记录

本次视频类型：{downgrade_name}
本次 capability level：{assessed or '未确认'}
是否单条连续视频：{'是' if continuity_report.get('is_single_continuous_video') else '否'}
是否多 clip 拼接：{'是' if continuity_report.get('is_multi_clip') else '否'}
是否静态图运镜：{'是' if continuity_report.get('is_static_image_motion') else '否'}
是否通过连续性检查：{'是' if continuity_report.get('passes_expected_level') else '否'}
是否允许称为真正 walkthrough：{'是' if L_ORDER_VALUE(assessed) >= 3 else '否'}
是否允许称为样片级连续空间漫游：{'是' if assessed == 'L4' else '否'}
L4 基础门禁结果：{continuity_report.get('l4_gate_result', 'not_applicable')}
是否需要空间语义人工复核：{'是' if continuity_report.get('semantic_review_required') else '否'}
空间语义人工复核是否通过：{'是' if continuity_report.get('manual_semantic_review_passed') else '否'}
是否发生降级：{'是' if downgraded else '否'}
如果不能，原因是什么：{'; '.join(continuity_report.get('reasons', [])) or '未发现阻断原因。'}

## 输入

- 项目：`{config.get('project_id', '')}`
- 源视频：`{rel(source_video)}`
- 源素材类型：`{source_type}`
- 音乐：`{rel(music) if music else '未提供'}`
- 音频处理：{audio_note}

## 后期

- 分辨率：{width} x {height}
- 帧率：{fps}
- 时长：{duration:.2f} 秒
- 调色：克制通透的高级样板间调色，低饱和暖灰，保留深色柜体重量感、暗部层次和材质清晰度，不硬提亮。
- 字幕模式：{config.get('subtitle_mode', 'none')}

## 样片级专项评分

样片级专项评分：脚本不自动给满分；必须结合 `{report_path.name}` 和人工观感复核。
L4 是否通过：{'是' if assessed == 'L4' else '否'}
不通过的原因：{'; '.join(continuity_report.get('reasons', [])) if assessed != 'L4' else '已通过 L4 基础门禁和人工空间语义复核。'}
降级后的正确命名：{downgrade_name}

## 输出

- 最终视频：`{rel(final)}`
- 无音乐/视频版：`{rel(video_only)}`
- 预览拼图：`{rel(preview)}`
- 连续性报告：`{rel(report_path)}`
- 素材记录：`{rel(MANIFEST_PATH)}`
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a continuous walkthrough project from project.json.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    parser.add_argument("--allow-downgrade", action="store_true", help="Override config allow_downgrade")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    source_video = resolve_path(config.get("source_video"))
    if not source_video or not source_video.exists():
        print("没有找到 source_video，无法渲染真正/样片级连续空间漫游。", file=sys.stderr)
        return 2

    source_type = str(config.get("source_type", "")).strip() or "real_video"
    if source_type not in CONTINUOUS_SOURCE_TYPES:
        print(f"source_type={source_type} 不是连续视频来源，不能走连续视频渲染器。", file=sys.stderr)
        return 2

    allow_downgrade = bool(config.get("allow_downgrade", False)) or args.allow_downgrade
    validation_code, continuity_report, report_path = run_validator(config_path, source_video, source_type, output_name, allow_downgrade)
    if validation_code == 3 and not allow_downgrade:
        print("连续性检查未达到目标等级，allow_downgrade=false，已停止渲染。", file=sys.stderr)
        print(report_path, file=sys.stderr)
        return 3
    if validation_code not in {0, 3}:
        return validation_code

    width, height = parse_resolution(str(config.get("resolution", "1080x1920")))
    fps = int(config.get("fps", 60))
    source_duration = get_duration(source_video)
    requested_duration = float(config.get("duration", 0) or 0)
    duration = min(source_duration, requested_duration) if requested_duration > 0 else source_duration
    if duration <= 0:
        print("无法读取源视频时长。", file=sys.stderr)
        return 2

    music = resolve_path(config.get("music"))
    if music and not music.exists():
        print(f"音乐不存在，将输出无指定音乐版：{music}", file=sys.stderr)
        music = None
    use_source_audio = bool(config.get("use_source_audio", False))
    subtitle_mode = str(config.get("subtitle_mode", "none"))
    if subtitle_mode not in {"none", "minimal", "brand"}:
        subtitle_mode = "none"

    video_only = OUT_DIR / f"{output_name}_video_only.mp4"
    final = OUT_DIR / f"{output_name}.mp4"
    preview = OUT_DIR / f"{output_name}_preview.jpg"
    plan = OUT_DIR / f"{output_name}_plan.md"

    render_video_only(source_video, video_only, duration, width, height, fps, subtitle_mode)
    audio_note = mux_audio(video_only, source_video, music, use_source_audio, final, duration)
    make_preview(final, preview, duration, output_name)
    update_manifest(
        project_id=project_id,
        source_video=source_video,
        source_type=source_type,
        music=music,
        duration=duration,
        report=continuity_report,
        config=config,
    )
    write_plan(
        plan=plan,
        final=final,
        video_only=video_only,
        preview=preview,
        report_path=report_path,
        continuity_report=continuity_report,
        config=config,
        source_video=source_video,
        music=music,
        audio_note=audio_note,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        source_type=source_type,
    )
    print(final)
    print(preview)
    print(report_path)
    print(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
