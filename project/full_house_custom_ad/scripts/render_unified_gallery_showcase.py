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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


W, H = 1080, 1920
FPS = 60
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
PROJECT_ID = "unified_color_home_showcase_27s"
MUSIC = ROOT / "music_library/mp3/9.99 05_15 q@r.Eu _8pm RkC__ 简约风全屋定制落地实拍，统一色系的家真的干净通透，百看不腻# 全屋定制 # 简约风装修 # 现代简约 # 荆州全屋定制 # 餐边柜 [7594398841790254726].mp3"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/PingFang.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
]


@dataclass(frozen=True)
class Shot:
    image: str
    start: float
    end: float
    motion: str
    caption_cn: str
    caption_en: str
    purpose: str


SHOTS = [
    Shot(
        "assets/generated/08_entry_cabinet.png",
        0.00,
        3.40,
        "side_entry_push",
        "玄关开始，秩序先到",
        "ORDER BEGINS AT THE ENTRY",
        "从玄关柜建立统一色系和全屋定制的秩序感",
    ),
    Shot(
        "assets/generated/02_tv_wall.png",
        3.40,
        7.00,
        "low_reflection_push",
        "统一色系，才真正耐看",
        "TIMELESS TONE",
        "用客厅电视墙承接第一眼高级感",
    ),
    Shot(
        "music_library/images/douyin_7551028693230030140 [7551028693230030140]/04.webp",
        7.00,
        10.70,
        "soft_room_reveal",
        "把功能藏进墙面",
        "FUNCTION, QUIETLY BUILT IN",
        "展示书桌和柜体一体化，不做凌乱展示",
    ),
    Shot(
        "assets/generated/04_kitchen.png",
        10.70,
        15.40,
        "kitchen_gallery_slide",
        "餐厨之间，是家的秩序",
        "DINING AND KITCHEN IN ONE RHYTHM",
        "在音乐中段打开餐厨收纳和全屋统一关系",
    ),
    Shot(
        "assets/generated/07_study_bookcase.png",
        15.40,
        18.90,
        "gallery_pan",
        "空间打开，生活变轻",
        "SPACE FEELS LIGHTER",
        "高潮后用书柜和桌面延续生活方式",
    ),
    Shot(
        "music_library/images/douyin_7551028693230030140 [7551028693230030140]/03.webp",
        18.90,
        22.30,
        "quiet_bedroom_push",
        "安静，比奢华更高级",
        "QUIET IS THE NEW LUXURY",
        "用卧室和整墙柜体收住情绪",
    ),
    Shot(
        "assets/generated/11_storage_detail.png",
        22.30,
        24.90,
        "detail_rise",
        "细节，决定质感",
        "DETAILS DEFINE THE FINISH",
        "尾段能量回升时展示收纳细节",
    ),
    Shot(
        "assets/generated/09_led_detail.png",
        24.90,
        26.85,
        "light_close",
        "全屋定制，不止好看",
        "DESIGNED AS A WHOLE",
        "用灯带和材质细节做品牌感收尾",
    ),
]


def ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def pick_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 4


def get_duration(path: Path) -> float:
    proc = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            stamp = line.split("Duration:", 1)[1].split(",", 1)[0].strip()
            h, m, s = stamp.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not read duration: {path}")


def load_images() -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    for shot in SHOTS:
        path = ROOT / shot.image
        if not path.exists():
            raise FileNotFoundError(path)
        images[shot.image] = Image.open(path).convert("RGB")
    return images


def cover(img: Image.Image, zoom: float, offset_x: float, offset_y: float) -> Image.Image:
    base = max(W / img.width, H / img.height)
    scale = base * zoom
    rw = max(W, int(img.width * scale))
    rh = max(H, int(img.height * scale))
    resized = img.resize((rw, rh), Image.Resampling.LANCZOS)
    max_x = max(0, rw - W)
    max_y = max(0, rh - H)
    left = int(max_x / 2 + offset_x * max_x / 2)
    top = int(max_y / 2 + offset_y * max_y / 2)
    left = max(0, min(max_x, left))
    top = max(0, min(max_y, top))
    return resized.crop((left, top, left + W, top + H))


def motion_params(motion: str, p: float) -> tuple[float, float, float]:
    e = ease(p)
    if motion == "side_entry_push":
        return 1.11 + 0.05 * e, -0.10 + 0.18 * e, 0.02 - 0.05 * e
    if motion == "low_reflection_push":
        return 1.09 + 0.07 * e, -0.03 + 0.04 * e, 0.05 - 0.08 * e
    if motion == "soft_room_reveal":
        return 1.10, 0.09 - 0.16 * e, -0.02
    if motion == "kitchen_gallery_slide":
        return 1.12, -0.12 + 0.24 * e, 0.01 - 0.03 * e
    if motion == "gallery_pan":
        return 1.11, 0.08 - 0.18 * e, 0.02 - 0.04 * e
    if motion == "quiet_bedroom_push":
        return 1.10 + 0.045 * e, -0.04 + 0.08 * e, 0.04 - 0.05 * e
    if motion == "detail_rise":
        return 1.17 - 0.05 * e, -0.04 + 0.08 * e, 0.09 - 0.16 * e
    if motion == "light_close":
        return 1.18 - 0.04 * e, -0.08 + 0.12 * e, 0.02 - 0.06 * e
    return 1.1, 0.0, 0.0


def apply_grade(img: Image.Image, t: float, duration: float) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.10)
    img = ImageEnhance.Color(img).enhance(0.84)
    img = ImageEnhance.Sharpness(img).enhance(1.06)
    arr = np.asarray(img).astype(np.float32)

    lum = arr[..., 0:1] * 0.2126 + arr[..., 1:2] * 0.7152 + arr[..., 2:3] * 0.0722
    shadow = np.clip((96 - lum) / 96, 0, 1)
    highlight = np.clip((lum - 152) / 103, 0, 1)
    cool_shadow = np.array([218, 224, 224], dtype=np.float32)
    warm_high = np.array([255, 235, 204], dtype=np.float32)
    arr = arr * (1 - shadow * 0.05) + cool_shadow * shadow * 0.05
    arr = arr * (1 - highlight * 0.045) + warm_high * highlight * 0.045

    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((r - 0.48) / 0.62, 0, 1) * 0.13
    arr *= vignette[..., None]

    if t < 0.45:
        arr *= 0.72 + 0.28 * ease_out(t / 0.45)
    if duration - t < 0.45:
        arr *= 0.82 + 0.18 * ease((duration - t) / 0.45)

    graded = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return add_bloom(graded)


def add_bloom(img: Image.Image) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    lum = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
    mask = np.clip((lum - 178) / 80, 0, 1).astype(np.float32)
    glow = np.zeros_like(arr)
    glow[..., 0] = mask * 255
    glow[..., 1] = mask * 225
    glow[..., 2] = mask * 180
    glow_img = Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(radius=11))
    out = arr + np.asarray(glow_img).astype(np.float32) * 0.075
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def light_sweep(img: Image.Image, amount: float, position: float) -> Image.Image:
    if amount <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    xs = np.linspace(0, 1, W, dtype=np.float32)
    band = np.exp(-((xs - position) ** 2) / 0.004) * amount
    arr += band[None, :, None] * np.array([72, 58, 42], dtype=np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_shot(images: dict[str, Image.Image], shot: Shot, t: float, duration: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    z, ox, oy = motion_params(shot.motion, p)
    frame = cover(images[shot.image], z, ox, oy)
    if shot.motion in {"kitchen_gallery_slide", "detail_rise", "light_close"}:
        frame = light_sweep(frame, 0.16 * (1 - abs(ease(p) - 0.5)), 0.12 + 0.76 * ease(p))
    frame = apply_grade(frame, t, duration)
    return add_caption(frame, shot, t)


def active_shot(t: float) -> tuple[int, Shot]:
    for idx, shot in enumerate(SHOTS):
        if shot.start <= t < shot.end or (idx == len(SHOTS) - 1 and t <= shot.end):
            return idx, shot
    return len(SHOTS) - 1, SHOTS[-1]


def transition_frame(images: dict[str, Image.Image], idx: int, shot: Shot, t: float, duration: float) -> Image.Image:
    trans = 0.38
    if idx == 0 or t - shot.start >= trans:
        return render_shot(images, shot, t, duration)
    p = ease((t - shot.start) / trans)
    prev = SHOTS[idx - 1]
    prev_frame = render_shot(images, prev, max(prev.start, prev.end - trans + (t - shot.start)), duration)
    curr_frame = render_shot(images, shot, t, duration)
    frame = Image.blend(prev_frame, curr_frame, p)
    frame = light_sweep(frame, 0.34 * np.sin(np.pi * p), p)
    return frame


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: int) -> float:
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(draw: ImageDraw.ImageDraw, text: str, center_x: int, y: int, font: ImageFont.ImageFont, fill, tracking: int) -> None:
    total = text_width(draw, text, font, tracking)
    x = center_x - total / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def add_caption(frame: Image.Image, shot: Shot, t: float) -> Image.Image:
    local = t - shot.start
    remaining = shot.end - t
    fade = ease(min(local / 0.32, remaining / 0.32, 1.0))
    if fade <= 0:
        return frame
    alpha = int(220 * fade)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(1330, H):
        a = int(((y - 1330) / (H - 1330)) ** 1.8 * 82 * fade)
        draw.line((0, y, W, y), fill=(0, 0, 0, a))

    cn_font = pick_font(41)
    en_font = pick_font(20)
    y0 = 1412
    bbox = draw.textbbox((0, 0), shot.caption_cn, font=cn_font)
    cn_x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((cn_x + 2, y0 + 2), shot.caption_cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.42)))
    draw.text((cn_x, y0), shot.caption_cn, font=cn_font, fill=(246, 242, 235, alpha))
    draw_tracked(draw, shot.caption_en, W // 2 + 1, y0 + 66 + 1, en_font, (0, 0, 0, int(alpha * 0.35)), 4)
    draw_tracked(draw, shot.caption_en, W // 2, y0 + 66, en_font, (230, 226, 218, int(alpha * 0.84)), 4)
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def render_video(video_only: Path, duration: float) -> None:
    images = load_images()
    encode = subprocess.Popen(
        [
            ffmpeg_exe(),
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
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert encode.stdin is not None
    total = int(round(duration * FPS))
    for idx in range(total):
        t = idx / FPS
        shot_idx, shot = active_shot(t)
        frame = transition_frame(images, shot_idx, shot, t, duration)
        encode.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if idx % 180 == 0:
            print(f"processed {idx}/{total} frames", flush=True)
    encode.stdin.close()
    stderr = encode.stderr.read().decode("utf-8", errors="replace") if encode.stderr else ""
    encode.wait()
    if encode.returncode != 0:
        raise RuntimeError(stderr)


def mux_audio(video_only: Path, final: Path, duration: float) -> None:
    fade_out_start = max(0.0, duration - 0.55)
    proc = subprocess.run(
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
            f"afade=t=in:st=0:d=0.16,afade=t=out:st={fade_out_start:.2f}:d=0.55,loudnorm=I=-16:LRA=10:TP=-1.5",
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
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)


def make_preview(final: Path, preview: Path, duration: float) -> None:
    frame_dir = OUT_DIR / "unified_gallery_frames"
    frame_dir.mkdir(exist_ok=True)
    times = np.linspace(0.6, duration - 0.7, 8)
    frames: list[Image.Image] = []
    for i, t in enumerate(times):
        out = frame_dir / f"frame_{i:02d}.jpg"
        subprocess.run(
            [ffmpeg_exe(), "-y", "-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-q:v", "2", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
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


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def bump_manifest(path: Path, updates: dict) -> None:
    manifest = load_manifest()
    rel = str(path.relative_to(ROOT)) if path.is_file() else str(path)
    entry = manifest.setdefault(rel, {})
    if path.is_file():
        entry["hash"] = file_hash(path)
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    entry.update(updates)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_manifest(duration: float) -> None:
    for shot in SHOTS:
        path = ROOT / shot.image
        bump_manifest(
            path,
            {
                "asset_type": "image",
                "space_type": shot.purpose,
                "suitable_for_showcase": True,
                "suitable_for_walkthrough": "入口" in shot.purpose or "客厅" in shot.purpose,
                "style_tags": ["modern_minimal", "unified_color", "art_gallery_home"],
            },
        )
    bump_manifest(
        MUSIC,
        {
            "asset_type": "music",
            "duration": round(duration, 2),
            "bpm_estimate": 105,
            "mood": "干净、通透、中速律动",
            "suitable_for_showcase": True,
        },
    )
    manifest = load_manifest()
    route_key = "route:unified_gallery_entry_living_kitchen_bedroom_detail"
    entry = manifest.setdefault(route_key, {})
    entry["asset_type"] = "camera_route"
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["description"] = "玄关进入，客厅打开，餐厨收纳，书房卧室，材质灯光收尾"
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f}s | {shot.image} | {shot.motion} | {shot.caption_cn} | {shot.purpose} |"
        for shot in SHOTS
    )
    plan.write_text(
        f"""# 统一色系艺术馆住宅短视频执行方案

本次视频类型：图片展示型 + 伪空间漫游式镜头语言
本次节奏模式：高级广告模式 / 舒适观看
本次视频风格：现代简约全屋定制 / 艺术馆住宅感
本次音乐方向：干净、通透、中速律动
本次画面关键词：统一色系、低饱和、木作秩序、地面反光、隐藏收纳
本次核心卖点：让客户看到统一色系的家，干净通透、耐看高级
本次原创设计点：不复用旧参考视频路线，改为玄关入场、客厅打开、餐厨收纳、书房卧室、材质灯光收尾。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 时长：{duration:.2f} 秒
- 处理：完整使用，不循环；只做尾部 0.55 秒自然淡出。
- 节奏：BPM 约 105，适合舒适观看和少量段落转场。

## 素材

- 共使用 8 个镜头段落。
- 7 张素材未在 manifest 中使用过，1 张厨房图为必要空间补充。
- 不使用之前 10 秒真正漫游视频。

## 分镜

| 时间 | 素材 | 运镜 | 字幕 | 目的 |
|---|---|---|---|---|
{rows}

## 滤镜

- 低饱和暖灰。
- 柔和高光，干净阴影。
- 灯带轻微 bloom。
- 地面反光保持通透。
- 材质清晰但不过度锐化。

## 输出

- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> None:
    duration = min(get_duration(MUSIC), SHOTS[-1].end)
    video_only = OUT_DIR / "unified_gallery_showcase_27s_video_only.mp4"
    final = OUT_DIR / "unified_gallery_showcase_27s.mp4"
    preview = OUT_DIR / "unified_gallery_showcase_27s_preview.jpg"
    plan = OUT_DIR / "unified_gallery_showcase_27s_plan.md"
    render_video(video_only, duration)
    mux_audio(video_only, final, duration)
    make_preview(final, preview, duration)
    update_manifest(duration)
    write_plan(plan, final, preview, duration)
    print(final)
    print(video_only)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
