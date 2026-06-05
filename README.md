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

## 备注

真正空间漫游需要真实连续视频、AI 连续视频或专业 3D 漫游素材。缺少连续素材时，skill 默认用 gpt-image-2 生成全新关键帧，再制作高级伪空间漫游或图片展示型成片。

