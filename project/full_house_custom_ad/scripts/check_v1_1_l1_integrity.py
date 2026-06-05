#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


REQUIRED_FILES = [
    ROOT / "scripts" / "image_generation_provider.py",
    ROOT / "scripts" / "generate_gpt_image_keyframes.py",
    ROOT / "scripts" / "generate_auto_project_assets.py",
    ROOT / "scripts" / "render_static_image_project.py",
    ROOT / "projects" / "example_self_generated_l1" / "project.json",
]

REQUIRED_KEYWORDS = {
    ROOT / "scripts" / "generate_auto_project_assets.py": [
        "generate_gpt_image_keyframes.py",
        "static_keyframes",
        "source_type",
        "static_images",
    ],
    ROOT / "scripts" / "generate_gpt_image_keyframes.py": [
        "OPENAI_API_KEY",
        "minimum_keyframes",
        "generated_capability_level",
        "L1",
    ],
    REPO / "README.md": [
        "example_self_generated_l1",
        "OPENAI_API_KEY",
        "generate_gpt_image_keyframes.py",
        "L1",
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
        print("V1.1 L1 integrity check failed.")
        for error in errors:
            print(f"- {error}")
        return 1
    print("V1.1 L1 integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
