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
    ROOT / "projects" / "example_self_generated_walkthrough_api_unattended" / "project.json",
    ROOT / "projects" / "example_self_generated_best_effort" / "project.json",
    REPO / "skills" / "full-house-custom-ad" / "references" / "auto-asset-generation.md",
]

README_KEYWORDS = [
    "example_self_generated_walkthrough",
    "example_self_generated_best_effort",
    "auto_generate_assets",
    "auto_generation_mode",
    "strict_true_walkthrough",
    "best_effort",
    "allow_auto_downgrade",
    "generation_execution_mode",
    "codex_session",
    "api_unattended",
    "hyperframes",
    "SESSION_VIDEO_PROVIDER_NOT_AVAILABLE",
    "GENERATOR_NOT_READY",
    "L3_GENERATOR_NOT_READY",
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
        "L3_GENERATOR_NOT_READY",
        "SESSION_VIDEO_PROVIDER_NOT_AVAILABLE",
    ],
    ROOT / "scripts" / "generate_auto_project_assets.py": [
        "continuous_ai_video",
        "segmented_ai_clips",
        "static_keyframes",
        "strict_true_walkthrough",
        "best_effort",
        "codex_session",
        "SESSION_VIDEO_PROVIDER_NOT_AVAILABLE",
        "allow_auto_downgrade",
        "auto_generation_path",
        "GENERATOR_NOT_READY",
    ],
    ROOT / "projects" / "example_self_generated_walkthrough" / "project.json": [
        "source_policy",
        "auto_generate_assets",
        "auto_generation_mode",
        "strict_true_walkthrough",
        "generation_execution_mode",
        "codex_session",
        "session_video_provider_order",
        "hyperframes",
        "allow_auto_downgrade",
        "auto_generation_order",
        "generation_backends",
        "self_generated_asset_plan",
    ],
    ROOT / "projects" / "example_self_generated_walkthrough_api_unattended" / "project.json": [
        "source_policy",
        "auto_generate_assets",
        "generation_execution_mode",
        "api_unattended",
        "auto_generation_mode",
        "strict_true_walkthrough",
        "allow_auto_downgrade",
        "generation_backends",
        "self_generated_asset_plan",
    ],
    ROOT / "projects" / "example_self_generated_best_effort" / "project.json": [
        "source_policy",
        "auto_generate_assets",
        "auto_generation_mode",
        "best_effort",
        "allow_auto_downgrade",
        "auto_generation_order",
        "generation_backends",
        "self_generated_asset_plan",
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
