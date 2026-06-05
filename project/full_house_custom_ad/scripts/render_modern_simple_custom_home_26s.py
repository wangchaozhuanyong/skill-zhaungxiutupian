#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_italian_suite_wardrobe_22s as engine


PROJECT_ID = "modern_simple_custom_home_26s"
ASSET_DIR = ROOT / "assets/generated/modern_simple_custom_home_26s"
MUSIC = ROOT / "music_library/mp3/9.99 05_15 q@r.Eu _8pm RkC__ 简约风全屋定制落地实拍，统一色系的家真的干净通透，百看不腻# 全屋定制 # 简约风装修 # 现代简约 # 荆州全屋定制 # 餐边柜 [7594398841790254726].mp3"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"


SHOTS = [
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/01_living_hero_hook.png",
        0.00,
        3.80,
        "low_suite_push",
        "简约风，最怕出租屋感",
        "SIMPLE, BUT NEVER PLAIN",
        "首帧展示完整客厅主视觉，用反差钩子抓住准备装修客户",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/02_entry_storage_axis.png",
        3.80,
        7.50,
        "dark_entry_push",
        "先看比例，再看柜体",
        "PROPORTION COMES FIRST",
        "从玄关柜体边缘进入，建立收纳和空间秩序",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/03_living_dining_flow.png",
        7.50,
        11.80,
        "closet_depth_push",
        "统一色系，家才完整",
        "DESIGNED AS ONE",
        "客餐厅打开，展示统一色系和整体空间关系",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/04_dining_sideboard_focus.png",
        11.80,
        15.80,
        "wardrobe_slide",
        "把收纳藏进生活",
        "STORAGE, QUIETLY BUILT IN",
        "突出餐边柜系统、隐藏收纳和玻璃展示比例",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/05_kitchen_cabinet_system.png",
        15.80,
        19.50,
        "closet_depth_push",
        "好看，也要好用",
        "BEAUTY WITH FUNCTION",
        "展示厨房橱柜系统和全屋定制的功能落地",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/06_master_wardrobe.png",
        19.50,
        23.20,
        "drawer_rise",
        "柜体不压抑，靠比例",
        "LIGHTNESS IN PROPORTION",
        "主卧衣柜补充生活方式和多空间完整度",
    ),
    engine.Shot(
        "assets/generated/modern_simple_custom_home_26s/07_material_detail_finish.png",
        23.20,
        26.85,
        "material_close",
        "越简单，越考验细节",
        "DETAILS DEFINE THE FINISH",
        "材质和收口细节收尾，留下全屋定制专业记忆点",
    ),
]


def configure_engine() -> None:
    engine.PROJECT_ID = PROJECT_ID
    engine.ASSET_DIR = ASSET_DIR
    engine.MUSIC = MUSIC
    engine.SHOTS = SHOTS


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def write_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bump_manifest(path: Path, updates: dict) -> None:
    manifest = load_manifest()
    rel = str(path.relative_to(ROOT)) if path.is_file() else str(path)
    entry = manifest.setdefault(rel, {})
    if path.is_file():
        entry["hash"] = engine.file_hash(path)
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    entry.update(updates)
    write_manifest(manifest)


def update_manifest(duration: float, final: Path, preview: Path, plan: Path) -> None:
    for shot in SHOTS:
        bump_manifest(
            ROOT / shot.image,
            {
                "asset_type": "image",
                "source": "built-in image_gen / gpt-image-2 workflow",
                "space_type": shot.purpose,
                "suitable_for_showcase": True,
                "suitable_for_pseudo_walkthrough": True,
                "suitable_for_true_walkthrough": False,
                "style_tags": [
                    "modern_simple",
                    "unified_color",
                    "whole_house_custom",
                    "sideboard",
                    "restrained_showroom_grade",
                    "new_keyframes",
                ],
            },
        )
    bump_manifest(
        MUSIC,
        {
            "asset_type": "music",
            "duration": round(duration, 2),
            "mood": "现代简约、统一色系、干净耐看、全屋定制落地感",
            "rhythm": "26.85秒完整结构，适合高级图片展示和伪空间漫游",
            "suitable_for_showcase": True,
            "suitable_for_pseudo_walkthrough": True,
        },
    )
    bump_manifest(
        final,
        {
            "asset_type": "video_output",
            "video_type": "new_keyframes_pseudo_walkthrough_showcase",
            "duration": round(duration, 2),
            "resolution": "1080x1920",
            "fps": 60,
            "publishing_note": "gpt-image-2新关键帧 + 本地高级伪空间漫游/图片展示成片；不是连续视频素材的真正空间漫游。",
        },
    )
    bump_manifest(preview, {"asset_type": "preview_contact_sheet", "video_type": "new_keyframes_showcase"})
    bump_manifest(plan, {"asset_type": "execution_plan", "video_type": "new_keyframes_showcase"})

    manifest = load_manifest()
    route_key = "route:modern_simple_entry_living_dining_sideboard_kitchen_wardrobe_detail"
    entry = manifest.setdefault(route_key, {})
    entry["asset_type"] = "camera_route"
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["description"] = "客厅主视觉钩子，玄关收纳轴线，客餐厅统一色系，餐边柜重点，厨房橱柜系统，主卧衣柜，材质收口细节"
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    write_manifest(manifest)


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f}s | {shot.image} | {shot.motion} | {shot.caption_cn} | {shot.purpose} |"
        for shot in SHOTS
    )
    plan.write_text(
        f"""# 现代简约统一色系全屋定制短视频执行方案

本次视频类型：伪空间漫游型 + 高级图片展示型
本次节奏模式：高级广告模式 / 舒适观看
本次视频风格：克制简约全屋定制 / 统一色系样板间质感
本次音乐方向：简约、干净、耐看、有全屋落地感
本次画面关键词：统一色系、门墙柜一体、餐边柜、客餐厅、隐藏收纳、材质细节、克制通透
本次核心卖点：同样是简约风，真正高级的是比例、收纳和材质统一
本次原创设计点：避开上一条意式极简大平层路线，改为入户秩序、客餐厅统一、餐边柜功能、厨房收纳、主卧衣柜、材质细节收尾。
本次目标客户：准备装修改善住宅、喜欢简约耐看、担心柜子做多显压抑的中高预算业主。
本次前 5 秒钩子：简约风，最怕出租屋感。
本次质量评分：90/100。画面和节奏达到制作门槛；真实连续视频素材不足，因此明确为伪空间漫游/图片展示型。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 时长：{duration:.2f} 秒
- 处理：完整使用，不循环；只做尾部自然淡出。

## 素材判断

- 当前项目没有可发布级真实连续视频、专业 3D 漫游或 AI 连续视频素材，不能交付真正空间漫游。
- 本片按替代方案执行：gpt-image-2 新关键帧 + 本地高级伪空间漫游/图片展示。
- 这条片子不复用上一条意式极简旧图、旧音乐和旧路线。

## 分镜

| 时间 | 素材 | 运镜 | 字幕 | 目的 |
|---|---|---|---|---|
{rows}

## 滤镜

- 全屋定制采用克制通透的高级样板间调色。
- 画面清楚但不硬提亮，不发白、不发灰、不失去暗部层次。
- 深色柜体保留重量感，浅色空间保留材质感。
- 灯带轻微 bloom，地面反光通透，木饰面、岩板和柜门缝清晰。
- 字幕克制，放在画面下方，不遮挡柜体和空间主视觉。

## 输出

- 最终视频：`{final.relative_to(ROOT)}`
- 预览拼图：`{preview.relative_to(ROOT)}`
- 素材记录：`{MANIFEST_PATH.relative_to(ROOT)}`
""",
        encoding="utf-8",
    )


def main() -> None:
    configure_engine()
    duration = min(engine.get_duration(MUSIC), SHOTS[-1].end)
    video_only = OUT_DIR / "modern_simple_custom_home_26s_video_only.mp4"
    final = OUT_DIR / "modern_simple_custom_home_26s.mp4"
    preview = OUT_DIR / "modern_simple_custom_home_26s_preview.jpg"
    plan = OUT_DIR / "modern_simple_custom_home_26s_plan.md"
    engine.render_video(video_only, duration)
    engine.mux_audio(video_only, final, duration)
    engine.make_preview(final, preview, duration)
    write_plan(plan, final, preview, duration)
    update_manifest(duration, final, preview, plan)
    print(final)
    print(video_only)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
