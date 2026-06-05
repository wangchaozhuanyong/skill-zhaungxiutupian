# VERSION STATUS

当前版本：v1.0-final-auto-assets

当前增量：v1.1-l1-auto-render

后续增量：v1.1-l2-l3-fal-backend

## 已完成能力

- L1：静态图 / gpt-image-2 关键帧 / 图片素材，可以制作样片风格伪漫游或高级图片展示。
- L2：多个独立 AI video clip，可以制作 AI 分段空间漫游。
- L3：单条真实连续视频、专业 3D 漫游导出、单条连续 AI video，可以制作真正空间漫游后期。
- L4：样片级连续空间漫游，必须通过连续性检查、视觉证据、专项评分和人工空间语义复核后才能标记。
- Auto Assets：用户不提供素材时，系统会自动尝试生成素材，按 L3 -> L2 -> L1 顺序选择最高可执行版本。

## 不承诺能力

- 不承诺从 0 全自动稳定生成 L4 样片级连续空间漫游。
- 不承诺静态图变成真正 walkthrough。
- 不承诺多个独立 AI clip 拼接后直接成为样片级一镜到底。
- 不承诺脚本能自动语义理解电视墙、沙发、餐桌、地面、灯光是否完全一致；L4 必须人工复核。

## L4 成立条件

L4 必须同时满足：

1. 素材来源是单条真实连续视频、专业 3D 漫游导出或单条连续 AI video；
2. continuity report 生成成功；
3. 关键帧视觉证据可用；
4. 最大跳变帧对可审查；
5. hard_cut_risk 不是 high；
6. motion_continuity_risk 不是 high；
7. continuity_checks 全部通过；
8. 样片级专项评分 >= 85；
9. 有效人工空间语义复核文件通过；
10. 复核文件中的 source_video_hash 与实际源视频一致。

## 自动素材生成原则

当用户不提供素材时：

1. 优先尝试生成单条连续 AI video，成功则进入 L3 候选；
2. 如果不可用，尝试生成多个 AI video clip，成功则进入 L2；
3. 如果不可用，尝试生成 gpt-image-2 静态关键帧，成功则进入 L1；
4. 如果所有生成后端都不可用，输出 GENERATOR_NOT_READY；
5. 不得第一轮要求用户上传 source_video。

## 冻结原则

v1.0 完成后，除非出现以下问题，否则不再继续修改 v1.0：

- L1/L2/L3 入口无法运行；
- 无素材时没有进入自动生成模式；
- L4 被错误标记；
- README 示例命令明显错误；
- 输出 plan 等级命名错误；
- validator 不能生成报告；
- 核心依赖缺失导致脚本无法启动。

其他优化进入 v1.1。

## v1.1 L1 增量

v1.1 第一阶段只打通 L1 自动出片链路：

1. `generate_gpt_image_keyframes.py` 使用 OpenAI Image API 生成静态关键帧；
2. `generate_auto_project_assets.py` 在 `static_keyframes` 阶段优先调用真实图片生成脚本；
3. 图片生成成功后写入 `source_type=static_images`、`capability_level=L1` 和 `source_images_dir`；
4. `render_project.py` 继续调用 `render_static_image_project.py` 输出 L1 样片风格伪漫游 MP4；
5. 若未配置 `OPENAI_API_KEY` 或图片生成失败，只输出 `GENERATOR_NOT_READY` / prompt pack，不伪造图片。

v1.1 L1 不改变 L4 门禁，不把静态关键帧视频称为真正 walkthrough。

## v1.1 L2/L3 增量

v1.1 后续阶段接顺 FAL 视频生成后端：

1. `fal_video_provider.py` 使用 FAL queue HTTP API 直连生成视频；
2. `generate_segmented_ai_walkthrough_clips_fal.py` 不再依赖外部 `plugins/video_gen/fal.py`，有 `FAL_KEY` 即可尝试生成多个 AI clip；
3. 多个 AI clip 成功后只能标 L2：AI 分段空间漫游；
4. `generate_continuous_ai_walkthrough_fal.py` 使用同一 provider 生成单条连续 AI video；
5. 单条连续 AI video 成功后只能进入 L3 candidate，不自动标 L4；
6. 未配置 `FAL_KEY` 时输出 `GENERATOR_NOT_READY`，不要求用户上传素材。
