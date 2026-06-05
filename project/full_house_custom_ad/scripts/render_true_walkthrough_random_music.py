#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import random
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
SOURCE_VIDEO = ROOT / "music_library/video/3.87 QXZ__ 05_26 _3pm y@G.II 不愧是意式极简，140㎡大平层装完有点高攀不起了 # 全案设计全案落地 # 设计案例分享 # 大平层 # 爱生活爱设计 # 空间美学 [7618904456465337650]_副本.mp4"
MUSIC_DIR = ROOT / "music_library/mp3"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
OUTPUT_STEM = "true_walkthrough_random_music_10s"
PROJECT_ID = "true_walkthrough_random_music"

OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class MusicAnalysis:
    path: Path
    duration: float
    bpm: int
    climax: float
    peak_times: tuple[float, ...]
    mood: str
    rhythm: str
    visual_fit: str


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)


def get_duration(path: Path) -> float:
    proc = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            h, m, s = stamp.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not read duration: {path}")


def decode_audio(path: Path, sample_rate: int = 22050) -> np.ndarray:
    proc = subprocess.run(
        [
            ffmpeg_exe(),
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    audio = np.frombuffer(proc.stdout, dtype=np.float32)
    if audio.size == 0:
        raise RuntimeError(f"Could not decode audio: {path}")
    return np.nan_to_num(audio)


def smooth(values: np.ndarray, width: int) -> np.ndarray:
    width = max(1, int(width))
    if width <= 1:
        return values
    kernel = np.ones(width, dtype=np.float32) / width
    return np.convolve(values, kernel, mode="same")


def audio_envelope(samples: np.ndarray, sample_rate: int = 22050) -> tuple[np.ndarray, float]:
    hop = int(sample_rate * 0.05)
    win = int(sample_rate * 0.12)
    if samples.size < win:
        rms = np.array([float(np.sqrt(np.mean(samples * samples)))], dtype=np.float32)
        return rms, 0.05
    frames = []
    for start in range(0, samples.size - win, hop):
        chunk = samples[start : start + win]
        frames.append(float(np.sqrt(np.mean(chunk * chunk))))
    envelope = np.array(frames, dtype=np.float32)
    envelope = smooth(envelope, 7)
    return envelope, hop / sample_rate


def estimate_bpm(envelope: np.ndarray, step: float) -> int:
    onset = np.diff(envelope, prepend=envelope[0])
    onset = np.maximum(onset, 0)
    onset = onset - float(onset.mean())
    best_bpm = 96
    best_score = -1.0
    for bpm in range(72, 181):
        lag = int(round((60.0 / bpm) / step))
        if lag < 2 or lag >= onset.size // 2:
            continue
        score = float(np.dot(onset[:-lag], onset[lag:]))
        if score > best_score:
            best_score = score
            best_bpm = bpm
    return best_bpm


def classify_music(path: Path, bpm: int, envelope: np.ndarray) -> tuple[str, str, str]:
    name = path.name
    energy = float(np.percentile(envelope, 82) / max(np.percentile(envelope, 35), 1e-6))
    if "餐边柜" in name:
        mood = "干净、精致、偏工艺细节"
        fit = "适合餐边柜、柜体细节和克制的高级展示"
    elif "儿童房" in name:
        mood = "轻快、生活化、带一点活力"
        fit = "适合卧室、儿童房和收纳系统展示"
    elif "意式极简" in name or "大平层" in name or "空间美学" in name:
        mood = "高级、克制、偏豪宅样板间"
        fit = "适合大平层、客厅、电视墙和连续看房镜头"
    elif "高级感" in name:
        mood = "沉稳、设计感、材质导向"
        fit = "适合柜体、灯带、玻璃柜门和材质特写"
    else:
        mood = "现代、干净、适合装修案例展示"
        fit = "适合全屋定制和空间展示"

    if bpm >= 145:
        rhythm = "节奏偏快，镜头要稳，不能追每个鼓点"
    elif bpm >= 105:
        rhythm = "中速律动，适合慢推进和自然揭示"
    else:
        rhythm = "舒缓留白，适合低机位慢走和长镜头"
    if energy > 2.2:
        rhythm += "；能量起伏明显，高潮处适合打开主空间"
    else:
        rhythm += "；能量较平滑，适合一镜到底的沉浸感"
    return mood, rhythm, fit


def analyze_music(path: Path) -> MusicAnalysis:
    duration = get_duration(path)
    sample_rate = 22050
    samples = decode_audio(path, sample_rate)
    envelope, step = audio_envelope(samples, sample_rate)
    bpm = estimate_bpm(envelope, step)

    if envelope.size:
        climax_idx = int(np.argmax(envelope))
        climax = min(duration, climax_idx * step)
        top_count = min(4, envelope.size)
        top = np.argpartition(envelope, -top_count)[-top_count:]
        peak_times = tuple(sorted(round(min(duration, int(i) * step), 2) for i in top))
    else:
        climax = duration * 0.68
        peak_times = (round(climax, 2),)

    mood, rhythm, fit = classify_music(path, bpm, envelope)
    return MusicAnalysis(
        path=path,
        duration=duration,
        bpm=bpm,
        climax=round(climax, 2),
        peak_times=peak_times,
        mood=mood,
        rhythm=rhythm,
        visual_fit=fit,
    )


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def music_usage(manifest: dict, path: Path) -> int:
    rel = str(path.relative_to(ROOT))
    return int(manifest.get(rel, {}).get("usage_count", 0))


def choose_random_music(video_duration: float) -> MusicAnalysis:
    candidates = sorted(MUSIC_DIR.glob("*.mp3"))
    if not candidates:
        raise FileNotFoundError(f"No music files in {MUSIC_DIR}")
    manifest = load_manifest()
    durations = [(path, get_duration(path)) for path in candidates]

    # True walkthrough needs enough time to enter, reveal, and settle.
    compatible = [(p, d) for p, d in durations if 8.0 <= d <= max(12.5, video_duration + 1.0)]
    pool = compatible or durations
    min_usage = min(music_usage(manifest, p) for p, _ in pool)
    fresh_pool = [(p, d) for p, d in pool if music_usage(manifest, p) == min_usage]
    selected, _ = random.SystemRandom().choice(fresh_pool)
    return analyze_music(selected)


def render_video(selected: MusicAnalysis, target_duration: float, final: Path) -> None:
    fade_out_start = max(0.0, target_duration - 0.48)
    video_filter = ",".join(
        [
            f"scale={W}:{H}:flags=lanczos",
            f"fps={FPS}",
            "eq=contrast=1.09:saturation=0.88:brightness=0.006:gamma=0.98",
            "unsharp=5:5:0.55:3:3:0.10",
            "vignette=angle=0.42:eval=frame",
            "fade=t=in:st=0:d=0.32",
            f"fade=t=out:st={fade_out_start:.2f}:d=0.48",
        ]
    )
    audio_filter = f"afade=t=in:st=0:d=0.18,afade=t=out:st={fade_out_start:.2f}:d=0.48,loudnorm=I=-16:LRA=10:TP=-1.5"
    cmd = [
        ffmpeg_exe(),
        "-y",
        "-i",
        str(SOURCE_VIDEO),
        "-i",
        str(selected.path),
        "-t",
        f"{target_duration:.2f}",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        video_filter,
        "-af",
        audio_filter,
        "-r",
        str(FPS),
        "-fps_mode",
        "cfr",
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "medium",
        "-crf",
        "18",
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
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)


def make_preview(final: Path, preview: Path, duration: float) -> None:
    frame_dir = OUT_DIR / "true_walkthrough_random_music_frames"
    frame_dir.mkdir(exist_ok=True)
    times = np.linspace(0.35, max(0.36, duration - 0.35), 8)
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


def bump_entry(manifest: dict, path: Path, updates: dict) -> None:
    rel = str(path.relative_to(ROOT))
    entry = manifest.setdefault(rel, {})
    entry["hash"] = file_hash(path)
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    entry.update(updates)


def update_manifest(selected: MusicAnalysis, video_duration: float, target_duration: float) -> None:
    manifest = load_manifest()
    bump_entry(
        manifest,
        SOURCE_VIDEO,
        {
            "asset_type": "video",
            "space_type": "true_walkthrough_living_room",
            "duration": round(video_duration, 2),
            "rendered_duration": round(target_duration, 2),
            "suitable_for_walkthrough": True,
            "suitable_for_showcase": True,
            "style_tags": ["true_walkthrough", "italian_minimal", "warm_grey", "showroom"],
        },
    )
    bump_entry(
        manifest,
        selected.path,
        {
            "asset_type": "music",
            "duration": round(selected.duration, 2),
            "bpm_estimate": selected.bpm,
            "climax_time": selected.climax,
            "mood": selected.mood,
            "rhythm": selected.rhythm,
            "suitable_for_walkthrough": True,
        },
    )
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(
    path: Path,
    selected: MusicAnalysis,
    video_duration: float,
    target_duration: float,
    final: Path,
    preview: Path,
) -> None:
    if selected.duration > video_duration:
        duration_note = (
            f"音乐 {selected.duration:.2f} 秒，真实漫游素材 {video_duration:.2f} 秒；"
            f"本次保留完整连续看房镜头，音乐裁到 {target_duration:.2f} 秒，不循环。"
        )
    elif selected.duration < video_duration:
        duration_note = (
            f"音乐 {selected.duration:.2f} 秒，真实漫游素材 {video_duration:.2f} 秒；"
            f"本次按音乐时长收住视频，不循环、不拼接第二段。"
        )
    else:
        duration_note = f"音乐和真实漫游素材均约 {target_duration:.2f} 秒，直接匹配，不循环。"

    peaks = "、".join(f"{p:.2f}s" for p in selected.peak_times)
    path.write_text(
        f"""# 真正空间漫游型成片方案

本次视频类型：真正空间漫游型
本次节奏模式：高级广告模式 / 舒适看房节奏
本次视频风格：意式极简大平层 / 暖灰电影感 / 样板间 walkthrough
本次音乐方向：{selected.mood}
本次画面关键词：低机位地面反光、侧墙进入、电视墙轴线、落地窗揭示、餐厨延展、暖灰滤镜
本次核心卖点：用一个连续镜头让客户像走进高端大平层，看清空间尺度、灯光、材质和全屋定制完成度。

## 音乐分析

- 随机选中音乐：`{selected.path.relative_to(ROOT)}`
- 音乐真实时长：{selected.duration:.2f} 秒
- 估算 BPM：{selected.bpm}
- 情绪判断：{selected.mood}
- 节奏判断：{selected.rhythm}
- 高潮点：约 {selected.climax:.2f} 秒
- 能量峰值参考：{peaks}
- 画面匹配：{selected.visual_fit}

## 时长和素材判断

- 真实漫游素材：`{SOURCE_VIDEO.relative_to(ROOT)}`
- 漫游素材时长：{video_duration:.2f} 秒
- 最终成片时长：{target_duration:.2f} 秒
- 图片数量：0 张；本次不做图片轮播，使用 1 条连续视频镜头。
- 处理原则：{duration_note}

## 镜头路径

1. 0-2 秒：侧墙和柜体边缘进入，低机位带出地面反光，建立真实看房感。
2. 2-5 秒：电视墙、灯带和天花线条成为主视觉，让空间尺度被看清。
3. 5-8 秒：落地窗和沙发区打开，保留城市景观和客厅尺度。
4. 8-{target_duration:.0f} 秒：餐厨与柜体关系收尾，形成完整大平层记忆点。

## 滤镜和画质

- 低饱和暖灰电影感，避免廉价高饱和。
- 压住窗边和灯带高光，保留亮部层次。
- 暗部轻抬，黑色柜体不死黑。
- 轻微锐化柜体线条和材质纹理，但不过度锐化。
- 边缘暗角非常克制，只做视线聚焦。
- 开头和结尾使用柔和淡入淡出，避免硬切。

## 输出

- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> None:
    final = OUT_DIR / f"{OUTPUT_STEM}.mp4"
    preview = OUT_DIR / f"{OUTPUT_STEM}_preview.jpg"
    plan = OUT_DIR / f"{OUTPUT_STEM}_plan.md"

    video_duration = get_duration(SOURCE_VIDEO)
    selected = choose_random_music(video_duration)
    target_duration = round(min(video_duration, selected.duration), 2)
    if target_duration < 6.0:
        raise RuntimeError("Selected music is too short for a true walkthrough.")

    print(f"selected_music={selected.path.name}", flush=True)
    print(f"music_duration={selected.duration:.2f}s bpm={selected.bpm} climax={selected.climax:.2f}s", flush=True)
    print(f"video_duration={video_duration:.2f}s target_duration={target_duration:.2f}s", flush=True)

    render_video(selected, target_duration, final)
    make_preview(final, preview, target_duration)
    update_manifest(selected, video_duration, target_duration)
    write_plan(plan, selected, video_duration, target_duration, final, preview)

    print(final)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
