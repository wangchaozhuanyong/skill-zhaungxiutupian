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
python scripts/render_project.py --config projects/example_walkthrough/project.json
```

`render_project.py` 会先生成连续性报告，再按素材类型路由：

- 单条真实连续视频、专业 3D 漫游导出或单条 AI 连续视频：走 `render_continuous_video_project.py`
- 多个独立 AI video clip：走 `assemble_segmented_ai_walkthrough_clips.py`
- 静态图关键帧：只允许走 L1 伪漫游/图片展示渲染器，不得冒充真正 walkthrough
- 没有素材：只输出报告并停止

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
- L2：AI 分段空间漫游，多个 AI video clip 拼接，但不保证同一空间连续性。
- L3：真正空间漫游，真实连续视频、专业 3D 漫游导出，或单条连续 AI video。
- L4：样片级连续空间漫游，必须满足同一空间连续路径、连续视差、少硬切、材质灯光比例稳定和发布级真实感。

缺少连续素材时，可以用 gpt-image-2 做高质量关键帧和 L1 伪漫游，但不能把它叫真正 walkthrough。多个独立 AI clip 默认是 L2；没有连续性报告、关键帧视觉证据和人工复核，不得叫 L4 样片级连续空间漫游。

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

本仓库的分段 AI clip 只标注为 L2：AI 分段空间漫游。它可以有动态镜头，但不能默认说成样片级连续 walkthrough。

## 备注

真正空间漫游需要真实连续视频、AI 连续视频或专业 3D 漫游素材。样片级连续空间漫游还必须通过连续性检查和专项评分。缺少连续素材时，skill 可以继续执行高质量降级方案，但必须清楚标注为图片展示、样片风格伪漫游或 AI 分段空间漫游，不能冒充同款样片级 walkthrough。
