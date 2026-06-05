# 自动原创素材生成规则

当用户明确不提供素材，或要求系统自己制作素材时，必须进入自动原创素材生成模式。目标是自动生成 L1/L2/L3 中最高可执行版本，而不是第一轮要求用户上传 `source_video`。

## 触发表达

用户出现以下任意表达，视为启用自动原创素材生成模式：

- 我不提供素材
- 你自己制作素材
- 自动生成素材
- 不要让我上传视频
- 做一个测试片
- 直接做一个原创空间
- 从零做一个装修视频
- 没有素材，你自己生成
- 我需要他自己制作素材

## 生成优先级

1. `continuous_ai_video` 可用：生成单条连续 AI video，`source_type=continuous_ai_video`，最高进入 L3 候选。
2. `segmented_ai_clips` 可用：生成多个独立 AI video clip，`source_type=segmented_ai_clips`，只能标 L2。
3. `static_keyframes` / `gpt-image-2` 可用：生成静态关键帧，`source_type=static_images`，只能标 L1。
4. 所有生成后端不可用：输出 `GENERATOR_NOT_READY`。

## 禁止行为

- 禁止在自动素材生成模式的第一轮要求用户上传真实连续视频。
- 禁止把 L1 静态关键帧运镜称为真正 walkthrough。
- 禁止把 L2 多段 AI clip 拼接称为真正空间漫游或样片级一镜到底。
- 禁止把 L3 自动称为 L4。
- 禁止伪造 gpt-image-2 已经生成图片；若本地不能直接生成图片，只能输出 prompt pack 和 `STATIC_IMAGE_GENERATION_PENDING`。

## 正确输出

自动素材生成模式下，必须输出：

```text
自动素材生成模式：已启用
用户是否提供素材：否
素材来源：自动生成
本次将自动生成的素材类型：
可用生成后端：
最高可执行 capability level：
是否发生自动降级：
最终输出等级命名：
GENERATOR_NOT_READY 状态：
如果不能生成，原因：
```

## L4 边界

v1.0 不承诺从 0 稳定生成 L4。L4 仍然必须满足：

- 素材来源是单条真实连续视频、专业 3D 漫游导出或单条连续 AI video。
- 生成 continuity report。
- 关键帧视觉证据和最大跳变帧对可审查。
- hard_cut_risk 与 motion_continuity_risk 不是 high。
- continuity_checks 全部通过。
- 样片级专项评分 >= 85。
- 有效人工空间语义复核文件通过，且 source_video_hash 匹配。
