#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_italian_suite_wardrobe_22s as engine


PROJECT_ID = "oriental_gallery_walkthrough_19s"
ASSET_DIR = ROOT / "assets/generated/oriental_gallery_walkthrough_19s"
MUSIC = ROOT / "music_library/mp3/1.74 _3pm 10_06 RKW__ M@J.vs 这种极简调性的全屋定制落地效果真的是越简单越耐看# 木作 # 空间设计美学 # 全屋定制 # 佛山全屋定制 # 门墙柜一体化 [7550252225508756770].mp3"
OUT_DIR = ROOT / "output"
MANIFEST_PATH = ROOT / "asset_manifest.json"


SHOTS = [
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/01_entry_reveal.png",
        0.00,
        3.20,
        "dark_entry_push",
        "越简单，越耐看",
        "LESS, BUT LASTING",
        "玄关暗部入场，柜体边缘建立看房入口",
    ),
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/02_integrated_living_wall.png",
        3.20,
        6.80,
        "low_suite_push",
        "整体感，才是高级感",
        "DESIGNED AS A WHOLE",
        "展示门墙柜一体化客厅主视觉",
    ),
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/03_living_dining_kitchen.png",
        6.80,
        10.40,
        "wardrobe_slide",
        "把收纳藏进墙面",
        "STORAGE, QUIETLY BUILT IN",
        "客餐厨横向打开，展示全屋秩序",
    ),
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/04_study_tea_room.png",
        10.40,
        13.90,
        "closet_depth_push",
        "空间安静，生活变轻",
        "A CALMER WAY TO LIVE",
        "东方现代书房茶区，补足生活方式",
    ),
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/05_material_light_detail.png",
        13.90,
        16.80,
        "material_close",
        "细节，决定质感",
        "DETAILS DEFINE THE FINISH",
        "木饰面、岩板、灯带和柜门收口细节",
    ),
    engine.Shot(
        "assets/generated/oriental_gallery_walkthrough_19s/06_final_hero.png",
        16.80,
        19.44,
        "final_hero_settle",
        "全屋定制，不止好看",
        "MORE THAN BEAUTIFUL",
        "完整空间主视觉收尾，形成品牌记忆点",
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


def update_manifest(duration: float) -> None:
    for shot in SHOTS:
        bump_manifest(
            ROOT / shot.image,
            {
                "asset_type": "image",
                "space_type": shot.purpose,
                "suitable_for_showcase": True,
                "suitable_for_walkthrough": True,
                "style_tags": ["modern_oriental", "art_gallery_home", "door_wall_cabinet", "gpt_image_2"],
            },
        )
    bump_manifest(
        MUSIC,
        {
            "asset_type": "music",
            "duration": round(duration, 2),
            "mood": "极简、耐看、克制、门墙柜一体化",
            "rhythm": "19.44秒完整结构，适合慢推进伪空间漫游",
            "suitable_for_showcase": True,
            "suitable_for_walkthrough": True,
        },
    )
    manifest = load_manifest()
    route_key = "route:oriental_gallery_entry_living_dining_study_material_hero"
    entry = manifest.setdefault(route_key, {})
    entry["asset_type"] = "camera_route"
    entry["usage_count"] = int(entry.get("usage_count", 0)) + 1
    entry["last_used"] = date.today().isoformat()
    entry["description"] = "玄关暗部入场，门墙柜一体客厅，客餐厨打开，东方书房茶区，材质灯带，完整大平层主视觉收尾"
    entry["projects"] = sorted(set(entry.get("projects", [])) | {PROJECT_ID})
    write_manifest(manifest)


def write_plan(plan: Path, final: Path, preview: Path, duration: float) -> None:
    rows = "\n".join(
        f"| {shot.start:.2f}-{shot.end:.2f}s | {shot.image} | {shot.motion} | {shot.caption_cn} | {shot.purpose} |"
        for shot in SHOTS
    )
    plan.write_text(
        f"""# 东方现代艺术馆住宅伪空间漫游执行方案

本次视频类型：伪空间漫游型 + 图片展示型
本次节奏模式：高级广告模式 / 舒适观看
本次视频风格：东方现代艺术馆住宅 + 门墙柜一体化
本次音乐方向：极简、耐看、克制、适合慢推进
本次画面关键词：玄关入场、门墙柜一体、客厅轴线、餐厨打开、材质灯光收尾
本次核心卖点：越简单越耐看，全屋定制的高级感来自整体秩序
本次原创设计点：用 gpt-image-2 生成全新东方现代关键帧，不复用深色酒店衣帽间路线，也不冒充真正连续视频。

## 音乐

- 音乐：`{MUSIC.relative_to(ROOT)}`
- 时长：{duration:.2f} 秒
- 处理：完整使用，不循环；只做尾部自然淡出。

## 素材判断

- 当前本机真实连续视频不足以支撑 19.44 秒真正空间漫游。
- 本片按替代方案执行：gpt-image-2 新关键帧 + 本地高级伪空间漫游。
- 已生成 6 张新图：`{ASSET_DIR.relative_to(ROOT)}`

## 分镜

| 时间 | 素材 | 运镜 | 字幕 | 目的 |
|---|---|---|---|---|
{rows}

## 滤镜

- 低饱和暖灰。
- 木色沉稳，灯带轻微 bloom。
- 地面反光通透，暗部保留细节。
- 字幕少而高级，不遮挡核心空间。

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
    video_only = OUT_DIR / "oriental_gallery_walkthrough_19s_video_only.mp4"
    final = OUT_DIR / "oriental_gallery_walkthrough_19s.mp4"
    preview = OUT_DIR / "oriental_gallery_walkthrough_19s_preview.jpg"
    plan = OUT_DIR / "oriental_gallery_walkthrough_19s_plan.md"
    engine.render_video(video_only, duration)
    engine.mux_audio(video_only, final, duration)
    engine.make_preview(final, preview, duration)
    update_manifest(duration)
    write_plan(plan, final, preview, duration)
    print(final)
    print(video_only)
    print(preview)
    print(plan)
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
