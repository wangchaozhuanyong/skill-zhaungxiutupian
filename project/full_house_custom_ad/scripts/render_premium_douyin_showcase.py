#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


W, H = 1080, 1920
FPS = 60
MUSIC_LOOPS = 2
MUSIC_DURATION = 10.06
DURATION = MUSIC_DURATION * MUSIC_LOOPS
ASSET_DIR = ROOT / "assets" / "generated"
MUSIC_DIR = ROOT / "music_library"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"
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
        "12_final_hero.png",
        0.00,
        3.40,
        "hero_push",
        "light_reveal",
        "像住进样板间的家",
        "A HOME THAT FEELS LIKE A SHOWROOM",
        "先建立完整空间价值和高级看房感",
    ),
    Shot(
        "01_living_full.png",
        3.40,
        6.70,
        "slow_pull",
        "line_match",
        "空间，决定生活质感",
        "SPACE DEFINES LIFESTYLE",
        "让客户看清客厅尺度和电视墙层次",
    ),
    Shot(
        "03_dining_sideboard.png",
        6.70,
        9.90,
        "pan_right",
        "material_match",
        "全案设计，全屋成景",
        "DESIGNED AS ONE",
        "展示客餐厅一体化和餐边柜定制价值",
    ),
    Shot(
        "04_kitchen.png",
        9.90,
        12.80,
        "pan_left",
        "axis_push",
        "厨房也有高级秩序",
        "ELEGANCE IN DAILY LIVING",
        "展示厨房柜体、动线和材质统一感",
    ),
    Shot(
        "06_walk_in_closet.png",
        12.80,
        15.70,
        "depth_zoom",
        "soft_blur",
        "收纳，是生活的从容",
        "STORAGE, CALMLY BUILT IN",
        "把衣帽间做成高级展厅感",
    ),
    Shot(
        "10_material_detail.png",
        15.70,
        17.90,
        "detail_reveal",
        "light_sweep",
        "材质，决定第一眼质感",
        "MATERIALS SPEAK FIRST",
        "用近景强调木饰面、岩板和收口细节",
    ),
    Shot(
        "05_master_bedroom.png",
        17.90,
        20.12,
        "final_soft",
        "quiet_fade",
        "高级全屋定制",
        "LUXURY CUSTOM HOME",
        "以卧室生活方式做温柔收尾",
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


def select_music() -> Path:
    files: list[Path] = []
    for ext in ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.flac"):
        files.extend(sorted(MUSIC_DIR.rglob(ext)))
    if not files:
        raise FileNotFoundError(f"No music files found under {MUSIC_DIR}")
    return random.choice(files)


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
    if motion == "hero_push":
        return 1.08 + 0.07 * e, 0.0, 0.03 - 0.05 * e
    if motion == "slow_pull":
        return 1.16 - 0.07 * e, 0.02 * math.sin(math.pi * e), 0.0
    if motion == "pan_right":
        return 1.13, -0.10 + 0.20 * e, -0.02 + 0.02 * e
    if motion == "pan_left":
        return 1.13, 0.10 - 0.20 * e, 0.01 - 0.02 * e
    if motion == "depth_zoom":
        return 1.08 + 0.10 * e, -0.03 + 0.06 * e, 0.0
    if motion == "detail_reveal":
        return 1.18 - 0.05 * e, -0.08 + 0.11 * e, 0.04 - 0.06 * e
    if motion == "final_soft":
        return 1.10 + 0.06 * e, -0.03 + 0.03 * e, 0.02 - 0.02 * e
    return 1.1, 0.0, 0.0


def color_grade(img: Image.Image, t: float) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.11)
    img = ImageEnhance.Color(img).enhance(0.90)
    img = ImageEnhance.Sharpness(img).enhance(1.07)
    arr = np.asarray(img).astype(np.float32)

    lum = arr[..., 0:1] * 0.2126 + arr[..., 1:2] * 0.7152 + arr[..., 2:3] * 0.0722
    shadow = np.clip((95 - lum) / 95, 0, 1)
    highlight = np.clip((lum - 150) / 105, 0, 1)
    cool_shadow = np.array([218, 224, 226], dtype=np.float32)
    warm_highlight = np.array([255, 232, 202], dtype=np.float32)
    arr = arr * (1 - shadow * 0.045) + cool_shadow * shadow * 0.045
    arr = arr * (1 - highlight * 0.035) + warm_highlight * highlight * 0.035

    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((r - 0.42) / 0.65, 0, 1) * 0.18
    arr *= vignette[..., None]

    if t < 0.8:
        arr *= 0.78 + 0.22 * ease_out(t / 0.8)
    if t > DURATION - 0.9:
        arr *= 1.0 + 0.025 * ease((t - (DURATION - 0.9)) / 0.9)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def light_sweep(img: Image.Image, amount: float, position: float) -> Image.Image:
    amount = max(0.0, min(1.0, amount))
    if amount <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    xs = np.linspace(0, 1, W, dtype=np.float32)
    band = np.exp(-((xs - position) ** 2) / 0.0045) * amount
    arr += band[None, :, None] * np.array([70, 58, 42], dtype=np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def render_shot(assets: dict[str, Image.Image], shot: Shot, t: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    z, ox, oy = motion_params(shot.motion, p)
    frame = cover(assets[shot.image], z, ox, oy)
    if shot.motion in {"hero_push", "detail_reveal", "final_soft"}:
        frame = light_sweep(frame, 0.22 * (1 - abs(ease(p) - 0.5)), 0.12 + 0.76 * ease(p))
    return color_grade(frame, t)


def active_shot(t: float) -> tuple[int, Shot]:
    for i, shot in enumerate(SHOTS):
        if shot.start <= t < shot.end or (i == len(SHOTS) - 1 and t <= shot.end):
            return i, shot
    return len(SHOTS) - 1, SHOTS[-1]


def transition_frame(assets: dict[str, Image.Image], idx: int, shot: Shot, t: float) -> Image.Image:
    trans = 0.38
    if idx == 0 or t - shot.start >= trans:
        return render_shot(assets, shot, t)
    p = ease((t - shot.start) / trans)
    prev = SHOTS[idx - 1]
    prev_frame = render_shot(assets, prev, max(prev.start, prev.end - trans + (t - shot.start)))
    curr_frame = render_shot(assets, shot, t)
    frame = Image.blend(prev_frame, curr_frame, p)

    if shot.transition in {"light_reveal", "light_sweep"}:
        frame = light_sweep(frame, 0.55 * math.sin(math.pi * p), p)
    elif shot.transition in {"line_match", "material_match", "axis_push"}:
        frame = frame.filter(ImageFilter.GaussianBlur(radius=max(0.0, 0.85 - abs(p - 0.5) * 1.7)))
    elif shot.transition == "soft_blur":
        frame = frame.filter(ImageFilter.GaussianBlur(radius=max(0.0, 1.05 - abs(p - 0.5) * 2.1)))
    elif shot.transition == "quiet_fade":
        pass
    return frame


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, tracking: int) -> float:
    return sum(draw.textlength(ch, font=fnt) for ch in text) + tracking * max(0, len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: int,
    y: int,
    fnt: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    tracking: int,
) -> None:
    total = text_width(draw, text, fnt, tracking)
    x = center_x - total / 2
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def add_caption(img: Image.Image, shot: Shot, t: float) -> Image.Image:
    p = (t - shot.start) / max(0.001, shot.end - shot.start)
    fade = ease(max(0.0, min(p / 0.24, (1 - p) / 0.20, 1.0)))
    final = shot.motion == "final_soft"
    cn_font = pick_font(48 if not final else 58)
    en_font = pick_font(25 if not final else 31)
    small_font = pick_font(20)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    shade_h = 430
    for y in range(H - shade_h, H):
        a = int(((y - (H - shade_h)) / shade_h) ** 1.65 * 120)
        draw.line((0, y, W, y), fill=(0, 0, 0, a))

    alpha = int(232 * fade)
    y = 1400 if not final else 1335
    cn_bbox = draw.textbbox((0, 0), shot.caption_cn, font=cn_font)
    cn_x = (W - (cn_bbox[2] - cn_bbox[0])) // 2
    draw.text((cn_x + 2, y + 2), shot.caption_cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.42)))
    draw.text((cn_x, y), shot.caption_cn, font=cn_font, fill=(246, 241, 232, alpha))
    draw_tracked(draw, shot.caption_en, W // 2 + 2, y + 73 + 2, en_font, (0, 0, 0, int(alpha * 0.38)), 4)
    draw_tracked(draw, shot.caption_en, W // 2, y + 73, en_font, (232, 228, 218, int(alpha * 0.92)), 4)
    line_y = y + 132
    draw.line((W // 2 - 150, line_y, W // 2 + 150, line_y), fill=(232, 228, 218, int(alpha * 0.45)), width=1)
    if final:
        draw_tracked(draw, "WHOLE HOUSE CUSTOMIZATION", W // 2, line_y + 34, small_font, (232, 228, 218, int(alpha * 0.72)), 6)
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
    for i in range(total):
        t = min(DURATION - 1 / FPS, i / FPS)
        proc.stdin.write(np.asarray(frame_at(t, assets), dtype=np.uint8).tobytes())
        if i % 180 == 0:
            print(f"rendered {i}/{total} frames", flush=True)
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(stderr)


def make_looped_music(music_path: Path, output_path: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-stream_loop",
            str(MUSIC_LOOPS - 1),
            "-i",
            str(music_path),
            "-t",
            f"{DURATION:.2f}",
            "-af",
            "afade=t=in:st=0:d=0.35,afade=t=out:st=19.55:d=0.55",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )


def attach_music(silent_path: Path, audio_path: Path, final_path: Path) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-i",
            str(silent_path),
            "-i",
            str(audio_path),
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
            str(final_path),
        ]
    )


def make_preview_sheet(assets: dict[str, Image.Image], path: Path) -> None:
    times = [0.5, 3.9, 7.5, 10.7, 13.6, 16.4, 19.2]
    thumbs = []
    for t in times:
        frame = frame_at(t, assets)
        frame.thumbnail((216, 384), Image.Resampling.LANCZOS)
        thumbs.append(frame.copy())
    sheet = Image.new("RGB", (216 * 4, 384 * 2), (18, 18, 18))
    for i, thumb in enumerate(thumbs):
        x = (i % 4) * 216
        y = (i // 4) * 384
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
        entry["projects"] = sorted(set(entry.get("projects", [])) | {"premium_douyin_showcase"})
        entry["suitable_for_showcase"] = True
        entry["suitable_for_walkthrough"] = shot.image in {"12_final_hero.png", "01_living_full.png", "04_kitchen.png", "06_walk_in_closet.png"}
        entry["space_type"] = {
            "12_final_hero.png": "whole_home_hero",
            "01_living_full.png": "living_room",
            "03_dining_sideboard.png": "dining_sideboard",
            "04_kitchen.png": "kitchen",
            "06_walk_in_closet.png": "walk_in_closet",
            "10_material_detail.png": "material_detail",
            "05_master_bedroom.png": "master_bedroom",
        }[shot.image]
        entry["style_tags"] = ["italian_minimal", "warm_grey", "luxury_custom_home"]
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_production_plan(path: Path, music_path: Path) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f} | {shot.image} | {shot.motion} | {shot.transition} | {shot.caption_cn} / {shot.caption_en} | {shot.purpose} |"
        for shot in SHOTS
    )
    path.write_text(
        f"""# 高级装修视频制作方案

本次视频类型：图片展示型
本次节奏模式：高级广告模式
本次视频风格：意式极简豪宅 / 大平层样板间
本次音乐方向：本地音乐库随机选择，快节奏家居氛围音乐，作为背景情绪循环两遍
本次画面关键词：暖灰、木饰面、隐藏灯带、岩板、全屋定制、空间秩序
本次核心卖点：用舒适慢镜头展示全案设计、柜体工艺和高端生活方式

## 音乐分析

- 所选音乐：`{music_path}`
- 原始时长：约 10.06 秒
- 估算节奏：约 180 BPM，鼓点密集，高潮出现较早
- 创作判断：如果按鼓点切图会造成快闪，影响客户观看空间
- 处理方式：音乐循环两遍并做淡入淡出，视频总时长 20.12 秒；画面不追每个鼓点，只在段落转换处做柔和转场

## 素材判断

当前素材是静态室内图，没有真实连续视频或 3D 漫游片段，因此本次选择图片展示型，而不是强行做空间漫游型。

精选 7 张核心图：完整空间、客厅、餐边柜、厨房、衣帽间、材质细节、卧室收尾。空间图停留约 2.9-3.4 秒，细节图 2.2 秒，符合高级广告模式的观看规则。

## 分镜

| 时间 | 素材 | 运镜 | 转场 | 字幕 | 目的 |
|---|---|---|---|---|---|
{rows}

## 调色

低饱和、暖灰电影感、干净阴影、柔和高光。保留灯带层次，材质清晰但不过度锐化。

## 输出

- 最终视频：`full_house_custom_ad/output/premium_douyin_showcase_20s.mp4`
- 无声视频：`full_house_custom_ad/output/premium_douyin_showcase_20s_video_only.mp4`
- 预览拼图：`full_house_custom_ad/output/premium_douyin_showcase_20s_preview.jpg`
- 素材记录：`full_house_custom_ad/asset_manifest.json`
""",
        encoding="utf-8",
    )


def main() -> None:
    random.seed()
    music = select_music()
    assets = load_assets()

    silent = OUT_DIR / "premium_douyin_showcase_20s_video_only.mp4"
    looped_music = OUT_DIR / "premium_douyin_showcase_20s_music.aac"
    final = OUT_DIR / "premium_douyin_showcase_20s.mp4"
    preview = OUT_DIR / "premium_douyin_showcase_20s_preview.jpg"
    plan = OUT_DIR / "premium_douyin_showcase_20s_plan.md"

    render_video(assets, silent)
    make_looped_music(music, looped_music)
    attach_music(silent, looped_music, final)
    looped_music.unlink(missing_ok=True)
    make_preview_sheet(assets, preview)
    update_manifest()
    write_production_plan(plan, music)

    print(final)
    print(silent)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)
    print(music)


if __name__ == "__main__":
    main()
