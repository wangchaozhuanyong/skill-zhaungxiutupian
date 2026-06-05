#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


REQUIRED_FILES = [
    ROOT / "VERSION_STATUS.md",
    ROOT / "scripts" / "generate_auto_project_assets.py",
    ROOT / "scripts" / "generate_continuous_ai_walkthrough_fal.py",
    ROOT / "scripts" / "write_static_keyframe_prompt_pack.py",
    ROOT / "scripts" / "render_project.py",
    ROOT / "scripts" / "validate_walkthrough_continuity.py",
    ROOT / "projects" / "example_self_generated_walkthrough" / "project.json",
    REPO / "skills" / "full-house-custom-ad" / "references" / "auto-asset-generation.md",
]

README_KEYWORDS = [
    "example_self_generated_walkthrough",
    "auto_generate_assets",
    "GENERATOR_NOT_READY",
    "自动生成素材",
    "L1",
    "L2",
    "L3",
    "L4",
]

SCRIPT_KEYWORDS = {
    ROOT / "scripts" / "render_project.py": [
        "generate_auto_project_assets.py",
        "auto_generate_assets",
        "GENERATOR_NOT_READY",
    ],
    ROOT / "scripts" / "generate_auto_project_assets.py": [
        "continuous_ai_video",
        "segmented_ai_clips",
        "static_keyframes",
        "GENERATOR_NOT_READY",
    ],
}


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing file: {path}")

    readme = REPO / "README.md"
    if not readme.exists():
        errors.append(f"missing file: {readme}")
    else:
        text = readme.read_text(encoding="utf-8", errors="replace")
        for keyword in README_KEYWORDS:
            if keyword not in text:
                errors.append(f"README missing keyword: {keyword}")

    for path, keywords in SCRIPT_KEYWORDS.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for keyword in keywords:
            if keyword not in text:
                errors.append(f"{path.name} missing keyword: {keyword}")

    if errors:
        print("V1 final auto-assets integrity check failed.")
        for error in errors:
            print(f"- {error}")
        return 1

    print("V1 final auto-assets integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
