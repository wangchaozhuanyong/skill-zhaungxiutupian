#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_walkthrough_continuity.py"
SEGMENTED_ASSEMBLER = ROOT / "scripts" / "assemble_segmented_ai_walkthrough_clips.py"


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def has_segmented_clips(config: dict[str, Any]) -> bool:
    return bool(config.get("source_clips_dir") or config.get("clip_dir") or config.get("ai_clips_dir"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a full house custom ad project from project.json.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--allow-downgrade", action="store_true", help="Override config allow_downgrade")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    report = ROOT / "output" / f"{output_name}_continuity_report.md"

    validate_cmd = [
        sys.executable,
        str(VALIDATOR),
        "--config",
        str(config_path),
        "--output",
        str(report),
    ]
    allow_downgrade = bool(config.get("allow_downgrade", False)) or args.allow_downgrade
    if not allow_downgrade:
        validate_cmd.append("--fail-on-overclaim")

    validation = run(validate_cmd, check=False)
    if validation.returncode == 3:
        print(
            "项目目标高于当前素材能力，已停止渲染。请查看 continuity_report.md，或明确 allow_downgrade=true。",
            file=sys.stderr,
        )
        return 3
    if validation.returncode != 0:
        return validation.returncode
    if args.validate_only:
        return 0

    if has_segmented_clips(config):
        return run([sys.executable, str(SEGMENTED_ASSEMBLER), "--config", str(config_path)], check=False).returncode

    source_video = resolve_path(config.get("source_video"))
    if source_video and source_video.exists():
        print("已生成连续性报告。当前通用入口暂不重剪单条连续视频，请使用对应后期脚本或新增 renderer。")
        print(report)
        return 0

    print("没有找到可渲染素材。已生成连续性报告。")
    print(report)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
