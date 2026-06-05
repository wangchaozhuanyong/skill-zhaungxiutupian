from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets" / "generated"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
FPS = 60
DURATION = 12.0
FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")


@dataclass(frozen=True)
class Shot:
    image: str
    start: float
    end: float
    motion: str
    caption_cn: str
    caption_en: str


SHOTS = [
    Shot("01_living_full.png", 0.0, 1.2, "hero_push", "全屋一体化设计", "WHOLE HOME, DESIGNED AS ONE"),
    Shot("03_dining_sideboard.png", 1.2, 2.8, "pan_right", "大宅尺度 静奢格调", "GRAND LIVING, QUIET LUXURY"),
    Shot("02_tv_wall.png", 2.8, 4.2, "detail_slide", "每一道线条都有意义", "EVERY LINE HAS PURPOSE"),
    Shot("04_kitchen.png", 4.2, 5.8, "vertical_reveal", "为日常优雅而定制", "BUILT FOR DAILY ELEGANCE"),
    Shot("05_master_bedroom.png", 5.8, 7.2, "pull_out", "舒适与精度并存", "COMFORT MEETS PRECISION"),
    Shot("06_walk_in_closet.png", 7.2, 8.8, "depth_zoom", "收纳也可以成为艺术", "STORAGE BECOMES ART"),
    Shot("07_study_bookcase.png", 8.8, 10.2, "beat_pan", "细节定义品质", "DETAILS DEFINE LUXURY"),
    Shot("01_living_full.png", 10.2, 12.0, "final_push", "高端全屋定制", "PREMIUM CUSTOM HOME"),
]


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def load_assets() -> dict[str, Image.Image]:
    assets: dict[str, Image.Image] = {}
    for shot in SHOTS:
        path = ASSET_DIR / shot.image
        if not path.exists():
            raise FileNotFoundError(path)
        assets[shot.image] = Image.open(path).convert("RGB")
    return assets


def cover_frame(img: Image.Image, zoom: float, offset_x: float, offset_y: float) -> Image.Image:
    target_w = int(WIDTH * zoom)
    target_h = int(HEIGHT * zoom)
    src_ratio = img.width / img.height
    dst_ratio = target_w / target_h
    if src_ratio > dst_ratio:
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        new_w = target_w
        new_h = int(new_w / src_ratio)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    max_x = max(0, new_w - WIDTH)
    max_y = max(0, new_h - HEIGHT)
    cx = 0.5 + offset_x
    cy = 0.5 + offset_y
    left = int(max(0, min(max_x, max_x * cx)))
    top = int(max(0, min(max_y, max_y * cy)))
    return resized.crop((left, top, left + WIDTH, top + HEIGHT))


def motion_params(motion: str, p: float) -> tuple[float, float, float]:
    e = smoothstep(p)
    if motion == "hero_push":
        return 1.02 + 0.08 * e, 0.0, -0.01 + 0.02 * e
    if motion == "pan_right":
        return 1.08, -0.11 + 0.22 * e, 0.0
    if motion == "detail_slide":
        return 1.14, 0.10 - 0.20 * e, 0.04 * math.sin(e * math.pi)
    if motion == "vertical_reveal":
        return 1.09, 0.0, -0.12 + 0.24 * e
    if motion == "pull_out":
        return 1.12 - 0.08 * e, 0.02 * math.sin(e * math.pi), 0.0
    if motion == "depth_zoom":
        return 1.04 + 0.12 * e, -0.04 + 0.08 * e, 0.0
    if motion == "beat_pan":
        return 1.12, -0.08 + 0.16 * e, -0.02
    if motion == "final_push":
        return 1.01 + 0.07 * e, 0.0, 0.0
    return 1.05, 0.0, 0.0


def grade(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(0.94)
    img = ImageEnhance.Sharpness(img).enhance(1.10)
    warm = Image.new("RGB", img.size, (255, 236, 210))
    return Image.blend(img, warm, 0.035)


def vignette_overlay() -> Image.Image:
    y, x = np.ogrid[-1:1:HEIGHT * 1j, -1:1:WIDTH * 1j]
    mask = np.sqrt(x * x + y * y)
    mask = np.clip((mask - 0.35) / 0.75, 0, 1)
    alpha = (mask**1.8 * 78).astype(np.uint8)
    overlay = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    overlay[..., 3] = alpha
    return Image.fromarray(overlay, "RGBA")


VIGNETTE = vignette_overlay()


def draw_tracking_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    tracking: int,
) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bbox = draw.textbbox((x, y), ch, font=font)
        x += (bbox[2] - bbox[0]) + tracking


def tracking_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, tracking: int) -> int:
    width = 0
    for i, ch in enumerate(text):
        bbox = draw.textbbox((0, 0), ch, font=font)
        width += bbox[2] - bbox[0]
        if i < len(text) - 1:
            width += tracking
    return width


def add_caption(frame: Image.Image, text_cn: str, text_en: str, local_p: float, final: bool = False) -> Image.Image:
    canvas = frame.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    cn_size = 46 if not final else 60
    en_size = 30 if not final else 36
    small_size = 22 if final else 19
    cn_font = ImageFont.truetype(str(FONT_PATH), cn_size)
    en_font = ImageFont.truetype(str(FONT_PATH), en_size)
    small = ImageFont.truetype(str(FONT_PATH), small_size)
    fade_in = min(1.0, local_p / 0.16)
    fade_out = min(1.0, (1.0 - local_p) / 0.18)
    alpha = int(235 * max(0.0, min(fade_in, fade_out)))
    en_tracking = 5 if not final else 7
    cn_bbox = draw.textbbox((0, 0), text_cn, font=cn_font)
    cn_w = cn_bbox[2] - cn_bbox[0]
    en_w = tracking_width(draw, text_en, en_font, en_tracking)
    y = 1418 if not final else 1308
    cn_x = (WIDTH - cn_w) // 2
    en_x = (WIDTH - en_w) // 2
    en_y = y + cn_size + 18
    draw.text((cn_x + 2, y + 2), text_cn, font=cn_font, fill=(0, 0, 0, int(alpha * 0.42)))
    draw.text((cn_x, y), text_cn, font=cn_font, fill=(246, 241, 232, alpha))
    draw_tracking_text(draw, (en_x + 2, en_y + 2), text_en, en_font, (0, 0, 0, int(alpha * 0.38)), en_tracking)
    draw_tracking_text(draw, (en_x, en_y), text_en, en_font, (238, 231, 220, int(alpha * 0.92)), en_tracking)
    line_w = min(380, max(150, max(cn_w, en_w) // 3))
    line_y = en_y + en_size + 30
    draw.line(
        ((WIDTH - line_w) // 2, line_y, (WIDTH + line_w) // 2, line_y),
        fill=(246, 241, 232, int(alpha * 0.65)),
        width=2,
    )
    if final:
        sub = "WHOLE HOUSE CUSTOMIZATION"
        bbox = draw.textbbox((0, 0), sub, font=small)
        sx = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((sx + 1, line_y + 28), sub, font=small, fill=(0, 0, 0, int(alpha * 0.34)))
        draw.text((sx, line_y + 27), sub, font=small, fill=(235, 228, 216, int(alpha * 0.88)))
    return canvas.convert("RGB")


def light_sweep(frame: Image.Image, intensity: float, position: float) -> Image.Image:
    if intensity <= 0:
        return frame
    arr = np.asarray(frame).astype(np.float32)
    xs = np.linspace(0, 1, WIDTH, dtype=np.float32)
    band = np.exp(-((xs - position) ** 2) / 0.004) * intensity
    arr += band[None, :, None] * np.array([70, 58, 42], dtype=np.float32)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def render_shot(assets: dict[str, Image.Image], shot: Shot, t: float) -> Image.Image:
    p = (t - shot.start) / (shot.end - shot.start)
    zoom, ox, oy = motion_params(shot.motion, p)
    frame = cover_frame(assets[shot.image], zoom, ox, oy)
    frame = grade(frame)
    if shot.motion in {"hero_push", "final_push"}:
        frame = light_sweep(frame, 28 * (1 - smoothstep(min(1, p * 2))), 0.16 + 0.72 * smoothstep(p))
    frame = frame.convert("RGBA")
    frame.alpha_composite(VIGNETTE)
    frame = frame.convert("RGB")
    frame = add_caption(frame, shot.caption_cn, shot.caption_en, p, final=shot.motion == "final_push")
    return frame


def frame_at(assets: dict[str, Image.Image], t: float) -> Image.Image:
    idx = next(i for i, shot in enumerate(SHOTS) if shot.start <= t < shot.end or (i == len(SHOTS) - 1 and t <= shot.end))
    shot = SHOTS[idx]
    frame = render_shot(assets, shot, t)
    transition = 0.18
    if idx > 0 and t - shot.start < transition:
        prev = SHOTS[idx - 1]
        prev_frame = render_shot(assets, prev, min(prev.end - 1 / FPS, prev.end - (transition - (t - shot.start))))
        a = smoothstep((t - shot.start) / transition)
        frame = Image.blend(prev_frame, frame, a)
        frame = light_sweep(frame, 36 * (1 - abs(a - 0.5) * 2), a)
    if t > 11.45:
        freeze = min(1.0, (t - 11.45) / 0.35)
        overlay = Image.new("RGB", (WIDTH, HEIGHT), (246, 241, 232))
        frame = Image.blend(frame, overlay, 0.045 * freeze)
    return frame


def write_music_guide(path: Path) -> None:
    path.write_text(
        """抖音发布音乐建议

本视频建议导出无音乐版，发布抖音时再使用抖音App内的近期热门音乐，这样更利于平台音乐流量和版权安全。

推荐音乐方向：
- 高级感 Deep House
- Luxury House
- Melodic House
- Fashion Beat
- Chill Electronic
- 高端生活方式类英文BGM
- 豪宅/装修/家居案例常用热门BGM

抖音搜索关键词：
- 高级感
- 豪宅
- 装修
- 家居
- 样板间
- luxury
- deep house
- house
- fashion
- chill
- lifestyle
- interior
- home design

卡点方案：
- 0秒：第一个重拍进入主视觉
- 1.5秒：第一次空间切换
- 4秒：进入定制细节
- 7秒：进入空间价值展示
- 10秒：进入高潮画面
- 11.5-12秒：品牌定格收尾

选歌标准：
- 前1秒或可裁剪起点附近有明显重拍
- 鼓点干净，中低频有质感
- 音乐要高级、现代、有生活方式感
- 优先选择抖音近期热门、收藏量高、同类家居账号正在使用的音乐
- 避免悲伤、土味、广场舞感、廉价电子感或强噪声感
""",
        encoding="utf-8",
    )


def run_ffmpeg(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)


def main() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    assets = load_assets()
    output = OUTPUT_DIR / "full_house_custom_ad_douyin_12s_bilingual_silent.mp4"
    guide = OUTPUT_DIR / "douyin_music_guide.txt"

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        f"{WIDTH}x{HEIGHT}",
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
        str(output),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    total_frames = int(DURATION * FPS)
    for i in range(total_frames):
        t = i / FPS
        frame = frame_at(assets, t)
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
        if i % 120 == 0:
            print(f"rendered {i}/{total_frames} frames")
    proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(stderr)

    write_music_guide(guide)
    print(output)
    print(guide)


if __name__ == "__main__":
    main()
