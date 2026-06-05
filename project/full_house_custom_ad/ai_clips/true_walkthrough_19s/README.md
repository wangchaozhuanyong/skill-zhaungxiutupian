# true_walkthrough_19s AI 连续镜头目录

把 AI 视频平台生成的 5 段竖屏 mp4 放到这个目录，文件名必须如下：

1. `01_entry_wall_cabinet.mp4`
2. `02_living_room_opening.mp4`
3. `03_dining_kitchen_slide.mp4`
4. `04_bedroom_closet_walk.mp4`
5. `05_material_light_close.mp4`

然后运行：

```bash
/Users/wangchao/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 full_house_custom_ad/scripts/assemble_true_walkthrough_ai_clips.py
```

输出会生成到：

- `full_house_custom_ad/output/true_walkthrough_ai_19s.mp4`
- `full_house_custom_ad/output/true_walkthrough_ai_19s_preview.jpg`
- `full_house_custom_ad/output/true_walkthrough_ai_19s_plan.md`
