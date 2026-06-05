#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_italian_suite_wardrobe_22s as engine


PROJECT_ID = "italian_minimal_pseudo_walkthrough_28s"
ASSET_DIR = ROOT / "assets/generated/italian_minimal_pseudo_walkthrough_28s"
MUSIC = ROOT / "music_library/mp3/3.30 P@k.PX _1pm 12_19 ZMW__ 140平意式极简风全屋定制完工，显大又高级！# 真实生活分享计划 # 意式极简 # 全屋定制 # 高级感的家 # 荆州全屋定制 [7561383493139549491].mp3"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"


SHOTS = [
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/01_living_hero_hook.png",
        0.00,
        4.40,
        "low_suite_push",
        "柜子做到顶，也可能很压抑",
        "PROPORTION COMES FIRST",
        "首帧直接给客厅主价值点，用反常识钩子让业主停留",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/02_entry_axis_reveal.png",
        4.40,
        8.60,
        "dark_entry_push",
        "关键在比例和灯光",
        "LIGHT MAKES IT LIVABLE",
        "从玄关轴线慢慢进入，建立真实看房的入口感",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/03_living_dining_flow.png",
        8.60,
        13.00,
        "closet_depth_push",
        "客餐厅连起来，家才显大",
        "LINES OPEN THE SPACE",
        "打开客餐厅尺度，展示大平层空间秩序",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/04_integrated_cabinet_wall.png",
        13.00,
        17.50,
        "wardrobe_slide",
        "把收纳藏进墙面",
        "STORAGE DISAPPEARS",
        "展示门墙柜一体化、电视墙和隐藏收纳系统",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/05_material_light_detail.png",
        17.50,
        21.10,
        "material_close",
        "收口细节，决定质感",
        "DETAILS DEFINE THE FINISH",
        "用材质、灯带、柜门边线强化高级感和可信度",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/06_walk_in_wardrobe.png",
        21.10,
        24.90,
        "drawer_rise",
        "衣帽间，是家的仪式感",
        "A PRIVATE WARDROBE RITUAL",
        "补充主卧衣帽间功能价值，让全屋定制不止客厅好看",
    ),
    engine.Shot(
        "assets/generated/italian_minimal_pseudo_walkthrough_28s/07_final_living_hero.png",
        24.90,
        28.47,
        "final_hero_settle",
        "意式极简全屋定制",
        "ITALIAN MINIMAL CUSTOM HOME",
        "回到完整客厅主视觉，稳定收尾形成记忆点",
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
                "source": "gpt-image-2",
                "space_type": shot.purpose,
                "suitable_for_showcase": True,
                "suitable_for_pseudo_walkthrough": True,
                "suitable_for_true_walkthrough": False,
                "style_tags": ["italian_minimal", "large_flat", "integrated_cabinet", "warm_gray", "gpt_image_2"],
            },
        )
    bump_manifest(
        MUSIC,
        {
            "asset_type": "music",
            "duration": round(duration, 2),
            "mood": "意式极简、大平层、高级、克制、有空间打开感",
            "rhythm": "28.47秒完整结构，适合舒适观看的伪空间漫游",
            "suitable_for_showcase": True,
            "suitable_for_pseudo_walkthrough": True,
        },
    )
    bump_manifest(
        final,
        {
            "asset_type": "video_output",
            "video_type": "gpt-image-2_keyframes_pseudo_walkthrough",
            "duration": round(duration, 2),
            "resolution": "1080x1920",
            "fps": 60,
            "publishing_note": "不是连续素材生成的真正空间漫游；是高真实关键帧伪空间漫游成片。",
        },
    )
    bump_manifest(
        preview,
        {
            "asset_type": "preview_contact_sheet",
            "video_type": "gpt-image-2_keyframes_pseudo_walkthrough",
        },
    )
    bump_manifest(
        plan,
        {
            "asset_type": "execution_plan",
            "video_type": "gpt-image-2_keyframes_pseudo_walkthrough",
        },
    )
    manifest = load_manifest()
    route_key = "route:italian_minimal_living_entry_dining_cabinet_detail_wardrobe_hero"
    entry = manifest.setdefault(route_key, {})
    entry["asset_type"] = "camera_route"
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["description"] = "客厅价值首帧，玄关轴线进入，客餐厅打开，电视柜墙系统，材质灯光细节，衣帽间，完整客厅收尾"
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    write_manifest(manifest)


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f}s | {shot.image} | {shot.motion} | {shot.caption_cn} | {shot.purpose} |"
        for shot in SHOTS
    )
    plan.write_text(
        f"""# 意式极简大平层伪空间漫游执行方案

本次视频类型：伪空间漫游型 + 高级图片展示型
本次节奏模式：高级广告模式 / 舒适观看
本次视频风格：意式极简大平层 + 门墙柜一体化
本次音乐方向：高级、克制、空间打开感
本次画面关键词：暖灰、深木、灯带、地面反光、整墙柜、客餐厅轴线、衣帽间
本次核心卖点：全屋定制不是柜子越多越好，而是比例、灯光、收纳和空间秩序一起成立
本次原创设计点：用全新 gpt-image-2 关键帧设计“客厅价值首帧 -> 玄关进入 -> 客餐厅打开 -> 柜体系统 -> 材质细节 -> 衣帽间 -> 客厅收尾”的原创路线。
本次目标客户：准备装修 120-180 平大平层、想要高级但担心柜体压抑的中高预算业主。
本次前 5 秒钩子：用“柜子做到顶，也可能很压抑”制造反常识停留，再用“关键在比例和灯光”给解决方向。
本次质量评分：88/100。真实连续漫游素材不足扣分；首帧、观看舒适度、画面统一性、客户心理钩子达到制作门槛。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 时长：{duration:.2f} 秒
- 处理：完整使用，不循环；只做尾部自然淡出。

## 素材判断

- 当前项目没有可发布级真实连续视频、专业 3D 漫游或 AI 连续视频素材，不能交付真正空间漫游。
- 本片按替代方案执行：gpt-image-2 全新高真实关键帧 + 本地高级伪空间漫游。
- 这条片子不使用之前 10 秒参考视频，也不复用旧图。

## 分镜

| 时间 | 素材 | 运镜 | 字幕 | 目的 |
|---|---|---|---|---|
{rows}

## 滤镜

- 克制通透的高级样板间调色，清楚但不硬提亮。
- 灯带轻微 bloom，不做廉价闪白。
- 暗部只救细节，不把阴影抬平成灰雾。
- 深色柜体保留重量感，柜体线条、木纹和地面反光必须看清楚。
- 暗角极轻，只做空间聚焦，不压暗画面。
- 地面反光保持通透，提升空间质感。
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
    video_only = OUT_DIR / "italian_minimal_pseudo_walkthrough_28s_video_only.mp4"
    final = OUT_DIR / "italian_minimal_pseudo_walkthrough_28s.mp4"
    preview = OUT_DIR / "italian_minimal_pseudo_walkthrough_28s_preview.jpg"
    plan = OUT_DIR / "italian_minimal_pseudo_walkthrough_28s_plan.md"
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
