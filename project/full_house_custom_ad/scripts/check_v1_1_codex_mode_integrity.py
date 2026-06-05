#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
SKILL = REPO / "skills" / "full-house-custom-ad"


REQUIRED_FILES = [
    SKILL / "SKILL.md",
    SKILL / "references" / "codex-interactive-generation.md",
    SKILL / "references" / "auto-asset-generation.md",
    SKILL / "references" / "decision-engine.md",
    SKILL / "references" / "output-templates.md",
    SKILL / "references" / "eval-cases.md",
    ROOT / "VERSION_STATUS.md",
    REPO / "README.md",
]

REQUIRED_KEYWORDS = {
    SKILL / "SKILL.md": [
        "Codex 交互式生成模式",
        "API 无人值守模式",
        "是否需要额外 API",
        "不得因缺少收费 API 视频生成后端而停止执行",
    ],
    SKILL / "references" / "codex-interactive-generation.md": [
        "日常默认模式",
        "是否需要额外 API：否",
        "本次最高稳定可执行等级：L1",
        "没有 OPENAI_API_KEY，所以不能做",
    ],
    SKILL / "references" / "auto-asset-generation.md": [
        "默认模式：Codex 交互式生成",
        "可选模式：API 无人值守生成",
        "缺少 API key",
        "Codex 交互模式仍可继续做 L1",
    ],
    SKILL / "references" / "decision-engine.md": [
        "Codex 交互式生成",
        "API 无人值守生成",
        "用户拒绝接 API",
        "必须切回 Codex 交互式生成",
    ],
    SKILL / "references" / "output-templates.md": [
        "生成模式：",
        "是否需要额外 API：",
        "自动原创素材生成模式是否默认使用 Codex 交互式生成",
    ],
    SKILL / "references" / "eval-cases.md": [
        "用户拒绝接 API",
        "是否需要额外 API：否",
        "默认最高稳定可执行等级是 L1",
    ],
    ROOT / "VERSION_STATUS.md": [
        "v1.1-codex-interactive-default",
        "默认启用 Codex 交互式生成模式",
        "缺少 API key 不得成为",
    ],
    REPO / "README.md": [
        "日常在 Codex 里直接调用 skill 时，默认不需要",
        "这段只适用于本地脚本无人值守生成图片",
        "V1.1 Codex interactive mode integrity check passed",
    ],
}


def main() -> int:
    errors: list[str] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"missing file: {path}")

    for path, keywords in REQUIRED_KEYWORDS.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for keyword in keywords:
            if keyword not in text:
                errors.append(f"{path.name} missing keyword: {keyword}")

    if errors:
        print("V1.1 Codex interactive mode integrity check failed.")
        for error in errors:
            print(f"- {error}")
        return 1

    print("V1.1 Codex interactive mode integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
