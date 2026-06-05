# Codex 交互式素材生成规则

Codex 交互式素材生成模式是日常默认模式。用户在 ChatGPT/Codex 里直接说“你自己做”“不要让我接 API”“我已经买了会员，直接用你做”时，必须优先使用当前 Codex 会话能用的生成能力和本地渲染脚本，而不是要求用户配置 `OPENAI_API_KEY` 或 `FAL_KEY`。

## 默认原则

- 默认不要求用户接 OpenAI API、FAL API 或其他额外付费后端。
- API 自动后端只用于无人值守、批量脚本化生产，必须由用户明确选择。
- 用户直接调用 Codex 时，先用 Codex 当前会话生成/准备素材，再本地渲染。
- 不得因为没有 `OPENAI_API_KEY` / `FAL_KEY` 就停止任务或要求用户上传 `source_video`。

## 默认可执行路径

当前 Codex 会话如果可生成图片：

1. 先生成原创 Style Bible；
2. 生成 4-8 张同一空间静态关键帧；
3. 保存到 `project/full_house_custom_ad/assets/generated/<project_id>/static_keyframes/`；
4. 生成或更新 L1 project.json；
5. 调用 `render_static_image_project.py` 或 `render_project.py`；
6. 输出 L1 样片风格伪漫游 MP4。

这个路径最高只能标 L1，不得叫真正 walkthrough 或 L4。

## 视频生成边界

如果当前 Codex 会话没有可用视频生成工具：

- 不承诺直接生成 L2/L3 视频素材；
- 可先输出 L1 成片；
- 同时说明 L2/L3 需要可用的会话视频生成工具、用户提供连续视频、或用户明确选择 API 自动后端。
- 如果用户要求 `strict_true_walkthrough` 且拒绝 API / 上传素材，必须输出 `SESSION_VIDEO_PROVIDER_NOT_AVAILABLE`，不得要求 `OPENAI_API_KEY` / `FAL_KEY`，不得自动降级 L2/L1。

如果当前 Codex 会话未来具备视频生成工具：

- 单条连续视频才可能进入 L3 candidate；
- 多段独立视频 clip 只能标 L2；
- L4 仍需连续性报告、视觉证据、专项评分和人工复核。

## 插件视频 provider

当用户明确要求使用视频插件（例如 `hyperframes`）时，必须先检查该插件是否在当前 Codex 会话中暴露为可调用工具。

- 如果可调用：可作为 L3 单条连续视频 provider。
- 如果不可调用：输出 `SESSION_VIDEO_PROVIDER_NOT_AVAILABLE`，说明插件名可见不等于工具已暴露。
- 不得把插件未暴露转写成需要 `OPENAI_API_KEY` / `FAL_KEY`。

## API 自动后端的地位

以下脚本是可选自动化能力，不是日常默认要求：

- `generate_gpt_image_keyframes.py`
- `generate_segmented_ai_walkthrough_clips_fal.py`
- `generate_continuous_ai_walkthrough_fal.py`

只有用户明确说“我要无人值守批量生成”“我要脚本自动跑”“我愿意配置 API key”时，才要求配置：

- `OPENAI_API_KEY`
- `FAL_KEY`

## 正确表达

当用户拒绝接 API 时，应输出：

```text
生成模式：Codex 交互式生成
是否需要额外 API：否
本次最高稳定可执行等级：L1 样片风格伪漫游
L2/L3 条件：需要会话视频生成工具、用户连续视频，或用户明确选择 API 自动后端
是否要求上传 source_video：否
```

## 禁止表达

- “没有 OPENAI_API_KEY，所以不能做。”
- “没有 FAL_KEY，所以你必须上传 source_video。”
- “你不接 API 就无法生成素材。”
- “静态关键帧成片是真正 walkthrough。”
