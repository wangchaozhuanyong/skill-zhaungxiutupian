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
PROJECT_ID = "italian_suite_wardrobe_22s"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
ASSET_DIR = ROOT / "assets/generated/italian_suite_22s"
MUSIC = ROOT / "music_library/mp3/6.41 qre__ N@w.FH 08_23 _6pm 高级感-意式极简衣柜细节设计分享 深色意式柜门＋树瘤科技背板＋渐变玻璃柜门的搭配 地柜＋吊柜设计 # 全屋定制 # 成都全屋定制 # 装修 # [7559891112849165631].mp3"
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
        "assets/generated/italian_suite_22s/01_entry_reveal.png",
        0.00,
        3.10,
        "dark_entry_push",
        "高级感，从进门开始",
        "QUIET LUXURY BEGINS HERE",
        "主卧入口暗部进入，建立酒店套房氛围",
    ),
    Shot(
        "assets/generated/italian_suite_22s/02_master_suite_full.png",
        3.10,
        6.40,
        "low_suite_push",
        "深色柜体，更显克制",
        "DARK TONES, QUIETLY REFINED",
        "展示主卧尺度、整墙柜和地面反光",
    ),
    Shot(
        "assets/generated/italian_suite_22s/03_wardrobe_wall.png",
        6.40,
        9.60,
        "wardrobe_slide",
        "门墙柜一体，才是真整体",
        "DESIGNED AS A WHOLE",
        "展示深色意式衣柜系统和门墙柜一体化",
    ),
    Shot(
        "assets/generated/italian_suite_22s/04_walk_in_closet_depth.png",
        9.60,
        13.30,
        "closet_depth_push",
        "打开柜门，就是生活质感",
        "A PRIVATE WARDROBE RITUAL",
        "进入衣帽间纵深，承接音乐高潮",
    ),
    Shot(
        "assets/generated/italian_suite_22s/05_burl_glass_detail.png",
        13.30,
        16.20,
        "material_close",
        "细节，决定贵气",
        "DETAILS DEFINE THE FINISH",
        "展示树瘤科技木背板、渐变玻璃和灯带",
    ),
    Shot(
        "assets/generated/italian_suite_22s/06_drawer_storage_detail.png",
        16.20,
        19.30,
        "drawer_rise",
        "好看，也要好用",
        "BEAUTY WITH FUNCTION",
        "展示抽屉收纳、五金和柜体功能价值",
    ),
    Shot(
        "assets/generated/italian_suite_22s/07_final_hero.png",
        19.30,
        22.20,
        "final_hero_settle",
        "全屋定制，不止一面柜",
        "MORE THAN A WARDROBE",
        "主卧与衣柜系统一体化收尾，形成记忆点",
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
    if motion == "dark_entry_push":
        return 1.10 + 0.06 * e, -0.10 + 0.18 * e, 0.02 - 0.06 * e
    if motion == "low_suite_push":
        return 1.08 + 0.055 * e, -0.04 + 0.08 * e, 0.06 - 0.07 * e
    if motion == "wardrobe_slide":
        return 1.12, -0.14 + 0.25 * e, 0.00 - 0.03 * e
    if motion == "closet_depth_push":
        return 1.09 + 0.075 * e, -0.06 + 0.11 * e, 0.03 - 0.07 * e
    if motion == "material_close":
        return 1.17 - 0.04 * e, 0.06 - 0.12 * e, 0.03 - 0.05 * e
    if motion == "drawer_rise":
        return 1.15 - 0.035 * e, -0.04 + 0.08 * e, 0.10 - 0.17 * e
    if motion == "final_hero_settle":
        return 1.13 - 0.035 * e, 0.04 - 0.08 * e, 0.02 - 0.04 * e
    return 1.1, 0.0, 0.0


def add_bloom(img: Image.Image) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    lum = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
    mask = np.clip((lum - 184) / 78, 0, 1).astype(np.float32)
    glow = np.zeros_like(arr)
    glow[..., 0] = mask * 255
    glow[..., 1] = mask * 212
    glow[..., 2] = mask * 165
    glow_img = Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8), "RGB").filter(
        ImageFilter.GaussianBlur(radius=11)
    )
    out = arr + np.asarray(glow_img).astype(np.float32) * 0.055
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def apply_grade(img: Image.Image, t: float, duration: float) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(1.02)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(0.84)
    img = ImageEnhance.Sharpness(img).enhance(1.04)
    arr = np.asarray(img).astype(np.float32)

    lum = arr[..., 0:1] * 0.2126 + arr[..., 1:2] * 0.7152 + arr[..., 2:3] * 0.0722
    shadow = np.clip((96 - lum) / 96, 0, 1)
    highlight = np.clip((lum - 150) / 106, 0, 1)
    cool_shadow = np.array([214, 216, 212], dtype=np.float32)
    warm_high = np.array([255, 226, 180], dtype=np.float32)
    arr = arr * (1 - shadow * 0.060) + cool_shadow * shadow * 0.060
    arr += shadow * 4.0
    arr = arr * (1 - highlight * 0.045) + warm_high * highlight * 0.045

    arr01 = np.clip(arr / 255.0, 0, 1)
    arr = np.power(arr01, 0.98) * 255.0

    avg_lum = float((arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722).mean())
    if avg_lum < 90:
        lift = min(6.0, (90 - avg_lum) * 0.30)
        arr += lift

    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((r - 0.50) / 0.70, 0, 1) * 0.085
    arr *= vignette[..., None]

    # Subtle deterministic film texture keeps the AI image from feeling too flat.
    grain = (np.sin(xx * 0.91 + yy * 0.37 + t * 19.0) + np.sin(xx * 0.19 + yy * 1.13)) * 0.9
    arr += grain[..., None]

    if t < 0.45:
        arr *= 0.74 + 0.26 * ease_out(t / 0.45)
    if duration - t < 0.55:
        arr *= 0.86 + 0.14 * ease((duration - t) / 0.55)

    graded = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return add_bloom(graded)


def light_sweep(img: Image.Image, amount: float, position: float) -> Image.Image:
    if amount <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    xs = np.linspace(0, 1, W, dtype=np.float32)
    band = np.exp(-((xs - position) ** 2) / 0.0038) * amount
    arr += band[None, :, None] * np.array([84, 58, 30], dtype=np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_shot(images: dict[str, Image.Image], shot: Shot, t: float, duration: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    z, ox, oy = motion_params(shot.motion, p)
    frame = cover(images[shot.image], z, ox, oy)
    if shot.motion in {"closet_depth_push", "material_close", "drawer_rise"}:
        frame = light_sweep(frame, 0.18 * (1 - abs(ease(p) - 0.5)), 0.10 + 0.78 * ease(p))
    frame = apply_grade(frame, t, duration)
    return add_caption(frame, shot, t)


def active_shot(t: float) -> tuple[int, Shot]:
    for idx, shot in enumerate(SHOTS):
        if shot.start <= t < shot.end or (idx == len(SHOTS) - 1 and t <= shot.end):
            return idx, shot
    return len(SHOTS) - 1, SHOTS[-1]


def transition_frame(images: dict[str, Image.Image], idx: int, shot: Shot, t: float, duration: float) -> Image.Image:
    trans = 0.42
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


def add_caption(frame: Image.Image, shot: Shot, t: float) -> Image.Image:
    local = t - shot.start
    remaining = shot.end - t
    fade = ease(min(local / 0.34, remaining / 0.34, 1.0))
    if fade <= 0:
        return frame
    alpha = int(220 * fade)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(1350, H):
        a = int(((y - 1350) / (H - 1350)) ** 1.8 * 92 * fade)
        draw.line((0, y, W, y), fill=(0, 0, 0, a))

    cn_font = pick_font(40)
    en_font = pick_font(19)
    y0 = 1430
    bbox = draw.textbbox((0, 0), shot.caption_cn, font=cn_font)
    cn_x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((cn_x + 2, y0 + 2), shot.caption_cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.45)))
    draw.text((cn_x, y0), shot.caption_cn, font=cn_font, fill=(246, 239, 228, alpha))
    draw_tracked(draw, shot.caption_en, W // 2 + 1, y0 + 66 + 1, en_font, (0, 0, 0, int(alpha * 0.35)), 4)
    draw_tracked(draw, shot.caption_en, W // 2, y0 + 66, en_font, (230, 218, 202, int(alpha * 0.86)), 4)
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
    fade_out_start = max(0.0, duration - 0.62)
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
            f"afade=t=in:st=0:d=0.16,afade=t=out:st={fade_out_start:.2f}:d=0.62,loudnorm=I=-16:LRA=10:TP=-1.5",
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
    frame_dir = OUT_DIR / "italian_suite_wardrobe_frames"
    frame_dir.mkdir(exist_ok=True)
    times = np.linspace(0.55, duration - 0.65, 8)
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


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    write_manifest(manifest)


def update_manifest(duration: float) -> None:
    for shot in SHOTS:
        path = ROOT / shot.image
        bump_manifest(
            path,
            {
                "asset_type": "image",
                "space_type": shot.purpose,
                "suitable_for_showcase": True,
                "suitable_for_walkthrough": True,
                "style_tags": ["dark_italian_minimal", "hotel_suite", "wardrobe_system", "gpt_image_2"],
            },
        )
    bump_manifest(
        MUSIC,
        {
            "asset_type": "music",
            "duration": round(duration, 2),
            "climax_time": 13.12,
            "mood": "高级、克制、深色意式衣柜细节",
            "rhythm": "22秒完整结构，适合伪空间漫游与材质细节广告",
            "suitable_for_showcase": True,
            "suitable_for_walkthrough": True,
        },
    )
    manifest = load_manifest()
    route_key = "route:italian_suite_entry_bedroom_wardrobe_closet_detail"
    entry = manifest.setdefault(route_key, {})
    entry["asset_type"] = "camera_route"
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["description"] = "主卧入口暗部进入，卧室全景，整墙衣柜，衣帽间纵深，材质与收纳细节，主视觉收尾"
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    write_manifest(manifest)


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f}s | {shot.image} | {shot.motion} | {shot.caption_cn} | {shot.purpose} |"
        for shot in SHOTS
    )
    plan.write_text(
        f"""# 深色意式酒店套房衣柜系统短视频执行方案

本次视频类型：伪空间漫游型 + 图片展示型
本次节奏模式：高级广告模式 / 舒适观看
本次视频风格：深色意式极简 + 五星酒店套房感
本次音乐方向：高级、克制、带一点节奏推进
本次画面关键词：深木柜门、树瘤科技木、渐变玻璃、隐藏灯带、酒店衣帽间、低机位反光
本次核心卖点：柜体细节很贵，空间很稳，全屋定制很有质感
本次原创设计点：用 gpt-image-2 生成全新深色酒店套房衣柜系统关键帧，不复用上一条浅色统一色系路线。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 时长：{duration:.2f} 秒
- 处理：完整使用，不循环；只做尾部自然淡出。
- 高潮：约 13.12 秒，对应衣帽间和材质细节段落。

## 素材

- 7 张新图来自 gpt-image-2。
- 已复制到：`{ASSET_DIR.relative_to(ROOT)}`
- 不使用旧图片，不使用之前 10 秒参考视频。

## 分镜

| 时间 | 素材 | 运镜 | 字幕 | 目的 |
|---|---|---|---|---|
{rows}

## 滤镜

- 克制通透的高级样板间调色，清楚但不硬提亮。
- 深色柜体保留重量感，木纹、玻璃和灯带细节可见。
- 暗部只救细节，不把阴影全部抬平成灰雾。
- 暗角极轻，只做聚焦，不压暗空间。
- 灯带轻微 bloom，玻璃和地面反光柔和。

## 输出

- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> None:
    duration = min(get_duration(MUSIC), SHOTS[-1].end)
    video_only = OUT_DIR / "italian_suite_wardrobe_22s_video_only.mp4"
    final = OUT_DIR / "italian_suite_wardrobe_22s.mp4"
    preview = OUT_DIR / "italian_suite_wardrobe_22s_preview.jpg"
    plan = OUT_DIR / "italian_suite_wardrobe_22s_plan.md"
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
