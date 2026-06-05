#!/usr/bin/env python3
from __future__ import annotations

import math
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


W, H = 1080, 1920
FPS = 60
DURATION = 12.0
ASSET_DIR = ROOT / "assets" / "generated"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_MAIN = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_ALT = "/System/Library/Fonts/Avenir Next.ttc"


SHOTS = [
    {
        "start": 0.0,
        "end": 1.2,
        "image": "01_living_full.png",
        "motion": "push",
        "scale": (1.08, 1.24),
        "x": (0.0, 0.0),
        "y": (0.04, -0.02),
        "transition": "flash",
    },
    {
        "start": 1.2,
        "end": 2.2,
        "image": "02_tv_wall.png",
        "motion": "pan_right",
        "scale": (1.12, 1.18),
        "x": (-0.10, 0.10),
        "y": (0.0, 0.0),
        "transition": "match_zoom",
    },
    {
        "start": 2.2,
        "end": 3.2,
        "image": "03_dining_sideboard.png",
        "motion": "pull",
        "scale": (1.20, 1.10),
        "x": (0.05, -0.05),
        "y": (0.02, 0.0),
        "transition": "light_leak",
    },
    {
        "start": 3.2,
        "end": 4.1,
        "image": "08_entry_cabinet.png",
        "motion": "vertical_reveal",
        "scale": (1.18, 1.14),
        "x": (0.0, 0.0),
        "y": (0.14, -0.12),
        "transition": "whip",
    },
    {
        "start": 4.1,
        "end": 5.0,
        "image": "04_kitchen.png",
        "motion": "pan_left",
        "scale": (1.13, 1.18),
        "x": (0.12, -0.10),
        "y": (0.0, 0.0),
        "transition": "zoom",
    },
    {
        "start": 5.0,
        "end": 5.9,
        "image": "09_led_detail.png",
        "motion": "macro_push",
        "scale": (1.08, 1.26),
        "x": (0.02, -0.02),
        "y": (0.06, 0.0),
        "transition": "film_burn",
    },
    {
        "start": 5.9,
        "end": 6.8,
        "image": "10_material_detail.png",
        "motion": "depth_zoom",
        "scale": (1.10, 1.24),
        "x": (-0.05, 0.04),
        "y": (0.02, -0.02),
        "transition": "match_zoom",
    },
    {
        "start": 6.8,
        "end": 7.7,
        "image": "11_storage_detail.png",
        "motion": "pull",
        "scale": (1.22, 1.10),
        "x": (0.04, 0.0),
        "y": (-0.03, 0.03),
        "transition": "motion_blur",
    },
    {
        "start": 7.7,
        "end": 8.7,
        "image": "05_master_bedroom.png",
        "motion": "parallax_push",
        "scale": (1.10, 1.20),
        "x": (-0.06, 0.04),
        "y": (0.04, -0.02),
        "transition": "soft_zoom",
    },
    {
        "start": 8.7,
        "end": 9.6,
        "image": "06_walk_in_closet.png",
        "motion": "pan_right",
        "scale": (1.12, 1.18),
        "x": (-0.12, 0.10),
        "y": (0.0, 0.0),
        "transition": "whip",
    },
    {
        "start": 9.6,
        "end": 10.5,
        "image": "07_study_bookcase.png",
        "motion": "vertical_reveal",
        "scale": (1.18, 1.10),
        "x": (0.0, 0.0),
        "y": (0.12, -0.10),
        "transition": "speed_ramp",
    },
    {
        "start": 10.5,
        "end": 12.0,
        "image": "12_final_hero.png",
        "motion": "final_push",
        "scale": (1.08, 1.18),
        "x": (0.0, 0.0),
        "y": (0.02, -0.02),
        "transition": "light_leak",
    },
]


TEXTS = [
    {"text": "Luxury Custom Home", "start": 0.25, "end": 1.75, "size": 58, "y": 0.17, "tracking": 5},
    {"text": "Designed for Modern Living", "start": 2.45, "end": 4.65, "size": 42, "y": 0.80, "tracking": 4},
    {"text": "Every Detail Matters", "start": 5.15, "end": 7.45, "size": 44, "y": 0.80, "tracking": 4},
    {"text": "A Home Made for You", "start": 7.95, "end": 10.20, "size": 43, "y": 0.80, "tracking": 4},
    {
        "text": "Premium Whole House Customization",
        "start": 10.78,
        "end": 12.0,
        "size": 38,
        "y": 0.76,
        "tracking": 3,
    },
    {"text": "Luxury Begins at Home", "start": 11.40, "end": 12.0, "size": 31, "y": 0.82, "tracking": 5},
]


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out_quint(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 5


def load_assets() -> dict[str, Image.Image]:
    assets = {}
    for shot in SHOTS:
        path = ASSET_DIR / shot["image"]
        img = Image.open(path).convert("RGB")
        assets[shot["image"]] = img
    return assets


def cover_transform(img: Image.Image, shot: dict, p: float, extra_scale: float = 1.0) -> Image.Image:
    p = ease(p)
    base_scale = max(W / img.width, H / img.height)
    s0, s1 = shot["scale"]
    anim_scale = s0 + (s1 - s0) * p
    scale = base_scale * anim_scale * extra_scale
    rw = max(W, int(img.width * scale))
    rh = max(H, int(img.height * scale))
    resized = img.resize((rw, rh), Image.Resampling.LANCZOS)

    x0, x1 = shot["x"]
    y0, y1 = shot["y"]
    ox = x0 + (x1 - x0) * p
    oy = y0 + (y1 - y0) * p
    max_x = max(0, rw - W)
    max_y = max(0, rh - H)
    left = int(max_x / 2 + ox * max_x / 2)
    top = int(max_y / 2 + oy * max_y / 2)
    left = max(0, min(max_x, left))
    top = max(0, min(max_y, top))
    return resized.crop((left, top, left + W, top + H))


def color_grade(img: Image.Image, t: float) -> Image.Image:
    arr = np.asarray(img).astype(np.float32) / 255.0
    lum = arr[..., 0:1] * 0.2126 + arr[..., 1:2] * 0.7152 + arr[..., 2:3] * 0.0722
    sat = 0.86
    arr = lum + (arr - lum) * sat
    arr = (arr - 0.5) * 1.12 + 0.5
    arr[..., 0] *= 1.035
    arr[..., 1] *= 1.012
    arr[..., 2] *= 0.962
    arr = np.clip(arr, 0, 1)

    yy, xx = np.ogrid[:H, :W]
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx + dy * dy)
    vignette = 1.0 - np.clip((r - 0.45) / 0.65, 0, 1) * 0.16
    arr *= vignette[..., None]

    if 0.0 <= t < 0.7:
        lift = ease_out_quint(t / 0.7)
        arr *= 0.75 + 0.25 * lift

    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGB")


def add_light_leak(img: Image.Image, amount: float, side: str = "right") -> Image.Image:
    amount = max(0.0, min(1.0, amount))
    if amount <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    x = np.linspace(0, 1, W, dtype=np.float32)
    if side == "left":
        grad = 1 - x
    else:
        grad = x
    grad = np.clip((grad - 0.36) / 0.64, 0, 1) ** 1.9
    pulse = math.sin(amount * math.pi)
    color = np.array([255, 196, 112], dtype=np.float32)
    arr = arr * (1 - grad[None, :, None] * 0.20 * pulse) + color[None, None, :] * grad[None, :, None] * 0.20 * pulse
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def add_film_burn(img: Image.Image, amount: float) -> Image.Image:
    amount = max(0.0, min(1.0, amount))
    arr = np.asarray(img).astype(np.float32)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    blob = np.exp(-((xx - 0.18 - 0.62 * amount) ** 2 / 0.045 + (yy - 0.25) ** 2 / 0.18))
    pulse = math.sin(amount * math.pi)
    color = np.array([255, 176, 92], dtype=np.float32)
    arr = arr * (1 - blob[..., None] * 0.22 * pulse) + color[None, None, :] * blob[..., None] * 0.24 * pulse
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def transition_frame(
    prev_img: Image.Image,
    curr_img: Image.Image,
    prev_shot: dict,
    curr_shot: dict,
    p: float,
) -> Image.Image:
    p = ease(p)
    kind = curr_shot["transition"]
    prev = cover_transform(prev_img, prev_shot, 1.0, extra_scale=1.0 + 0.04 * p)
    curr = cover_transform(curr_img, curr_shot, 0.0, extra_scale=1.08 - 0.06 * p)

    if kind in {"whip", "motion_blur", "speed_ramp"}:
        shift = int((1 - p) * W * 0.34)
        prev = prev.transform((W, H), Image.Transform.AFFINE, (1, 0, -shift, 0, 1, 0), resample=Image.Resampling.BICUBIC)
        curr = curr.transform((W, H), Image.Transform.AFFINE, (1, 0, W * 0.18 - shift, 0, 1, 0), resample=Image.Resampling.BICUBIC)
        blended = Image.blend(prev, curr, p)
        return blended.filter(ImageFilter.GaussianBlur(radius=(1 - abs(0.5 - p) * 2) * 3.0))

    blended = Image.blend(prev, curr, p)
    if kind in {"light_leak", "flash"}:
        blended = add_light_leak(blended, p, side="right")
    elif kind == "film_burn":
        blended = add_film_burn(blended, p)
    elif kind in {"zoom", "match_zoom", "soft_zoom"}:
        blended = blended.filter(ImageFilter.GaussianBlur(radius=max(0, 1.2 - abs(p - 0.5) * 2.4)))
    return blended


def shot_at(t: float) -> tuple[int, dict, float]:
    for i, shot in enumerate(SHOTS):
        if shot["start"] <= t < shot["end"] or (i == len(SHOTS) - 1 and t <= shot["end"]):
            p = (t - shot["start"]) / max(0.001, shot["end"] - shot["start"])
            return i, shot, p
    return len(SHOTS) - 1, SHOTS[-1], 1.0


def draw_tracked_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: int,
) -> None:
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = center_x - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + tracking


def add_texts(img: Image.Image, t: float) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for item in TEXTS:
        if not (item["start"] <= t <= item["end"]):
            continue
        fade = min((t - item["start"]) / 0.35, (item["end"] - t) / 0.35, 1.0)
        fade = ease(max(0.0, fade))
        font_path = FONT_ALT if item["size"] < 40 else FONT_MAIN
        font = ImageFont.truetype(font_path, item["size"])
        y = int(H * item["y"] + (1 - fade) * 18)
        alpha = int(232 * fade)
        draw_tracked_text(draw, item["text"], W // 2, y, font, (242, 239, 232, alpha), item["tracking"])

    if 11.35 <= t <= 12.0:
        fade = ease(min((t - 11.35) / 0.45, 1.0))
        font = ImageFont.truetype(FONT_ALT, 24)
        draw_tracked_text(draw, "CUSTOM HOME", W // 2, int(H * 0.90), font, (232, 228, 218, int(150 * fade)), 8)
        line_w = 170
        y = int(H * 0.885)
        draw.line((W // 2 - line_w, y, W // 2 + line_w, y), fill=(232, 228, 218, int(70 * fade)), width=1)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def render_frame(t: float, assets: dict[str, Image.Image]) -> Image.Image:
    idx, shot, p = shot_at(t)
    trans = 0.18
    if idx > 0 and t - shot["start"] < trans:
        prev_shot = SHOTS[idx - 1]
        frame = transition_frame(
            assets[prev_shot["image"]],
            assets[shot["image"]],
            prev_shot,
            shot,
            (t - shot["start"]) / trans,
        )
    else:
        frame = cover_transform(assets[shot["image"]], shot, p)
        if shot["transition"] == "film_burn" and shot["start"] <= t <= shot["start"] + 0.22:
            frame = add_film_burn(frame, (t - shot["start"]) / 0.22)
        if idx == len(SHOTS) - 1 and t - shot["start"] < 0.42:
            frame = add_light_leak(frame, (t - shot["start"]) / 0.42)

    frame = color_grade(frame, t)
    frame = add_texts(frame, t)
    return frame


def synth_audio(path: Path) -> None:
    sr = 44100
    n = int(DURATION * sr)
    t = np.arange(n, dtype=np.float32) / sr
    bpm = 120.0
    beat = 60.0 / bpm
    audio = np.zeros(n, dtype=np.float32)

    def env(start: float, decay: float, length: int) -> np.ndarray:
        local = np.arange(length, dtype=np.float32) / sr
        return np.exp(-local / decay) * (local >= 0)

    for b in np.arange(0, DURATION, beat):
        i = int(b * sr)
        length = min(int(0.23 * sr), n - i)
        if length <= 0:
            continue
        local = np.arange(length, dtype=np.float32) / sr
        kick = np.sin(2 * np.pi * (92 - 52 * local / 0.23) * local) * env(b, 0.08, length)
        audio[i : i + length] += kick * 0.85

    for b in np.arange(beat * 0.5, DURATION, beat):
        i = int(b * sr)
        length = min(int(0.06 * sr), n - i)
        rng = np.random.default_rng(int(b * 1000) + 9)
        hat = rng.normal(0, 1, length).astype(np.float32) * np.exp(-np.linspace(0, 1, length) * 12)
        audio[i : i + length] += hat * 0.10

    for b in np.arange(beat, DURATION, beat * 2):
        i = int(b * sr)
        length = min(int(0.15 * sr), n - i)
        rng = np.random.default_rng(int(b * 1000) + 23)
        clap = rng.normal(0, 1, length).astype(np.float32) * np.exp(-np.linspace(0, 1, length) * 18)
        audio[i : i + length] += clap * 0.13

    roots = [43.65, 51.91, 38.89, 46.25]
    for bar, root in enumerate(roots):
        start = bar * 2.0
        end = min(DURATION, start + 2.0)
        mask = (t >= start) & (t < end)
        local_t = t[mask] - start
        pad = (
            np.sin(2 * np.pi * root * local_t)
            + 0.5 * np.sin(2 * np.pi * root * 2 * local_t)
            + 0.25 * np.sin(2 * np.pi * root * 3 * local_t)
        )
        audio[mask] += pad.astype(np.float32) * 0.055

    swell = np.clip((t - 9.5) / 1.0, 0, 1) * np.clip((12.0 - t) / 1.2, 0, 1)
    audio += np.sin(2 * np.pi * 174.61 * t) * 0.04 * swell
    audio *= np.clip(t / 0.05, 0, 1)
    audio *= np.clip((DURATION - t) / 0.35, 0, 1)
    audio = audio / max(1e-6, np.max(np.abs(audio))) * 0.82

    pcm = (audio * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def main() -> None:
    assets = load_assets()
    silent_mp4 = OUT_DIR / "luxury_custom_home_silent.mp4"
    audio_wav = OUT_DIR / "luxury_deep_house_original.wav"
    final_mp4 = OUT_DIR / "luxury_custom_home_ad_12s.mp4"

    total_frames = int(DURATION * FPS)
    writer = imageio.get_writer(
        silent_mp4,
        fps=FPS,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=None,
        output_params=["-movflags", "+faststart"],
    )
    try:
        for frame_idx in range(total_frames):
            t = frame_idx / FPS
            frame = render_frame(t, assets)
            writer.append_data(np.asarray(frame))
            if frame_idx % 120 == 0:
                print(f"rendered {frame_idx}/{total_frames} frames", flush=True)
    finally:
        writer.close()

    synth_audio(audio_wav)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(silent_mp4),
            "-i",
            str(audio_wav),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final_mp4),
        ],
        check=True,
    )
    print(final_mp4)


if __name__ == "__main__":
    main()
