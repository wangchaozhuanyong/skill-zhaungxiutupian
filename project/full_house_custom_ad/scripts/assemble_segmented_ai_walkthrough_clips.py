#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))


W, H = 1080, 1920
FPS = 60
PROJECT_ID = "segmented_ai_walkthrough_19s"
DEFAULT_CLIP_DIR = ROOT / "ai_clips" / "segmented_ai_walkthrough_19s"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
DEFAULT_MUSIC = ROOT / "music_library/mp3/1.74 _3pm 10_06 RKW__ M@J.vs 这种极简调性的全屋定制落地效果真的是越简单越耐看# 木作 # 空间设计美学 # 全屋定制 # 佛山全屋定制 # 门墙柜一体化 [7550252225508756770].mp3"
VALIDATOR = ROOT / "scripts" / "validate_walkthrough_continuity.py"
OUT_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class ClipSpec:
    filename: str
    duration: float
    label: str


DEFAULT_CLIPS = [
    ClipSpec("01_entry_wall_cabinet.mp4", 3.20, "玄关门墙柜一体入场"),
    ClipSpec("02_living_room_opening.mp4", 4.00, "客厅空间打开"),
    ClipSpec("03_dining_kitchen_slide.mp4", 4.30, "餐厨横移漫游"),
    ClipSpec("04_bedroom_closet_walk.mp4", 3.00, "柜体系统近景"),
    ClipSpec("05_material_light_close.mp4", 4.94, "材质灯光收尾"),
]


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc


def load_config(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def clips_from_config(config: dict[str, Any]) -> list[ClipSpec]:
    raw = config.get("clips", config.get("clip_specs"))
    if not isinstance(raw, list):
        return DEFAULT_CLIPS
    clips: list[ClipSpec] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename", "")).strip()
        if not filename:
            continue
        clips.append(ClipSpec(filename, float(item.get("duration", 4.0)), str(item.get("label", filename))))
    return clips or DEFAULT_CLIPS


def missing_clips(clip_dir: Path, clips: list[ClipSpec]) -> list[Path]:
    return [clip_dir / spec.filename for spec in clips if not (clip_dir / spec.filename).exists()]


def get_duration(path: Path) -> float:
    proc = run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], check=False)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            h, m, s = stamp.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not read duration: {path}")


def transcode_clip(src: Path, dst: Path, duration: float) -> None:
    fade_start = max(0.0, duration - 0.20)
    vf = ",".join(
        [
            f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
            f"crop={W}:{H}",
            f"fps={FPS}",
            "setsar=1",
            "eq=contrast=1.08:saturation=0.86:brightness=0.004:gamma=0.98",
            "unsharp=5:5:0.45:3:3:0.10",
            "fade=t=in:st=0:d=0.12",
            f"fade=t=out:st={fade_start:.2f}:d=0.20",
        ]
    )
    run(
        [
            ffmpeg_exe(),
            "-y",
            "-i",
            str(src),
            "-t",
            f"{duration:.2f}",
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


def concat_clips(transcoded: list[Path], output_name: str, video_only: Path) -> None:
    concat_file = OUT_DIR / f"{output_name}_concat.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in transcoded), encoding="utf-8")
    run(
        [
            ffmpeg_exe(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(video_only),
        ]
    )


def mux_music(video_only: Path, music: Path, final: Path, duration: float) -> None:
    fade_start = max(0.0, duration - 0.55)
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
            f"afade=t=in:st=0:d=0.16,afade=t=out:st={fade_start:.2f}:d=0.55,loudnorm=I=-16:LRA=10:TP=-1.5",
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


def make_preview(final: Path, preview: Path, duration: float, output_name: str) -> None:
    import numpy as np
    from PIL import Image

    frame_dir = OUT_DIR / f"{output_name}_frames"
    frame_dir.mkdir(exist_ok=True)
    times = np.linspace(0.5, max(0.6, duration - 0.5), 8)
    frames: list[Image.Image] = []
    for i, t in enumerate(times):
        out = frame_dir / f"frame_{i:02d}.jpg"
        run([ffmpeg_exe(), "-y", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-update", "1", "-q:v", "2", str(out)])
        img = Image.open(out).convert("RGB")
        img.thumbnail((216, 384), Image.Resampling.LANCZOS)
        frames.append(img.copy())
    sheet = Image.new("RGB", (216 * 4, 384 * 2), (16, 16, 16))
    for i, img in enumerate(frames):
        sheet.paste(img, ((i % 4) * 216, (i // 4) * 384))
    sheet.save(preview, quality=92)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(project_id: str, clip_dir: Path, music: Path, clips: list[ClipSpec], duration: float) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    for spec in clips:
        path = clip_dir / spec.filename
        rel = str(path.relative_to(ROOT))
        entry = manifest.setdefault(rel, {})
        entry["hash"] = file_hash(path)
        entry["asset_type"] = "segmented_ai_video_clip"
        entry["space_type"] = spec.label
        entry["duration"] = round(get_duration(path), 2)
        entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
        entry["last_used"] = date.today().isoformat()
        entry["projects"] = sorted(set(entry.get("projects", [])) | {project_id})
        entry["capability_level"] = "L2"
        entry["suitable_for_segmented_walkthrough"] = True
        entry["suitable_for_true_walkthrough"] = False
        entry["style_tags"] = ["segmented_ai_walkthrough", "italian_minimal", "wall_cabinet_integrated"]
    rel_music = str(music.relative_to(ROOT))
    music_entry = manifest.setdefault(rel_music, {})
    music_entry["hash"] = file_hash(music)
    music_entry["asset_type"] = "music"
    music_entry["duration"] = round(duration, 2)
    music_entry["mood"] = "低速、克制、高级、适合慢镜头看房"
    music_entry["usage_count"] = int(music_entry.get("usage_count", 0)) + 1
    music_entry["last_used"] = date.today().isoformat()
    music_entry["projects"] = sorted(set(music_entry.get("projects", [])) | {project_id})
    route = manifest.setdefault("route:segmented_ai_wall_cabinet_entry_whole_home", {})
    route["asset_type"] = "camera_route"
    route["capability_level"] = "L2"
    route["usage_count"] = int(route.get("usage_count", 0)) + 1
    route["last_used"] = date.today().isoformat()
    route["description"] = "多个 AI clip 分段拼接：门墙柜入场，客厅打开，餐厨横移，柜体近景，材质灯光收尾"
    route["projects"] = sorted(set(route.get("projects", [])) | {project_id})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_continuity_report(config_path: Path | None, project_id: str, clip_dir: Path, output_name: str) -> Path:
    report = OUT_DIR / f"{output_name}_continuity_report.md"
    cmd = [sys.executable, str(VALIDATOR), "--clips-dir", str(clip_dir), "--source-type", "segmented_ai_clips", "--project-id", project_id, "--output", str(report)]
    if config_path:
        cmd = [sys.executable, str(VALIDATOR), "--config", str(config_path), "--clips-dir", str(clip_dir), "--source-type", "segmented_ai_clips", "--output", str(report)]
    subprocess.run(cmd, check=True)
    return report


def write_plan(plan: Path, final: Path, preview: Path, report: Path, music: Path, clips: list[ClipSpec], duration: float, project_id: str, config: dict[str, Any]) -> None:
    rows = "\n".join(f"| {spec.filename} | {spec.duration:.2f}s | {spec.label} |" for spec in clips)
    plan.write_text(
        f"""# AI 分段空间漫游型成片记录

本次视频类型：AI 分段空间漫游型 / segmented AI walkthrough
本次 capability level：L2
素材来源：{config.get('asset_origin', '用户提供 / 本地已有')}
自动素材生成模式：{'启用' if config.get('auto_generated_assets') else '未启用'}
自动生成模式：{config.get('auto_generation_mode', '未启用')}
自动生成路径：{config.get('auto_generation_path', '未启用')}
是否发生自动降级：{'是' if config.get('auto_downgraded') else '否'}
是否允许自动降级：{'是' if config.get('allow_auto_downgrade') else '否'}
是否单条连续视频：否
是否多 clip 拼接：是
是否静态图运镜：否
是否通过连续性检查：默认未通过 L4；详见 continuity report
是否允许称为真正 walkthrough：否
是否允许称为样片级连续空间漫游：否
如果不能，原因是什么：多个独立 AI clip 拼接不能默认证明同一空间连续视差、材质灯光比例一致和少硬切。

本次节奏模式：舒适观看 / 高级广告模式
本次视频风格：意式极简木作 / 门墙柜一体 / 艺术馆住宅感
本次音乐方向：低速、克制、高级、适合慢镜头看房
本次原创设计点：门墙柜一体化入户动线，使用统一 Style Bible 约束多个 AI clip。

## 音乐

- 音乐：`{music.relative_to(ROOT)}`
- 成片时长：{duration:.2f} 秒
- 处理：完整使用音乐，只做自然淡出。

## 分段 AI 镜头

| 文件 | 目标时长 | 空间 |
|---|---:|---|
{rows}

## 输出

- 项目：`{project_id}`
- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 连续性报告：`{report.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble segmented AI walkthrough clips.")
    parser.add_argument("--config", help="Project JSON config")
    parser.add_argument("--clips-dir", help="Directory of AI clips")
    parser.add_argument("--music", help="Music file")
    parser.add_argument("--output-name", help="Output stem")
    parser.add_argument("--project-id", help="Project id")
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if args.config else None
    config = load_config(config_path)
    project_id = args.project_id or str(config.get("project_id", PROJECT_ID))
    clip_dir = resolve_path(args.clips_dir) or resolve_path(config.get("source_clips_dir")) or DEFAULT_CLIP_DIR
    music = resolve_path(args.music) or resolve_path(config.get("music")) or DEFAULT_MUSIC
    output_name = args.output_name or str(config.get("output_name", PROJECT_ID))
    assert clip_dir is not None and music is not None
    clips = clips_from_config(config)

    missing = missing_clips(clip_dir, clips)
    if missing:
        run_continuity_report(config_path, project_id, clip_dir, output_name)
        print("缺少以下 AI 分段镜头，暂时不能合成 AI 分段空间漫游成片：")
        for path in missing:
            print(f"- {path}")
        print("\n这些 clip 即使补齐，默认也只能标注为 L2：AI 分段空间漫游；不得默认称为真正 walkthrough。")
        return 2

    duration = sum(spec.duration for spec in clips)
    transcoded: list[Path] = []
    for spec in clips:
        src = clip_dir / spec.filename
        dst = OUT_DIR / f"tmp_{output_name}_{spec.filename}"
        print(f"transcoding {spec.filename}", flush=True)
        transcode_clip(src, dst, spec.duration)
        transcoded.append(dst)

    video_only = OUT_DIR / f"{output_name}_video_only.mp4"
    final = OUT_DIR / f"{output_name}.mp4"
    preview = OUT_DIR / f"{output_name}_preview.jpg"
    plan = OUT_DIR / f"{output_name}_plan.md"
    concat_clips(transcoded, output_name, video_only)
    mux_music(video_only, music, final, duration)
    make_preview(final, preview, duration, output_name)
    report = run_continuity_report(config_path, project_id, clip_dir, output_name)
    update_manifest(project_id, clip_dir, music, clips, duration)
    write_plan(plan, final, preview, report, music, clips, duration, project_id, config)
    print(final)
    print(preview)
    print(report)
    print(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
