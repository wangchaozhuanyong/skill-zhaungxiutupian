#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DEPS = ROOT / ".deps"
if DEPS.exists():
    sys.path.insert(0, str(DEPS))
sys.path.insert(0, str(REPO))

import requests


CLIP_DIR = ROOT / "ai_clips" / "true_walkthrough_19s"
ASSEMBLER = ROOT / "scripts" / "assemble_true_walkthrough_ai_clips.py"
NEGATIVE_PROMPT = (
    "cartoon, animation, CGI look, low quality, blurry, distorted room, "
    "distorted wide angle, warped cabinet lines, messy clutter, harsh lighting, "
    "over saturated colors, cheap decoration, red yellow promotional text, "
    "subtitles, logo, watermark, people, shaky handheld camera, fast cuts, "
    "flicker, unrealistic furniture"
)


@dataclass(frozen=True)
class ClipPrompt:
    filename: str
    duration: int
    prompt: str


CLIPS = [
    ClipPrompt(
        "01_entry_wall_cabinet.mp4",
        4,
        "Luxury minimalist custom home walkthrough video, vertical 9:16, continuous gimbal camera movement, low camera height, entering from a hallway beside an integrated wall cabinet system, warm grey wood veneer, hidden LED lighting, clean floor reflection, quiet luxury interior, cinematic real estate walkthrough, natural wide angle, no text, no watermark.",
    ),
    ClipPrompt(
        "02_living_room_opening.mp4",
        4,
        "High-end living room walkthrough video, vertical 9:16, camera slowly moves forward from entry into a spacious minimalist living room, premium TV wall, integrated storage cabinets, sofa area revealed gradually, warm grey palette, wood veneer and stone, glossy floor reflection, soft hidden LED lights, cinematic stable gimbal movement, no text, no watermark.",
    ),
    ClipPrompt(
        "03_dining_kitchen_slide.mp4",
        5,
        "Luxury dining and open kitchen walkthrough video, vertical 9:16, slow lateral camera slide along a dining sideboard into an open kitchen with island, premium built-in cabinets, hidden LED strip lighting, warm grey and natural wood palette, clean floor reflection, elegant residential interior, cinematic gimbal movement, no people, no text, no watermark.",
    ),
    ClipPrompt(
        "04_bedroom_closet_walk.mp4",
        4,
        "Luxury master bedroom and wardrobe walkthrough video, vertical 9:16, camera enters from the edge of a tall wardrobe cabinet, integrated closet system, calm bedroom, warm indirect lighting, soft fabric bed, wood veneer cabinet doors, quiet premium residential atmosphere, smooth stabilizer movement, no text, no watermark.",
    ),
    ClipPrompt(
        "05_material_light_close.mp4",
        5,
        "Luxury custom cabinet material detail walkthrough video, vertical 9:16, slow cinematic close-up moving along wood veneer, stone texture, hidden LED strip, precise cabinet gaps and premium hardware, warm grey color grading, subtle bloom, then revealing a clean built-in cabinet wall, ultra realistic interior video, no text, no watermark.",
    ),
]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def download_video(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def generate_clip(provider, clip: ClipPrompt, model: str, resolution: str) -> Path:
    out = CLIP_DIR / clip.filename
    if out.exists() and out.stat().st_size > 1024:
        print(f"skip existing {clip.filename}")
        return out
    print(f"generating {clip.filename} ({clip.duration}s)", flush=True)
    result = provider.generate(
        prompt=clip.prompt,
        model=model,
        duration=clip.duration,
        aspect_ratio="9:16",
        resolution=resolution,
        negative_prompt=NEGATIVE_PROMPT,
        audio=False,
    )
    if not result.get("success"):
        raise RuntimeError(f"{clip.filename}: {result.get('error')}")
    video_url = result.get("video")
    if not video_url:
        raise RuntimeError(f"{clip.filename}: provider returned no video URL")
    download_video(video_url, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI video clips for true walkthrough via FAL.")
    parser.add_argument("--model", default="seedance-2.0", help="FAL video model family")
    parser.add_argument("--resolution", default="720p", choices=["480p", "540p", "720p", "1080p"])
    parser.add_argument("--no-assemble", action="store_true", help="Only generate clips; do not assemble final video")
    args = parser.parse_args()

    load_dotenv(Path.home() / ".hermes" / ".env")
    if not os.environ.get("FAL_KEY", "").strip() or os.environ["FAL_KEY"].strip() == "your_fal_api_key_here":
        print("FAL_KEY is not configured.")
        print("Open /Users/wangchao/.hermes/.env and add: FAL_KEY=your_real_fal_key")
        return 2

    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    from plugins.video_gen.fal import FALVideoGenProvider

    provider = FALVideoGenProvider()
    for clip in CLIPS:
        generate_clip(provider, clip, args.model, args.resolution)

    if not args.no_assemble:
        subprocess.run([sys.executable, str(ASSEMBLER)], cwd=str(REPO), check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
