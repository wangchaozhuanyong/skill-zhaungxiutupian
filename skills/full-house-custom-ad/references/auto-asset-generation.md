# 自动原创素材生成规则

当用户明确不提供素材，或要求系统自己制作素材时，必须进入自动原创素材生成模式。默认使用 Codex 交互式生成；API 后端只用于用户明确要求无人值守、批量自动化或愿意配置 API key 的场景。

不要把 `OPENAI_API_KEY` / `FAL_KEY` 当成日常默认要求。缺少 API key 只代表脚本无人值守后端未就绪，不代表 Codex 交互模式不能继续制作 L1。

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

## 默认模式：Codex 交互式生成

用户直接在 ChatGPT/Codex 里让我们做时，默认流程是：

1. Codex 先设计 Style Bible、分镜和关键帧提示词；
2. Codex 使用当前会话可用的图片生成能力生成或准备静态关键帧；
3. 保存关键帧到项目素材目录；
4. 调用本地 L1 renderer 输出样片风格伪漫游 MP4；
5. 全程不要求用户配置额外 API。

如果当前会话没有视频生成工具，默认最高稳定可执行等级是 L1。不得因为缺少 FAL API 就要求用户上传 `source_video`。

## 自动生成模式

`strict_true_walkthrough` 用于真正空间漫游硬目标：

- 触发：用户说真正空间漫游、不要图片轮播、不要分段 clip、不接受降级、必须像走进房子一样。
- 行为：只尝试单条连续 AI video / L3 路径。
- 成功：`source_type=continuous_ai_video`，capability level 为 L3 candidate，可称为真正空间漫游型。
- 失败：输出 `L3_GENERATOR_NOT_READY` / `GENERATOR_NOT_READY`，不得降级 L2/L1，不得要求用户上传素材。

`best_effort` 用于最高可执行测试目标：

- 触发：用户说自己生成素材、做测试片、最高质量版本、尽量做出来。
- 行为：先尝试 L3，再尝试 L2，最后尝试 L1。
- 成功：按真实素材能力标注 L3/L2/L1。
- 降级：必须写明 `auto_downgraded=true` 和最终正确命名。

## 可选模式：API 无人值守生成

只有用户明确选择本地脚本无人值守、批量自动化或愿意配置 API key 时，才使用以下顺序：

1. `continuous_ai_video` 可用：生成单条连续 AI video，`source_type=continuous_ai_video`，最高进入 L3 候选。
2. `segmented_ai_clips` 可用：生成多个独立 AI video clip，`source_type=segmented_ai_clips`，只能标 L2。
3. `static_keyframes` / OpenAI Image API 可用：调用 `generate_gpt_image_keyframes.py` 生成静态关键帧，`source_type=static_images`，只能标 L1。
4. 所有 API 无人值守后端不可用：输出 `GENERATOR_NOT_READY`，但仅表示 API 无人值守模式不可用；Codex 交互模式仍可继续做 L1。

## 禁止行为

- 禁止在自动素材生成模式的第一轮要求用户上传真实连续视频。
- 禁止把 L1 静态关键帧运镜称为真正 walkthrough。
- 禁止把 L2 多段 AI clip 拼接称为真正空间漫游或样片级一镜到底。
- 禁止把 L3 自动称为 L4。
- 禁止伪造 OpenAI Image API 已经生成图片；若本地不能直接生成图片，只能输出 prompt pack 和 `STATIC_IMAGE_GENERATION_PENDING` / `GENERATOR_NOT_READY`。
- 禁止把缺少 API key 说成“无法制作视频”；应切回 Codex 交互式生成，先做 L1。

## v1.1 L1 自动出片

v1.1 第一阶段优先打通 L1：

```text
project.json
-> generate_auto_project_assets.py
-> generate_gpt_image_keyframes.py
-> OpenAI Image API 生成静态关键帧
-> render_static_image_project.py
-> 输出 L1 样片风格伪漫游 MP4
```

如果用户选择 API 无人值守模式但没有 `OPENAI_API_KEY`，必须保留 prompt pack 并输出 `GENERATOR_NOT_READY`，不得假装已生成图片。若用户是在 Codex 里直接调用，则切回 Codex 交互模式，由 Codex 当前会话生成或准备关键帧。图片生成成功后，成片仍然只能命名为 L1 样片风格伪漫游。

## v1.1 L2/L3 FAL 后端

v1.1 已内置 FAL queue provider：

- `generate_segmented_ai_walkthrough_clips_fal.py`：有 `FAL_KEY` 时可直接生成多个 AI video clip，成功后标 L2。
- `generate_continuous_ai_walkthrough_fal.py`：有 `FAL_KEY` 时可直接生成单条连续 AI video，成功后标 L3 candidate。
- 两者都不得自动标 L4。
- 未配置 `FAL_KEY` 时输出 `GENERATOR_NOT_READY`，不要求用户上传素材，也不阻止 Codex 交互模式继续做 L1。

## 正确输出

自动素材生成模式下，必须输出：

```text
自动素材生成模式：已启用
生成模式：Codex 交互式生成 / API 无人值守模式
自动生成模式：strict_true_walkthrough / best_effort
用户是否提供素材：否
素材来源：自动生成
本次将自动生成的素材类型：
可用生成后端：
最高可执行 capability level：
是否发生自动降级：
是否允许自动降级：
最终输出等级命名：
是否需要额外 API：
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

## 音乐和后端能力

自动生成 L3 时，单条连续视频优先于音乐完整长度。如果 continuous_ai_video 后端最大只支持 8-10 秒，就生成 8-10 秒单条连续视频，音乐裁切或淡出；不得为了完整使用 19 秒音乐而要求用户提供 19 秒视频。

L2 多 clip 和 L1 静态关键帧可以按音乐完整结构设计更长时长，但仍必须让画面有足够停留时间。
