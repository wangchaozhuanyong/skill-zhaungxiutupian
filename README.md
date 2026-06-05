# skill-zhaungxiutupian

装修短视频导演 skill 源码备份仓库。

这个仓库保存两部分内容：

- `skills/full-house-custom-ad/`：Codex skill 规则、参考规则、默认启动提示。
- `project/full_house_custom_ad/`：本地视频制作脚本、项目目录结构和素材记录入口。

## 安装 Skill

把 skill 目录复制到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills/full-house-custom-ad
rsync -a skills/full-house-custom-ad/ ~/.codex/skills/full-house-custom-ad/
```

之后可以这样调用：

```text
使用 $full-house-custom-ad，任务是：先选音乐，再用 gpt-image-2 生成新图片，最后本地制作成抖音竖屏高级装修视频。先给我方案，确认后再制作。
```

日常在 Codex 里直接调用 skill 时，默认不需要你配置 `OPENAI_API_KEY`、`FAL_KEY` 或其他额外 API。Codex 会先用当前会话可用的生成能力设计/准备素材，再调用本地脚本渲染成片。API 后端只用于你明确要求“脚本无人值守自动跑”“批量生产”“我愿意配置 API key”的场景。

如果你不想接 API，可以这样说：

```text
使用 $full-house-custom-ad，任务是：不接 API，直接由 Codex 生成素材并制作一条 L1 样片风格伪漫游装修短视频。先给我方案，确认后再制作。
```

## 本地项目

本地制作脚本在：

```text
project/full_house_custom_ad/scripts/
```

首次运行脚本前建议安装本地依赖：

```bash
python3 -m pip install -r requirements.txt -t project/full_house_custom_ad/.deps
```

通用入口：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_l4_target_missing_assets/project.json --validate-only --allow-downgrade
```

上面这个命令只用于检查 L4 目标模板，不会直接生成视频；报告会说明当前缺素材，不能通过 L4。样片级连续空间漫游必须先填写真实连续视频、专业 3D 漫游导出或单条连续 AI video。

如果只是查看 L4 缺素材报告，可以使用 `--allow-downgrade`。如果要验证系统是否会拦截 L4 过度声明，请去掉 `--allow-downgrade`，此时不满足 L4 会返回失败码。

自动生成素材入口一：无用户素材，自动生成真正空间漫游 L3 候选：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_self_generated_walkthrough/project.json
```

这个入口用于 `strict_true_walkthrough`：当用户不提供素材，但明确要求“真正空间漫游型”“不要图片轮播”“不接受降级”时，只尝试生成单条 `continuous_ai_video`。成功后进入 L3 真正空间漫游候选；失败后输出 `L3_GENERATOR_NOT_READY` / `GENERATOR_NOT_READY`，不会自动降级 L2/L1，也不会第一轮要求用户上传 `source_video`。

默认模板使用 `generation_execution_mode=codex_session`。它不会要求 `OPENAI_API_KEY` / `FAL_KEY`，而是代表“必须在当前 Codex 会话里有可调用的视频生成工具，或已暴露可调用的视频插件，例如 hyperframes”。如果当前会话没有这类 provider，会输出 `SESSION_VIDEO_PROVIDER_NOT_AVAILABLE`。

对应关键配置字段：

```text
auto_generate_assets=true
generation_execution_mode=codex_session
auto_generation_mode=strict_true_walkthrough
allow_auto_downgrade=false
session_video_provider_order=codex_video,hyperframes
```

自动生成素材入口二：无用户素材，自动生成最高可执行版本：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_self_generated_best_effort/project.json
```

这个入口用于 `best_effort`：当用户说“你自己生成素材”“做测试片”“尽量做出最高质量版本”时，按 L3 -> L2 -> L1 尝试最高可执行版本。只有这里才允许自动降级，但必须写明最终 capability level 和正确命名。

对应关键配置字段：

```text
auto_generate_assets=true
auto_generation_mode=best_effort
allow_auto_downgrade=true
```

这里的 `render_project.py` 是本地脚本无人值守入口，不能直接调用 Codex 聊天窗口里的会员能力。日常让 Codex 交互式制作时，不需要先跑这个 API 入口。

Codex 交互式自动素材生成的默认顺序是：

- 设计 Style Bible、空间路线和关键帧提示词。
- 当前会话可生成图片时，生成或准备同一空间静态关键帧。
- 调用本地 L1 renderer 输出样片风格伪漫游 MP4。
- 不要求用户上传 `source_video`，也不要求配置额外 API。

本地脚本无人值守模式的后端顺序是：

- `strict_true_walkthrough`：只尝试 `continuous_ai_video`，不自动降级。
- `best_effort`：`continuous_ai_video` 可用时生成 L3 candidate；不可用再尝试 `segmented_ai_clips` L2；再不可用才尝试 `static_keyframes` / `gpt-image-2` L1。
- 所有 API 后端不可用：输出 `GENERATOR_NOT_READY`，生成 auto assets report，不会第一轮要求用户上传 `source_video`。这个状态只代表脚本无人值守后端未就绪，不代表 Codex 交互模式不能做 L1。

如果你明确要使用 API 无人值守 strict 模式，使用单独模板：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_self_generated_walkthrough_api_unattended/project.json
```

这个模板才会检查 `FAL_KEY` 等脚本后端。默认日常调用不走它。

如果本地不能直接调用 gpt-image-2，脚本只会写出 `prompt_pack.md` 和 `STATIC_IMAGE_GENERATION_PENDING`，不会伪造图片或假装已经生成成片。

L1 静态图伪漫游 renderer 支持 `transition_type=auto`、`subtitle_mode=minimal`、`auto_captions=true` 和 `captions`。默认会按镜头语义选择柔和转场：入口到大景用顺动横移，主视觉用克制叠化，细节用轻柔模糊，收尾用慢溶解。文案应该按镜头设计，少字、低压迫感、突出空间价值；如果没有手写 `captions`，脚本会按镜头类型自动生成基础文案，并生成 `.ass` 字幕文件烧录到最终 MP4。

v1.1 L1 自动图片成片入口：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_self_generated_l1/project.json
```

这个入口只测试最稳定的 L1 链路：

```text
project.json
-> generate_auto_project_assets.py
-> generate_gpt_image_keyframes.py
-> OpenAI Image API 生成静态关键帧
-> render_static_image_project.py
-> 输出 L1 样片风格伪漫游 MP4
```

如需真实生成图片，请在以下任一文件配置：

```text
project/full_house_custom_ad/.env
project/.env
~/.hermes/.env
```

格式：

```text
OPENAI_API_KEY=your_real_openai_api_key
```

`generate_gpt_image_keyframes.py` 默认使用项目配置里的图片模型，例如 `gpt-image-1.5`。如果本机没有 `OPENAI_API_KEY`，它会输出 `GENERATOR_NOT_READY`，同时保留 `prompt_pack.md`，不会伪造图片。生成出的图片最高只进入 L1 样片风格伪漫游，不得称为真正 walkthrough 或 L4。

这段只适用于本地脚本无人值守生成图片。你直接在 Codex 里让我做时，默认走 Codex 交互式生成，不要求配置这个 key。

连续视频后期模板：

```bash
cd project/full_house_custom_ad
# 先把 projects/example_continuous_video_template/project.json 里的 source_video 改成真实视频路径
python scripts/render_project.py --config projects/example_continuous_video_template/project.json
```

静态图 L1 伪漫游模板：

```bash
cd project/full_house_custom_ad
# 先把 projects/example_static_image_l1_template/project.json 里的 source_images_dir 改成图片目录
python scripts/render_project.py --config projects/example_static_image_l1_template/project.json
```

L2 分段 AI 漫游模板：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_segmented_ai_walkthrough/project.json
```

L2 模板需要先准备 `source_clips_dir` 里的多个 AI video clip。它只能默认标注为 AI 分段空间漫游，不是 L4 样片级连续 walkthrough。

L4 人工空间语义复核模板：

```bash
cd project/full_house_custom_ad
python scripts/create_semantic_review_template.py --config projects/example_continuous_video_template/project.json --reviewer "你的名字"
```

L4 最终通过不能只改 `project.json`。必须保留 `output/<project>_semantic_review.md` 人工空间语义复核记录，且 validator 会校验项目 ID、源视频 hash、样片级专项评分、逐项复核勾选和最终结论。样片级专项评分必须不低于 85 分；低于 70 分必须考虑降级。

`render_project.py` 会先生成连续性报告，再按素材类型路由：

- 单条真实连续视频、专业 3D 漫游导出或单条 AI 连续视频：走 `render_continuous_video_project.py`
- 多个独立 AI video clip：走 `assemble_segmented_ai_walkthrough_clips.py`
- 静态图关键帧：走 `render_static_image_project.py`，只允许标注 L1 伪漫游/图片展示，不得冒充真正 walkthrough
- 没有素材且在 Codex 交互式调用：默认由 Codex 设计/准备素材，再走 L1 渲染
- 没有素材且 `generation_execution_mode=codex_session`：本地脚本输出 `SESSION_VIDEO_PROVIDER_NOT_AVAILABLE`，提示需要当前会话视频工具或 hyperframes 这类已暴露插件，不要求 API key 或上传素材
- 没有素材且 `auto_generate_assets=true` 或 `source_policy=auto_generate` 且明确 `generation_execution_mode=api_unattended`：本地脚本先走 `generate_auto_project_assets.py`，自动尝试 API L3 -> L2 -> L1 最高可执行版本
- 没有素材且所有 API 生成后端不可用：输出 `GENERATOR_NOT_READY`，但不要求上传 `source_video`
- 没有素材且没有开启自动生成：只输出报告并停止

仓库不提交以下内容：

- `.deps/`：本地依赖包，体积大，可在本机环境重新生成。
- `output/`：生成视频和预览图。
- `assets/generated/`：AI 生成图片素材。
- `music_library/mp3/`：本地音乐文件。

这些文件属于运行素材或生成结果，不属于源码。需要制作视频时，把本地授权音乐放入：

```text
project/full_house_custom_ad/music_library/mp3/
```

## 核心规则

当前调色规则已经调整为：

```text
全屋定制默认采用克制通透的高级样板间调色。
画面必须清楚，但不能硬提亮、发白、发灰或失去暗部层次。
深色柜体要保留重量感，浅色空间要保留材质感。
目标是高级、干净、有层次、手机可看清，不是单纯变亮。
```

## 空间漫游能力等级

- L0：不能做漫游，只能图片展示。
- L1：样片风格伪漫游，gpt-image-2 静态关键帧 + 本地运镜。
- L2：AI 分段空间漫游，至少 2 个 AI video clip 拼接，但不保证同一空间连续性。
- L3：真正空间漫游，真实连续视频、专业 3D 漫游导出，或单条连续 AI video。
- L4：样片级连续空间漫游，必须满足同一空间连续路径、连续视差、少硬切、材质灯光比例稳定、发布级真实感、样片级专项评分 >= 85 和人工空间语义复核文件校验。

缺少连续素材时，可以用 gpt-image-2 做高质量关键帧和 L1 伪漫游，但不能把它叫真正 walkthrough。多个独立 AI clip 至少需要 2 个 clip 才能进入 L2；没有连续性报告、关键帧视觉证据、有效人工空间语义复核文件和 >=85 的样片级专项评分，不得叫 L4 样片级连续空间漫游。

## FAL AI video

v1.1 已内置 `fal_video_provider.py`，不再需要自行添加 `plugins/video_gen/fal.py`。FAL 是可选的脚本无人值守视频生成后端，不是日常调用 skill 的必需条件。如果要使用 FAL 生成 L2 分段 AI clip 或 L3 单条连续 AI video，只需要配置密钥。密钥可放在以下任一文件：

```text
project/full_house_custom_ad/.env
project/.env
~/.hermes/.env
```

格式：

```text
FAL_KEY=your_real_fal_key
```

本仓库的分段 AI clip 只标注为 L2：AI 分段空间漫游。它可以有动态镜头，但不能默认说成样片级连续 walkthrough。单条连续 AI video 只进入 L3 candidate，不自动保证 L4。

内置 provider 使用 FAL queue HTTP API：

```text
project/full_house_custom_ad/scripts/fal_video_provider.py
```

## v1.0 完整性检查

最终收口后可以运行：

```bash
cd project/full_house_custom_ad
python scripts/check_v1_integrity.py
```

通过时会输出：

```text
V1 final auto-assets integrity check passed.
```

v1.1 L1 链路检查：

```bash
cd project/full_house_custom_ad
python scripts/check_v1_1_l1_integrity.py
```

通过时会输出：

```text
V1.1 L1 integrity check passed.
```

v1.1 L2/L3 视频后端检查：

```bash
cd project/full_house_custom_ad
python scripts/check_v1_1_video_integrity.py
```

通过时会输出：

```text
V1.1 video backend integrity check passed.
```

v1.1 Codex 交互式默认模式检查：

```bash
cd project/full_house_custom_ad
python scripts/check_v1_1_codex_mode_integrity.py
```

通过时会输出：

```text
V1.1 Codex interactive mode integrity check passed.
```

v1.2 生成模式检查：

```bash
cd project/full_house_custom_ad
python scripts/check_v1_integrity.py
```

检查内容包含 `strict_true_walkthrough`、`best_effort`、自生成项目模板和自动降级字段。

## 备注

真正空间漫游需要真实连续视频、AI 连续视频或专业 3D 漫游素材。日常 Codex 调用不需要额外 API，默认先检查当前会话视频生成能力和已暴露视频插件 provider，例如 hyperframes；如果当前会话没有可调用视频 provider，strict 模式输出 `SESSION_VIDEO_PROVIDER_NOT_AVAILABLE`，不要求 `OPENAI_API_KEY` / `FAL_KEY`，也不要求上传素材。`strict_true_walkthrough` 代表“只要真正空间漫游，不接受降级”；`best_effort` 代表“自动生成最高可执行版本”。API key 只用于你明确选择 `api_unattended` 本地脚本无人值守模式。v1.0/v1.1/v1.2 不承诺从 0 稳定生成 L4。样片级连续空间漫游还必须通过连续性检查、样片级专项评分和人工空间语义复核文件校验。validator 的抽帧和帧差只提供基础视觉证据，不能自动证明电视墙、沙发、材质、灯光和空间比例语义一致。缺少连续素材时，skill 可以继续执行高质量降级方案，但必须清楚标注为图片展示、样片风格伪漫游或 AI 分段空间漫游，不能冒充同款样片级 walkthrough。
