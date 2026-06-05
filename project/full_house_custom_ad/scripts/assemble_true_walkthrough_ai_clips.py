#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import imageio_ffmpeg
import numpy as np
from PIL import Image


W, H = 1080, 1920
FPS = 60
PROJECT_ID = "true_walkthrough_ai_19s"
CLIP_DIR = ROOT / "ai_clips" / "true_walkthrough_19s"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
MUSIC = ROOT / "music_library/mp3/1.74 _3pm 10_06 RKW__ M@J.vs 这种极简调性的全屋定制落地效果真的是越简单越耐看# 木作 # 空间设计美学 # 全屋定制 # 佛山全屋定制 # 门墙柜一体化 [7550252225508756770].mp3"
OUT_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class ClipSpec:
    filename: str
    duration: float
    label: str


CLIPS = [
    ClipSpec("01_entry_wall_cabinet.mp4", 3.20, "玄关门墙柜一体入场"),
    ClipSpec("02_living_room_opening.mp4", 4.00, "客厅空间打开"),
    ClipSpec("03_dining_kitchen_slide.mp4", 4.30, "餐厨横移漫游"),
    ClipSpec("04_bedroom_closet_walk.mp4", 3.00, "主卧衣柜系统"),
    ClipSpec("05_material_light_close.mp4", 4.94, "材质灯光收尾"),
]


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc


def missing_clips() -> list[Path]:
    return [CLIP_DIR / spec.filename for spec in CLIPS if not (CLIP_DIR / spec.filename).exists()]


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


def concat_clips(transcoded: list[Path], video_only: Path) -> None:
    concat_file = OUT_DIR / "true_walkthrough_ai_19s_concat.txt"
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


def mux_music(video_only: Path, final: Path, duration: float) -> None:
    fade_start = max(0.0, duration - 0.55)
    run(
        [
            ffmpeg_exe(),
            "-y",
            "-i",
            str(video_only),
            "-i",
            str(MUSIC),
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


def make_preview(final: Path, preview: Path, duration: float) -> None:
    frame_dir = OUT_DIR / "true_walkthrough_ai_19s_frames"
    frame_dir.mkdir(exist_ok=True)
    times = np.linspace(0.5, max(0.6, duration - 0.5), 8)
    frames: list[Image.Image] = []
    for i, t in enumerate(times):
        out = frame_dir / f"frame_{i:02d}.jpg"
        run([ffmpeg_exe(), "-y", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(out)])
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


def update_manifest(duration: float) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    for spec in CLIPS:
        path = CLIP_DIR / spec.filename
        rel = str(path.relative_to(ROOT))
        entry = manifest.setdefault(rel, {})
        entry["hash"] = file_hash(path)
        entry["asset_type"] = "ai_video_clip"
        entry["space_type"] = spec.label
        entry["duration"] = round(get_duration(path), 2)
        entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
        entry["last_used"] = date.today().isoformat()
        entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
        entry["suitable_for_walkthrough"] = True
        entry["style_tags"] = ["true_walkthrough", "italian_minimal", "wall_cabinet_integrated"]
    rel_music = str(MUSIC.relative_to(ROOT))
    music = manifest.setdefault(rel_music, {})
    music["hash"] = file_hash(MUSIC)
    music["asset_type"] = "music"
    music["duration"] = round(duration, 2)
    music["bpm_estimate"] = 72
    music["mood"] = "低速、克制、高级、适合慢镜头看房"
    music["usage_count"] = int(music.get("usage_count", 0)) + 1
    music["last_used"] = date.today().isoformat()
    music["projects"] = sorted(set(music.get("projects", [])) | {PROJECT_ID})
    route = manifest.setdefault("route:true_walkthrough_wall_cabinet_entry_whole_home", {})
    route["asset_type"] = "camera_route"
    route["usage_count"] = int(route.get("usage_count", 0)) + 1
    route["last_used"] = date.today().isoformat()
    route["description"] = "门墙柜一体玄关入场，客厅打开，餐厨横移，主卧衣柜，材质灯光收尾"
    route["projects"] = sorted(set(route.get("projects", [])) | {PROJECT_ID})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(f"| {spec.filename} | {spec.duration:.2f}s | {spec.label} |" for spec in CLIPS)
    plan.write_text(
        f"""# 真正空间漫游型成片记录

本次视频类型：真正空间漫游型
本次节奏模式：舒适观看 / 高级广告模式
本次视频风格：意式极简木作 / 门墙柜一体 / 艺术馆住宅感
本次音乐方向：低速、克制、高级、适合慢镜头看房
本次原创设计点：门墙柜一体化入户动线，不复用旧参考视频路线。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 成片时长：{duration:.2f} 秒
- 处理：完整使用音乐，只做自然淡出。

## 连续镜头

| 文件 | 目标时长 | 空间 |
|---|---:|---|
{rows}

## 输出

- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> int:
    missing = missing_clips()
    if missing:
        print("缺少以下 AI 连续镜头，暂时不能合成真正空间漫游成片：")
        for path in missing:
            print(f"- {path}")
        print("\n请先按 output/true_walkthrough_ai_clip_package_19s.md 生成这些 mp4。")
        return 2

    duration = sum(spec.duration for spec in CLIPS)
    transcoded: list[Path] = []
    for spec in CLIPS:
        src = CLIP_DIR / spec.filename
        dst = OUT_DIR / f"tmp_{spec.filename}"
        print(f"transcoding {spec.filename}", flush=True)
        transcode_clip(src, dst, spec.duration)
        transcoded.append(dst)

    video_only = OUT_DIR / "true_walkthrough_ai_19s_video_only.mp4"
    final = OUT_DIR / "true_walkthrough_ai_19s.mp4"
    preview = OUT_DIR / "true_walkthrough_ai_19s_preview.jpg"
    plan = OUT_DIR / "true_walkthrough_ai_19s_plan.md"
    concat_clips(transcoded, video_only)
    mux_music(video_only, final, duration)
    make_preview(final, preview, duration)
    update_manifest(duration)
    write_plan(plan, final, preview, duration)
    print(final)
    print(preview)
    print(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
