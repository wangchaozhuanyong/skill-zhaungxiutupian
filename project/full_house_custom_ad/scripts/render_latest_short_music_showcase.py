#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
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
DURATION = 12.01
ASSET_DIR = ROOT / "assets" / "generated"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
MUSIC = ROOT / "music_library/mp3/5.30 06_03 mDH__ i@c.Ag _0pm 餐边柜的高级感设计# 餐边柜 # 全屋定制 # 装修 # 设计案例分享 # 内容启发搜索 [7533166150035131706].mp3"

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
    transition: str
    caption_cn: str
    caption_en: str
    purpose: str


SHOTS = [
    Shot(
        "03_dining_sideboard.png",
        0.00,
        4.20,
        "sidewall_glide",
        "light_reveal",
        "餐边柜，藏住家的高级感",
        "QUIET LUXURY IN EVERY LINE",
        "音乐主题是餐边柜高级感，开场直接展示主卖点",
    ),
    Shot(
        "12_final_hero.png",
        4.20,
        8.25,
        "low_reflection_push",
        "ceiling_line_match",
        "从一面柜，到一个家的秩序",
        "DESIGNED AS ONE",
        "在高潮附近打开全屋空间，让客户看清整体价值",
    ),
    Shot(
        "10_material_detail.png",
        8.25,
        12.01,
        "material_reveal",
        "soft_bloom_fade",
        "材质，决定第一眼质感",
        "MATERIALS SPEAK FIRST",
        "用材质近景和品牌感收住，不突然结束",
    ),
]


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 4


def pick_font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def load_assets() -> dict[str, Image.Image]:
    assets: dict[str, Image.Image] = {}
    for shot in SHOTS:
        path = ASSET_DIR / shot.image
        if not path.exists():
            raise FileNotFoundError(path)
        assets[shot.image] = Image.open(path).convert("RGB")
    return assets


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
    if motion == "sidewall_glide":
        return 1.12, -0.10 + 0.20 * e, -0.03 + 0.04 * e
    if motion == "low_reflection_push":
        return 1.10 + 0.08 * e, -0.03 + 0.05 * e, 0.05 - 0.08 * e
    if motion == "material_reveal":
        return 1.18 - 0.05 * e, -0.09 + 0.12 * e, 0.05 - 0.08 * e
    return 1.1, 0.0, 0.0


def apply_grade(img: Image.Image, t: float) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.14)
    img = ImageEnhance.Color(img).enhance(0.86)
    img = ImageEnhance.Sharpness(img).enhance(1.08)
    arr = np.asarray(img).astype(np.float32)

    lum = arr[..., 0:1] * 0.2126 + arr[..., 1:2] * 0.7152 + arr[..., 2:3] * 0.0722
    shadow = np.clip((100 - lum) / 100, 0, 1)
    highlight = np.clip((lum - 145) / 110, 0, 1)
    cool_shadow = np.array([220, 226, 226], dtype=np.float32)
    warm_high = np.array([255, 234, 205], dtype=np.float32)
    arr = arr * (1 - shadow * 0.055) + cool_shadow * shadow * 0.055
    arr = arr * (1 - highlight * 0.04) + warm_high * highlight * 0.04

    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((r - 0.45) / 0.62, 0, 1) * 0.16
    arr *= vignette[..., None]

    if t < 0.45:
        arr *= 0.76 + 0.24 * ease_out(t / 0.45)
    if t > DURATION - 0.55:
        arr *= 1.0 + 0.025 * ease((t - (DURATION - 0.55)) / 0.55)

    graded = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return add_bloom(graded)


def add_bloom(img: Image.Image) -> Image.Image:
    arr = np.asarray(img).astype(np.float32)
    lum = arr[..., 0] * 0.2126 + arr[..., 1] * 0.7152 + arr[..., 2] * 0.0722
    mask = np.clip((lum - 176) / 80, 0, 1).astype(np.float32)
    glow = np.zeros_like(arr)
    glow[..., 0] = mask * 255
    glow[..., 1] = mask * 222
    glow[..., 2] = mask * 170
    glow_img = Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(radius=10))
    glow_arr = np.asarray(glow_img).astype(np.float32)
    out = arr + glow_arr * 0.08
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def light_sweep(img: Image.Image, amount: float, position: float) -> Image.Image:
    amount = max(0.0, min(1.0, amount))
    if amount <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    xs = np.linspace(0, 1, W, dtype=np.float32)
    band = np.exp(-((xs - position) ** 2) / 0.004) * amount
    arr += band[None, :, None] * np.array([70, 58, 42], dtype=np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_shot(assets: dict[str, Image.Image], shot: Shot, t: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    z, ox, oy = motion_params(shot.motion, p)
    frame = cover(assets[shot.image], z, ox, oy)
    if shot.motion in {"low_reflection_push", "material_reveal"}:
        frame = light_sweep(frame, 0.18 * (1 - abs(ease(p) - 0.5)), 0.12 + 0.76 * ease(p))
    return apply_grade(frame, t)


def active_shot(t: float) -> tuple[int, Shot]:
    for idx, shot in enumerate(SHOTS):
        if shot.start <= t < shot.end or (idx == len(SHOTS) - 1 and t <= shot.end):
            return idx, shot
    return len(SHOTS) - 1, SHOTS[-1]


def transition_frame(assets: dict[str, Image.Image], idx: int, shot: Shot, t: float) -> Image.Image:
    trans = 0.34
    if idx == 0 or t - shot.start >= trans:
        return render_shot(assets, shot, t)
    p = ease((t - shot.start) / trans)
    prev = SHOTS[idx - 1]
    prev_frame = render_shot(assets, prev, max(prev.start, prev.end - trans + (t - shot.start)))
    curr_frame = render_shot(assets, shot, t)
    frame = Image.blend(prev_frame, curr_frame, p)
    if shot.transition in {"light_reveal", "soft_bloom_fade"}:
        frame = light_sweep(frame, 0.42 * math.sin(math.pi * p), p)
    elif shot.transition == "ceiling_line_match":
        frame = frame.filter(ImageFilter.GaussianBlur(radius=max(0.0, 0.7 - abs(p - 0.5) * 1.4)))
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


def add_caption(img: Image.Image, shot: Shot, t: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    fade = ease(max(0.0, min(p / 0.18, (1 - p) / 0.18, 1.0)))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    shade_h = 420
    for y in range(H - shade_h, H):
        alpha = int(((y - (H - shade_h)) / shade_h) ** 1.7 * 118)
        draw.line((0, y, W, y), fill=(0, 0, 0, alpha))

    final = shot == SHOTS[-1]
    cn_font = pick_font(46 if not final else 54)
    en_font = pick_font(24 if not final else 29)
    small_font = pick_font(20)
    alpha = int(232 * fade)
    y = 1398 if not final else 1340

    cn_bbox = draw.textbbox((0, 0), shot.caption_cn, font=cn_font)
    cn_x = (W - (cn_bbox[2] - cn_bbox[0])) // 2
    draw.text((cn_x + 2, y + 2), shot.caption_cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.42)))
    draw.text((cn_x, y), shot.caption_cn, font=cn_font, fill=(246, 242, 235, alpha))
    draw_tracked(draw, shot.caption_en, W // 2 + 2, y + 70 + 2, en_font, (0, 0, 0, int(alpha * 0.35)), 4)
    draw_tracked(draw, shot.caption_en, W // 2, y + 70, en_font, (232, 228, 218, int(alpha * 0.92)), 4)

    line_y = y + 126
    draw.line((W // 2 - 140, line_y, W // 2 + 140, line_y), fill=(232, 228, 218, int(alpha * 0.42)), width=1)
    if final:
        draw_tracked(draw, "WHOLE HOUSE CUSTOMIZATION", W // 2, line_y + 32, small_font, (232, 228, 218, int(alpha * 0.72)), 6)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def frame_at(t: float, assets: dict[str, Image.Image]) -> Image.Image:
    idx, shot = active_shot(t)
    frame = transition_frame(assets, idx, shot, t)
    return add_caption(frame, shot, t)


def run_ffmpeg(cmd: list[str], input_bytes: bytes | None = None) -> None:
    proc = subprocess.run(cmd, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))


def render_video(assets: dict[str, Image.Image], silent_path: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
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
        "20",
        "-movflags",
        "+faststart",
        str(silent_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    total = int(round(DURATION * FPS))
    for idx in range(total):
        t = min(DURATION - 1 / FPS, idx / FPS)
        proc.stdin.write(np.asarray(frame_at(t, assets), dtype=np.uint8).tobytes())
        if idx % 180 == 0:
            print(f"rendered {idx}/{total} frames", flush=True)
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(stderr)


def attach_music(silent_path: Path, final_path: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(silent_path),
            "-i",
            str(MUSIC),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            f"{DURATION:.2f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final_path),
        ]
    )


def make_preview_sheet(assets: dict[str, Image.Image], path: Path) -> None:
    times = [0.5, 2.6, 4.7, 6.9, 8.8, 11.2]
    thumbs = []
    for t in times:
        frame = frame_at(t, assets)
        frame.thumbnail((270, 480), Image.Resampling.LANCZOS)
        thumbs.append(frame.copy())
    sheet = Image.new("RGB", (270 * 3, 480 * 2), (18, 18, 18))
    for idx, thumb in enumerate(thumbs):
        x = (idx % 3) * 270
        y = (idx // 3) * 480
        sheet.paste(thumb, (x, y))
    sheet.save(path, quality=92)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def update_manifest() -> None:
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = {}
    today = date.today().isoformat()
    for shot in SHOTS:
        rel = str((ASSET_DIR / shot.image).relative_to(ROOT))
        entry = manifest.setdefault(rel, {})
        entry["hash"] = file_hash(ROOT / rel)
        entry["asset_type"] = "image"
        entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
        entry["last_used"] = today
        entry["projects"] = sorted(set(entry.get("projects", [])) | {"latest_short_music_showcase"})
        entry["suitable_for_showcase"] = True
        entry["suitable_for_walkthrough"] = shot.image in {"03_dining_sideboard.png", "12_final_hero.png"}
        entry["space_type"] = {
            "03_dining_sideboard.png": "dining_sideboard",
            "12_final_hero.png": "whole_home_hero",
            "10_material_detail.png": "material_detail",
        }[shot.image]
        entry["style_tags"] = ["italian_minimal", "warm_grey", "sideboard_design"]
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_plan(path: Path) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f} | {shot.image} | {shot.motion} | {shot.transition} | {shot.caption_cn} / {shot.caption_en} | {shot.purpose} |"
        for shot in SHOTS
    )
    path.write_text(
        f"""# 最新规则短音乐高级装修视频方案

本次视频类型：图片展示型
本次节奏模式：高级广告模式
本次视频风格：意式极简豪宅 / 餐边柜高级感
本次音乐方向：本地音乐库随机抽取，餐边柜主题，节奏密集但不强卡点
本次画面关键词：餐边柜、暖灰、木饰面、隐藏灯带、岩板质感、全屋秩序
本次核心卖点：12 秒内精选 3 张图，不循环音乐，让客户看清餐边柜和整体空间高级感

## 音乐分析

- 所选音乐：`{MUSIC}`
- 真实时长：约 12.01 秒
- 估算节奏：约 180 BPM，鼓点密集
- 主要能量峰值：约 7.84 秒
- 创作判断：接近短音乐边界，不循环；精选 3 张图，每张空间图约 3.7-4.2 秒

## 类型判断

当前素材是静态图片，不具备真正连续 walkthrough。由于本次使用 3 张不同空间/细节图，因此判断为图片展示型高级广告片，而不是伪空间漫游型或真正空间漫游型。

## 分镜

| 时间 | 素材 | 运镜 | 转场 | 字幕 | 目的 |
|---|---|---|---|---|---|
{rows}

## 滤镜和画质

低饱和暖灰电影感；压住灯带高光，抬起暗部细节；轻微 bloom 让灯带更柔；保留木饰面、岩板和柜体线条清晰度；地面和台面反光保持通透。

## 输出

- 最终视频：`full_house_custom_ad/output/latest_short_music_sideboard_12s.mp4`
- 无声视频：`full_house_custom_ad/output/latest_short_music_sideboard_12s_video_only.mp4`
- 预览拼图：`full_house_custom_ad/output/latest_short_music_sideboard_12s_preview.jpg`
- 素材记录：`full_house_custom_ad/asset_manifest.json`
""",
        encoding="utf-8",
    )


def main() -> None:
    assets = load_assets()
    silent = OUT_DIR / "latest_short_music_sideboard_12s_video_only.mp4"
    final = OUT_DIR / "latest_short_music_sideboard_12s.mp4"
    preview = OUT_DIR / "latest_short_music_sideboard_12s_preview.jpg"
    plan = OUT_DIR / "latest_short_music_sideboard_12s_plan.md"

    render_video(assets, silent)
    attach_music(silent, final)
    make_preview_sheet(assets, preview)
    update_manifest()
    write_plan(plan)

    print(final)
    print(silent)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)
    print(MUSIC)


if __name__ == "__main__":
    main()
