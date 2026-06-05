#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


REQUIRED_FILES = [
    ROOT / "scripts" / "fal_video_provider.py",
    ROOT / "scripts" / "generate_continuous_ai_walkthrough_fal.py",
    ROOT / "scripts" / "generate_segmented_ai_walkthrough_clips_fal.py",
    ROOT / "scripts" / "generate_auto_project_assets.py",
]

REQUIRED_KEYWORDS = {
    ROOT / "scripts" / "fal_video_provider.py": [
        "queue.fal.run",
        "Authorization",
        "FAL_KEY",
        "bytedance/seedance-2.0/text-to-video",
    ],
    ROOT / "scripts" / "generate_continuous_ai_walkthrough_fal.py": [
        "FALQueueVideoProvider",
        "generated_source_type",
        "continuous_ai_video",
        "generated_capability_level",
        "L3",
    ],
    ROOT / "scripts" / "generate_segmented_ai_walkthrough_clips_fal.py": [
        "FALQueueVideoProvider",
        "generated_source_type",
        "segmented_ai_clips",
        "generated_capability_level",
        "L2",
    ],
    REPO / "README.md": [
        "fal_video_provider.py",
        "FAL_KEY",
        "continuous_ai_video",
        "segmented_ai_clips",
    ],
}


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing file: {path}")
    for path, keywords in REQUIRED_KEYWORDS.items():
        if not path.exists():
            errors.append(f"missing file: {path}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for keyword in keywords:
            if keyword not in text:
                errors.append(f"{path.name} missing keyword: {keyword}")
    if errors:
        print("V1.1 video backend integrity check failed.")
        for error in errors:
            print(f"- {error}")
        return 1
    print("V1.1 video backend integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
