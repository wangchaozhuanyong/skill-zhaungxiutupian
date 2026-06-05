# 评估用例

这些用例用于检查 Skill 是否正确区分图片展示、伪空间漫游、真正空间漫游和样片级连续空间漫游。

## 用户上传样片并说“我要这种视频”

用户：

```text
这是参考视频，我要做出这种感觉，不要图片轮播。
```

期望行为：

- 先判断为样片级连续空间漫游。
- 同时输出 capability level。
- 说明它不是普通图片展示。
- 拆解镜头路径、空间结构、调色、字幕节奏。
- 判断当前素材是否能支撑。
- 如果没有连续视频、3D 漫游或 AI video，不得直接承诺同款。
- 必须说明只能做降级版伪漫游。
- 输出 13 秒连续漫游时间码脚本或同等时长结构。

## 用户只有 6 张静态图

用户：

```text
我只有 6 张图，但想做成参考视频那种走进去的感觉。
```

期望行为：

- 不能说可以做真正 walkthrough。
- capability level 必须是 L1。
- 判断为样片风格伪漫游。
- 输出 Style Bible。
- 输出需要补充的关键帧。
- 明确差距：缺少连续视差、空间一致运动和真实摄影机路径。

## 用户有 13 秒 3D 漫游视频

用户：

```text
我有一条 13 秒 3D 漫游视频，帮我做成参考视频那种高级感。
```

期望行为：

- 判断可以做样片级连续漫游后期。
- capability level 至少是 L3，只有通过连续性检查才可标为 L4。
- 输出调色、节奏、字幕、音乐和导出方案。
- 不转成图片方案。
- 如果要最终标 L4，必须生成并通过人工空间语义复核文件。

## 用户有多个 AI clip

用户：

```text
我有 5 段 AI 生成的视频，拼起来做成样片级漫游。
```

期望行为：

- 默认判断为 L2：AI 分段空间漫游。
- 不能直接说是真正 walkthrough。
- 必须要求或生成连续性检查报告。
- 如果空间、材质、灯光、比例不一致，不得升级为 L4。

## 用户说“不够像样片”

用户：

```text
你做的不像我发的那个样片。
```

期望行为：

- 先诊断是不是因为用了图片轮播。
- 指出是否缺少连续空间视差。
- 指出是否缺少一镜到底路径。
- 给出真漫游补素材方案和伪漫游补救方案。

## L4 目标但没有素材

项目配置：

```text
capability_level=L4
source_video=""
allow_downgrade=false
```

期望行为：

- `render_project.py` 必须先生成 continuity report。
- 返回缺素材或目标无法满足，不得生成假视频。
- 不得自动转 gpt-image-2 伪漫游并称为同款样片级。
- 报告必须说明没有关键帧视觉证据，当前不能通过 L4。

## 单条真实连续视频

项目配置：

```text
source_type=real_video
source_video=/path/to/continuous.mp4
capability_level=L3
```

期望行为：

- `render_project.py` 必须调用 `render_continuous_video_project.py`。
- 输出 mp4、preview、plan、continuity report。
- capability level 至少可为 L3。
- 只有基础视觉门禁、有效人工空间语义复核文件和样片级专项评分 >=85 都通过，才可以最终标为 L4。

## 多个 AI clip 但用户坚持说样片级

用户：

```text
这 5 段 AI 视频帮我拼成样片级一镜到底。
```

期望行为：

- 默认 L2：AI 分段空间漫游。
- 输出“多 clip 拼接”。
- 即使生成了关键帧证据，也不能自动称为 L4。
- 必须说明缺少同一空间连续路径和真实连续视差证明。

## L2 目标但 clip 目录未准备好

项目配置：

```text
source_type=segmented_ai_clips
source_clips_dir=/path/to/empty_or_missing_dir
capability_level=L2
```

期望行为：

- 当前 capability level 必须是 L0。
- `readiness_status` 必须是 `L2_not_ready`。
- 报告必须说明至少需要 2 个 AI video clip。
- 不得把空目录或 1 个 clip 标注为 AI 分段空间漫游。

## continuity_checks 全 true 但缺视觉证据

项目配置：

```text
capability_level=L4
continuity_checks 全部 true
source_video=""
manual_semantic_review_file=output/example_semantic_review.md
```

期望行为：

- 不得通过 L4。
- `--fail-on-overclaim` 必须失败。
- 报告必须说明缺少关键帧视觉证据和有效人工空间语义复核文件。
- 不能只因为 project.json 声明 true 就称为样片级。

## 静态图项目

项目配置：

```text
source_type=static_images
source_images_dir=/path/to/images
capability_level=L1
```

期望行为：

- `render_project.py` 必须调用 `render_static_image_project.py`。
- 输出 L1 样片风格伪漫游视频、preview、plan、continuity report。
- plan 必须写明不是真正 walkthrough，不是 L4。
- 静态图不得升级为 L3/L4。

## L4 基础门禁候选

项目配置：

```text
source_type=real_video
source_video=/path/to/continuous.mp4
capability_level=L4
continuity_checks 全部 true
manual_semantic_review_file=output/example_semantic_review.md
```

期望行为：

- 如果关键帧证据和硬切风险通过，`l4_gate_result` 可为 candidate。
- candidate 不等于 L4 通过。
- `passes_expected_level` 应为 false。
- 只有 `manual_semantic_review_file` 存在且有效、专项评分达标，才允许最终 L4。

## L4 复核文件缺少专项评分

项目配置：

```text
source_type=real_video
source_video=/path/to/continuous.mp4
capability_level=L4
continuity_checks 全部 true
manual_semantic_review_file=output/example_semantic_review.md
样片级专项评分未填写
```

期望行为：

- 不得通过 L4。
- 报告必须说明样片级专项评分未填写或格式无效。
- `sample_level_score_passed` 必须是 false。

## L4 专项评分低于门槛

项目配置：

```text
source_type=real_video
source_video=/path/to/continuous.mp4
capability_level=L4
continuity_checks 全部 true
manual_semantic_review_file=output/example_semantic_review.md
样片级专项评分=84
```

期望行为：

- 不得通过 L4。
- 报告必须说明样片级专项评分低于 85。
- 如果专项评分低于 70，报告必须提示必须降级。

## L4 配置布尔值为 true 但没有复核文件

项目配置：

```text
source_type=real_video
source_video=/path/to/continuous.mp4
capability_level=L4
continuity_checks 全部 true
manual_semantic_review_passed=true
manual_semantic_review_file 缺失或文件不存在
```

期望行为：

- 不得通过 L4。
- `--fail-on-overclaim` 必须失败。
- 报告必须说明 `manual_semantic_review_passed=true` 不能单独作为 L4 通过依据。
- 报告必须指出缺少有效人工空间语义复核文件。

## 验收标准

1. 用户发样片并说“做这种”，Skill 先分析样片类型，而不是直接套图片展示模板。
2. 如果样片是连续 walkthrough，Skill 必须识别为“样片级连续空间漫游”。
3. 没有连续视频、3D 漫游或 AI video 时，Skill 不能承诺做出真正同款。
4. 只有静态图时，Skill 只能输出“样片风格伪漫游”，并说明差距。
5. Skill 必须能输出 13 秒连续漫游时间码脚本。
6. Skill 必须区分图片展示型、伪空间漫游型、真正空间漫游型、样片级连续空间漫游型。
7. Skill 必须输出 L0-L4 capability level。
8. 至少 2 个独立 AI clip 才能标 L2，且不能默认叫样片级。
9. 不要删除 gpt-image-2 高真实关键帧能力，但要防止它错误替代样片级连续漫游目标。
10. 不要恢复低真实感本地程序化 3D 路线。
11. 新规则必须写进 references，并在 SKILL.md 中引用。
12. L4 目标但没有素材时，脚本必须报告缺素材或过度声明失败，不得生成假 L4。
13. `source_video` 存在且是连续视频来源时，`render_project.py` 必须调用 continuous renderer。
14. 静态图项目必须调用 L1 static renderer 或返回明确缺口，不得冒充完成。
15. continuity report 必须包含关键帧拼图、最大跳变帧对、抽帧数量、硬切风险、运动连续性风险、L4 门禁结果、素材就绪状态、人工语义复核文件状态和样片级专项评分状态。
16. `continuity_checks` 全 true 但没有视觉证据或有效人工语义复核文件时，不得通过 L4。
17. `manual_semantic_review_passed=true` 但没有有效 `manual_semantic_review_file` 时，不得通过 L4。
18. L4 人工复核文件没有样片级专项评分或评分低于 85 时，不得通过 L4。
19. L2 目标少于 2 个 clip 时，当前能力必须是 L0，素材就绪状态必须是 L2_not_ready。
