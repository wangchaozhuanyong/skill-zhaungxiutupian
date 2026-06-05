#!/usr/bin/env python3
"""Legacy one-off renderer.

This script is kept for the earlier reference-video case. New continuous
walkthrough projects should use:

    python scripts/render_project.py --config projects/<project>/project.json

or call scripts/render_continuous_video_project.py directly.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


W, H = 1080, 1920
FPS = 60
SOURCE_VIDEO = ROOT / "music_library/video/3.87 QXZ__ 05_26 _3pm y@G.II 不愧是意式极简，140㎡大平层装完有点高攀不起了 # 全案设计全案落地 # 设计案例分享 # 大平层 # 爱生活爱设计 # 空间美学 [7618904456465337650]_副本.mp4"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
]


def pick_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def grade_frame(frame: Image.Image, t: float, duration: float) -> Image.Image:
    arr = np.asarray(frame).astype(np.float32)
    arr01 = arr / 255.0

    lum = arr01[..., 0:1] * 0.2126 + arr01[..., 1:2] * 0.7152 + arr01[..., 2:3] * 0.0722
    sat = 0.86
    arr01 = lum + (arr01 - lum) * sat
    arr01 = (arr01 - 0.5) * 1.12 + 0.5

    # Keep the reference-video warmth while preventing yellow/green cast.
    arr01[..., 0] *= 1.028
    arr01[..., 1] *= 1.005
    arr01[..., 2] *= 0.968

    # Lift shadows slightly and compress highlights for a polished showroom look.
    lum2 = arr01[..., 0:1] * 0.2126 + arr01[..., 1:2] * 0.7152 + arr01[..., 2:3] * 0.0722
    shadow = np.clip((0.34 - lum2) / 0.34, 0, 1)
    highlight = np.clip((lum2 - 0.72) / 0.28, 0, 1)
    arr01 = arr01 * (1 - shadow * 0.045) + np.array([0.54, 0.56, 0.56], dtype=np.float32) * shadow * 0.045
    arr01 = arr01 * (1 - highlight * 0.055) + np.array([0.96, 0.88, 0.75], dtype=np.float32) * highlight * 0.055

    # Gentle vignette for focus without making the room feel dark.
    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    radius = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((radius - 0.48) / 0.62, 0, 1) * 0.13
    arr01 *= vignette[..., None]

    # Soft fade in/out keeps the walkthrough from feeling abruptly cut.
    if t < 0.35:
        arr01 *= 0.76 + 0.24 * ease(t / 0.35)
    if duration - t < 0.45:
        arr01 *= 0.82 + 0.18 * ease((duration - t) / 0.45)

    graded = Image.fromarray((np.clip(arr01, 0, 1) * 255).astype(np.uint8), "RGB")
    return add_bloom_and_clarity(graded)


def add_bloom_and_clarity(img: Image.Image) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    lum = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
    mask = np.clip((lum - 178) / 78, 0, 1).astype(np.float32)
    glow = np.zeros_like(arr)
    glow[..., 0] = mask * 255
    glow[..., 1] = mask * 222
    glow[..., 2] = mask * 170
    glow_img = Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(radius=12))
    glow_arr = np.asarray(glow_img).astype(np.float32)
    out = arr + glow_arr * 0.07
    sharpened = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB").filter(
        ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=4)
    )
    return sharpened


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: int) -> float:
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: int,
    y: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    tracking: int,
) -> None:
    total = text_width(draw, text, font, tracking)
    x = center_x - total / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def add_minimal_caption(frame: Image.Image, t: float, duration: float) -> Image.Image:
    cues = [
        (0.55, 3.15, "空间，缓缓打开", "SPACE OPENS SLOWLY"),
        (duration - 2.40, duration - 0.32, "高级全屋定制", "LUXURY CUSTOM HOME"),
    ]
    active = None
    for cue in cues:
        if cue[0] <= t <= cue[1]:
            active = cue
            break
    if active is None:
        return frame

    start, end, cn, en = active
    fade = ease(max(0.0, min((t - start) / 0.28, (end - t) / 0.28, 1.0)))
    alpha = int(220 * fade)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    y0 = 1388
    for y in range(1320, H):
        a = int(((y - 1320) / (H - 1320)) ** 1.8 * 78 * fade)
        draw.line((0, y, W, y), fill=(0, 0, 0, a))

    cn_font = pick_font(42)
    en_font = pick_font(22)
    cn_bbox = draw.textbbox((0, 0), cn, font=cn_font)
    cn_x = (W - (cn_bbox[2] - cn_bbox[0])) // 2
    draw.text((cn_x + 2, y0 + 2), cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.40)))
    draw.text((cn_x, y0), cn, font=cn_font, fill=(246, 242, 235, alpha))
    draw_tracked(draw, en, W // 2 + 1, y0 + 64 + 1, en_font, (0, 0, 0, int(alpha * 0.34)), 4)
    draw_tracked(draw, en, W // 2, y0 + 64, en_font, (232, 228, 218, int(alpha * 0.86)), 4)
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def get_duration(ffmpeg: str, path: Path) -> float:
    proc = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            h, m, s = stamp.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError("Could not read duration")


def process_video(video_only: Path) -> float:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    duration = get_duration(ffmpeg, SOURCE_VIDEO)
    decode = subprocess.Popen(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(SOURCE_VIDEO),
            "-vf",
            f"fps={FPS},scale={W}:{H}:flags=lanczos",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    encode = subprocess.Popen(
        [
            ffmpeg,
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{W}x{H}",
            "-pix_fmt",
            "rgb24",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-vcodec",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "19",
            "-movflags",
            "+faststart",
            str(video_only),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert decode.stdout is not None
    assert encode.stdin is not None

    frame_bytes = W * H * 3
    idx = 0
    while True:
        raw = decode.stdout.read(frame_bytes)
        if len(raw) != frame_bytes:
            break
        t = idx / FPS
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((H, W, 3))
        frame = Image.fromarray(arr, "RGB")
        frame = grade_frame(frame, t, duration)
        frame = add_minimal_caption(frame, t, duration)
        encode.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if idx % 180 == 0:
            print(f"processed {idx} frames", flush=True)
        idx += 1

    decode.stdout.close()
    decode.wait()
    encode.stdin.close()
    stderr = encode.stderr.read().decode("utf-8", errors="replace") if encode.stderr else ""
    encode.wait()
    if encode.returncode != 0:
        raise RuntimeError(stderr)
    return duration


def mux_audio(video_only: Path, final: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_only),
            "-i",
            str(SOURCE_VIDEO),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))


def make_preview(final: Path, preview: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_dir = OUT_DIR / "true_walkthrough_frames"
    tmp_dir.mkdir(exist_ok=True)
    times = [0.3, 1.4, 2.7, 4.0, 5.4, 6.8, 8.1, 9.6]
    frames: list[Image.Image] = []
    for i, t in enumerate(times):
        out = tmp_dir / f"frame_{i:02d}.jpg"
        subprocess.run(
            [ffmpeg, "-y", "-ss", str(t), "-i", str(final), "-frames:v", "1", "-q:v", "2", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        img = Image.open(out).convert("RGB")
        img.thumbnail((216, 384), Image.Resampling.LANCZOS)
        frames.append(img.copy())
    sheet = Image.new("RGB", (216 * 4, 384 * 2), (18, 18, 18))
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
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = {}
    rel = str(SOURCE_VIDEO.relative_to(ROOT))
    entry = manifest.setdefault(rel, {})
    entry["hash"] = file_hash(SOURCE_VIDEO)
    entry["asset_type"] = "video"
    entry["space_type"] = "true_walkthrough_living_room"
    entry["duration"] = round(duration, 2)
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["projects"] = sorted(set(entry.get("projects", [])) | {"true_walkthrough_enhanced"})
    entry["suitable_for_walkthrough"] = True
    entry["suitable_for_showcase"] = True
    entry["style_tags"] = ["true_walkthrough", "italian_minimal", "warm_grey", "showroom"]
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(path: Path, duration: float) -> None:
    path.write_text(
        f"""# 真正空间漫游型视频方案

本次视频类型：真正空间漫游型
本次节奏模式：高级广告模式
本次视频风格：意式极简豪宅 / 样板间 walkthrough
本次音乐方向：使用真实视频原声，不循环
本次画面关键词：低机位、地面反光、天花线条、电视墙、落地窗、暖灰滤镜
本次核心卖点：用连续镜头制造高级看房体验，让客户像走进大平层空间

## 类型判断

本次使用真实竖屏视频素材，而不是静态图片，因此符合真正空间漫游型标准。镜头具备连续移动路径：侧墙/柜体边缘进入，沿电视墙和地面反光打开客厅，再带出落地窗、沙发区和餐厨空间。

## 音乐和时长

- 视频原始时长：约 {duration:.2f} 秒
- 音频处理：保留原声，不循环、不强行延长
- 节奏处理：连续镜头为主，字幕极少，音乐只做氛围承托

## 摄影机路径

1. 0-2 秒：从侧墙和地面反光进入空间，建立高级看房感。
2. 2-5 秒：电视墙、灯带和天花线条成为主视觉。
3. 5-8 秒：落地窗打开空间尺度，带出沙发区和城市景观。
4. 8-10 秒：餐厨与柜体空间收尾，保留完整空间记忆点。

## 滤镜和画质

- 低饱和暖灰电影感。
- 压住灯带和窗边高光。
- 抬起暗部细节，黑色不死黑。
- 灯带和窗光轻微 bloom。
- 提升地面反光通透度和材质清晰度。
- 少字字幕，不遮挡核心空间。

## 输出

- 最终视频：`full_house_custom_ad/output/true_walkthrough_enhanced_10s.mp4`
- 无声视频：`full_house_custom_ad/output/true_walkthrough_enhanced_10s_video_only.mp4`
- 预览拼图：`full_house_custom_ad/output/true_walkthrough_enhanced_10s_preview.jpg`
- 素材记录：`full_house_custom_ad/asset_manifest.json`
""",
        encoding="utf-8",
    )


def main() -> None:
    video_only = OUT_DIR / "true_walkthrough_enhanced_10s_video_only.mp4"
    final = OUT_DIR / "true_walkthrough_enhanced_10s.mp4"
    preview = OUT_DIR / "true_walkthrough_enhanced_10s_preview.jpg"
    plan = OUT_DIR / "true_walkthrough_enhanced_10s_plan.md"

    duration = process_video(video_only)
    mux_audio(video_only, final)
    make_preview(final, preview)
    update_manifest(duration)
    write_plan(plan, duration)

    print(final)
    print(video_only)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)
    print(SOURCE_VIDEO)


if __name__ == "__main__":
    main()
