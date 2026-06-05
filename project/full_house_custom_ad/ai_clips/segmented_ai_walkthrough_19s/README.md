# segmented_ai_walkthrough_19s AI 分段镜头目录

把 AI 视频平台生成的 5 段竖屏 mp4 放到这个目录，文件名必须如下：

1. `01_entry_wall_cabinet.mp4`
2. `02_living_room_opening.mp4`
3. `03_dining_kitchen_slide.mp4`
4. `04_bedroom_closet_walk.mp4`
5. `05_material_light_close.mp4`

然后运行：

```bash
/Users/wangchao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 full_house_custom_ad/scripts/render_project.py --config full_house_custom_ad/projects/segmented_ai_walkthrough_19s/project.json
```

输出会生成到：

- `full_house_custom_ad/output/segmented_ai_walkthrough_19s.mp4`
- `full_house_custom_ad/output/segmented_ai_walkthrough_19s_preview.jpg`
- `full_house_custom_ad/output/segmented_ai_walkthrough_19s_plan.md`
- `full_house_custom_ad/output/segmented_ai_walkthrough_19s_continuity_report.md`

注意：多个独立 AI clip 拼接默认是 L2：AI 分段空间漫游，不是真正 walkthrough，也不是样片级连续空间漫游。
