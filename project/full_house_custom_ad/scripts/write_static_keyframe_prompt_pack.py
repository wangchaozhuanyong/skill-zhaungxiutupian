#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHOTS = [
    ("01_entry_edge", "玄关柜体边缘入场，地面反光引导到客餐厅纵深。"),
    ("02_living_room_opening", "客厅大景慢慢打开，电视墙、沙发、落地窗同时成立。"),
    ("03_tv_wall_focus", "暖灰岩板电视墙和门墙柜一体柜体成为主视觉。"),
    ("04_dining_sideboard_slide", "餐桌、餐边柜和客厅保持同一空间连续关系。"),
    ("05_material_detail", "柜门、木饰面、灯带和石材细节近景。"),
    ("06_final_wide", "客餐厅完整大景收尾，空间比例清楚，少字或无字。"),
]
NEGATIVE_PROMPT = (
    "different room, different house, inconsistent TV wall, inconsistent sofa, "
    "inconsistent dining table, changing floor material, changing cabinet color, "
    "warped cabinet lines, distorted perspective, harsh light, over saturated, "
    "cartoon, low quality, blurry, text, logo, watermark, people"
)


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def style_bible(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("style_bible")
    if isinstance(raw, dict):
        return raw
    return {
        "project_theme": config.get("style", "高端全屋定制原创空间"),
        "floor_plan_assumption": "玄关进入客餐厅一体大横厅，电视墙、沙发、餐桌、餐边柜和落地窗在同一空间内连续成立。",
        "fixed_furniture_layout": "电视墙在长边，沙发正对电视墙，餐桌位于沙发后方，餐边柜靠近餐区。",
        "fixed_tv_wall": "暖灰岩板电视墙，深灰门墙柜一体柜体，隐藏灯带。",
        "fixed_sofa": "低矮暖灰色直排沙发，与电视墙平行。",
        "fixed_dining_table": "深色长方形餐桌，位于客餐厅中轴后段。",
        "fixed_floor_material": "暖灰高反光大板砖，反光干净但不过亮。",
        "fixed_cabinet_material": "深灰哑光柜门、暖木饰面、香槟金属细节。",
        "fixed_light_temperature": "3000K 暖色隐藏灯带，柔和窗光，低饱和高级调色。",
        "negative_prompt": NEGATIVE_PROMPT,
    }


def bible_text(bible: dict[str, Any]) -> str:
    locked = bible.get("locked_visual_elements", [])
    locked_text = ", ".join(str(item) for item in locked) if isinstance(locked, list) else str(locked)
    return (
        f"Project theme: {bible.get('project_theme')}. "
        f"Floor plan: {bible.get('floor_plan_assumption')}. "
        f"Furniture layout: {bible.get('fixed_furniture_layout')}. "
        f"TV wall: {bible.get('fixed_tv_wall')}. "
        f"Sofa: {bible.get('fixed_sofa')}. "
        f"Dining table: {bible.get('fixed_dining_table')}. "
        f"Floor material: {bible.get('fixed_floor_material')}. "
        f"Cabinet material: {bible.get('fixed_cabinet_material')}. "
        f"Light temperature: {bible.get('fixed_light_temperature')}. "
        f"Locked visual elements: {locked_text}. "
        "All keyframes must look like the same home, same living-dining room, same materials, same lighting."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a gpt-image-2 static keyframe prompt pack.")
    parser.add_argument("--config", required=True, help="Project JSON config")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    project_id = str(config.get("project_id", config_path.parent.name))
    output_name = str(config.get("output_name", project_id))
    out_dir = ROOT / "assets" / "generated" / project_id / "static_keyframes"
    out_dir.mkdir(parents=True, exist_ok=True)

    bible = style_bible(config)
    shared = bible_text(bible)
    negative = str(bible.get("negative_prompt", NEGATIVE_PROMPT))
    prompts = []
    for index, (shot_id, shot_desc) in enumerate(DEFAULT_SHOTS, 1):
        prompt = (
            f"{shared} Shot {index}: {shot_desc} "
            "Luxury full-house custom interior, photorealistic, vertical 9:16, 1080x1920, "
            "professional interior photography, low saturation warm grey sample-room color, "
            "clean cabinet lines, realistic floor reflection, hidden LED strips, no text, no watermark."
        )
        prompts.append({"shot_id": shot_id, "filename": f"{shot_id}.png", "prompt": prompt, "negative_prompt": negative})

    prompt_pack = out_dir / "prompt_pack.md"
    plan = out_dir / "generation_plan.json"
    prompt_text = ["# Static Keyframe Prompt Pack", "", f"项目：{project_id}", "", "状态：STATIC_IMAGE_GENERATION_PENDING", ""]
    for item in prompts:
        prompt_text.extend(
            [
                f"## {item['shot_id']}",
                "",
                "中文用途：用于生成同一原创空间的高质量静态关键帧，后续只能制作 L1 样片风格伪漫游。",
                "",
                "英文提示词：",
                "",
                "```text",
                item["prompt"],
                "```",
                "",
                "负面词：",
                "",
                "```text",
                item["negative_prompt"],
                "```",
                "",
            ]
        )
    prompt_pack.write_text("\n".join(prompt_text), encoding="utf-8")
    plan.write_text(
        json.dumps(
            {
                "project_id": project_id,
                "output_name": output_name,
                "generated_source_type": "static_keyframes",
                "generated_capability_level": "L1",
                "status": "STATIC_IMAGE_GENERATION_PENDING",
                "provider": "gpt-image-2",
                "source_images_dir": str(out_dir),
                "prompt_pack": str(prompt_pack),
                "prompts": prompts,
                "note": "本地脚本不能直接调用 gpt-image-2 时只生成 prompt pack，不伪造图片。",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("STATIC_IMAGE_GENERATION_PENDING")
    print(prompt_pack)
    print(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
