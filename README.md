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

自动生成素材入口：

```bash
cd project/full_house_custom_ad
python scripts/render_project.py --config projects/example_self_generated_walkthrough/project.json
```

这个入口用于 v1.0-final-auto-assets：当用户不提供素材、要求系统自己制作素材、自动生成素材、做测试片或从零做原创空间时，`render_project.py` 会先启用 `auto_generate_assets` 自动生成素材模式。

自动生成素材模式的顺序是：

- `continuous_ai_video` 可用：生成单条连续 AI video，进入 L3 candidate，再走真正空间漫游后期；不自动保证 L4。
- `segmented_ai_clips` 可用：生成多个 AI video clip，进入 L2 AI 分段空间漫游；不得叫 L3/L4。
- `static_keyframes` / `gpt-image-2` 可用：生成静态关键帧，进入 L1 样片风格伪漫游；不得叫 true walkthrough。
- 所有生成后端不可用：输出 `GENERATOR_NOT_READY`，生成 auto assets report，不会第一轮要求用户上传 `source_video`。

如果本地不能直接调用 gpt-image-2，脚本只会写出 `prompt_pack.md` 和 `STATIC_IMAGE_GENERATION_PENDING`，不会伪造图片或假装已经生成成片。

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
- 没有素材且 `auto_generate_assets=true` 或 `source_policy=auto_generate`：先走 `generate_auto_project_assets.py`，自动尝试 L3 -> L2 -> L1 最高可执行版本
- 没有素材且所有生成后端不可用：输出 `GENERATOR_NOT_READY`
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

## FAL 分段 AI video

如果要使用 FAL 生成分段 AI clip，需要自行准备可用的 provider 和密钥。密钥可放在以下任一文件：

```text
project/full_house_custom_ad/.env
project/.env
~/.hermes/.env
```

格式：

```text
FAL_KEY=your_real_fal_key
```

本仓库的分段 AI clip 只标注为 L2：AI 分段空间漫游。它可以有动态镜头，但不能默认说成样片级连续 walkthrough。FAL provider 需要自行添加到：

```text
project/full_house_custom_ad/plugins/video_gen/fal.py
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

## 备注

真正空间漫游需要真实连续视频、AI 连续视频或专业 3D 漫游素材。v1.0 可以在用户不提供素材时自动尝试生成 L3/L2/L1 中最高可执行版本，但不承诺从 0 稳定生成 L4。样片级连续空间漫游还必须通过连续性检查、样片级专项评分和人工空间语义复核文件校验。validator 的抽帧和帧差只提供基础视觉证据，不能自动证明电视墙、沙发、材质、灯光和空间比例语义一致。缺少连续素材时，skill 可以继续执行高质量降级方案，但必须清楚标注为图片展示、样片风格伪漫游或 AI 分段空间漫游，不能冒充同款样片级 walkthrough。
