# 图片生成和素材提示词库

本文件只放图片生成、素材补充和视觉关键词。节奏、音乐、转场、字幕、风格细节分别见其他 reference 文件。

## 默认视频规格

- 9:16 竖屏
- 1080 x 1920
- 60fps
- MP4
- 发布平台：抖音
- 默认节奏：高级广告模式或舒适观看模式
- 默认时长：跟随音乐完整结构和空间观看体验
- 核心原则：客户看清楚空间，比剪辑卡点更重要

## 图片内容清单

完整全屋定制案例建议准备 8-12 张高质量图，但实际视频不一定全部使用。最终使用数量由音乐长度、视频类型、素材质量和观看体验共同决定。

优先素材：

1. 客厅全景
2. 电视背景墙
3. 餐厅和餐边柜
4. 厨房橱柜
5. 主卧空间
6. 衣柜或衣帽间
7. 书房或书柜
8. 玄关柜
9. 隐藏灯带细节
10. 材质细节
11. 收纳系统细节
12. 结尾完整主视觉

图片质量要求：

- 4K 级视觉质感
- 构图干净，不拥挤
- 柜体线条清晰
- 灯光层次丰富
- 克制通透的高级样板间质感，适合手机观看
- 暗部有细节，但不能被硬提亮成灰雾
- 深色柜体保留重量感，浅色空间保留材质感
- 材质真实高级
- 有木饰面、岩板、玻璃、金属、皮革、隐藏灯带等质感
- 有空间大景，也有定制细节
- 像专业摄影师为视频漫游拍摄的关键帧，而不是普通静态效果图

## 每次生成新设计

每次生成图片前，先根据音乐和原创导演概念确定新主题，不要直接复用旧提示词。

必须明确：

- 本次风格：例如艺术馆住宅、酒店套房感、东方现代会所、都市精英大平层。
- 本次空间路线：从哪里进入，高潮展示什么，结尾停在哪里。
- 本次材质：木饰面、岩板、玻璃、金属、皮革、微水泥等。
- 本次光线：受控自然窗光、隐藏灯带、柔和主光、局部补光、酒店暖光等。
- 本次镜头：低机位、侧墙进入、柜体边缘遮挡、天花线条引导等。

## 视频关键帧摄影要求

生成或选择图片时，优先满足：

- 入口感：画面有墙边、柜体边、门洞、玄关或前景遮挡。
- 运动方向：看得出摄影机可以向前推进、横向滑移或从暗部走向亮部。
- 引导线：天花线、灯槽、地面线、柜体竖线能引导视线。
- 低机位或中低机位：突出地面反光和空间尺度。
- 地面反光：瓷砖、岩板或木地板反光干净通透。
- 主视觉落点：电视墙、落地窗、沙发区、餐厨、衣帽间中心明确。
- 广角自然：wide-angle architectural photography，但家具不变形。
- 光线层次：隐藏灯带、窗光、局部照明有层次。
- 手机观看：整体曝光均衡，空间主体清楚，但不能过亮、发白或失去对比。

这些图片更适合做伪空间漫游或高级图片展示。真正空间漫游需要连续视频、AI video 或 3D camera path，不能只用静态图冒充。缺少真实连续视频素材时，优先使用 gpt-image-2 生成本次原创高质量空间关键帧，再进入本地高级运镜、转场、调色和配乐制作流程。

## 基础图片生成提示词

中文说明：
这里用于生成高端全屋定制室内图片，适合客厅、餐厅、厨房、衣帽间、书房和定制柜体主视觉。使用前必须按本次音乐和原创导演概念替换风格、材质和空间路线。

英文提示词：

```text
Luxury modern custom home interior, premium whole house customized furniture, high-end built-in cabinets, minimalist interior design, warm grey color palette, wood veneer, marble texture, hidden LED light strips, elegant living room, premium kitchen cabinetry, walk-in closet, dining room with sideboard, balanced luxury showroom lighting, controlled soft daylight, warm indirect lighting, rich but visible shadows, premium cabinet texture, clear material detail, not overbright, cinematic interior photography, wide-angle architectural photography, low camera height, gimbal walkthrough perspective, leading ceiling lines, clean floor reflection, natural perspective, soft shadows, high-end residential design, 4K.
```

## 艺术馆住宅提示词

中文说明：
适合生成留白、线条、石材、艺术灯光和安静高级感的空间。

英文提示词：

```text
Luxury art gallery residence interior, refined minimalist home, sculptural built-in cabinets, warm grey stone, subtle wood veneer, gallery-like lighting, large quiet living room, curated furniture, clean negative space, low camera height, architectural leading lines, controlled soft daylight, balanced luxury showroom lighting, rich but visible shadows, premium custom storage, cinematic interior photography, not washed out, ultra realistic, 4K.
```

## 五星酒店套房提示词

中文说明：
适合生成酒店套房、衣帽间、深木、玻璃柜门、金属线条和品牌广告感空间。

英文提示词：

```text
Luxury hotel suite inspired home interior, dark wood veneer with visible grain and weight, champagne metal details, marble texture, glass wardrobe doors, soft indirect lighting, controlled daylight fill, rich but visible shadows, premium walk-in closet, elegant bedroom, high-end custom cabinets, cinematic interior photography, low camera height, reflective floor, foreground cabinet edge, luxury walkthrough composition, quiet luxury, not overbright, not underexposed, ultra realistic, 4K.
```

## 东方现代会所提示词

中文说明：
适合生成东方现代、木石结合、安静秩序、暗部层次和会所感住宅。

英文提示词：

```text
Modern oriental luxury residence interior, calm clubhouse atmosphere, dark wood built-in cabinets with visible texture and weight, natural stone wall, warm indirect lighting, controlled daylight fill, refined symmetry, quiet luxury, elegant tea area, premium storage system, rich clean shadows, low camera height, floor reflection, architectural composition, not washed out, ultra realistic, 4K interior photography.
```

## 都市精英大平层提示词

中文说明：
适合生成黑灰大平层、城市窗景、地面反光和强空间尺度。

英文提示词：

```text
Urban luxury penthouse interior, high-end black and warm grey custom cabinetry, large floor-to-ceiling window with city view, premium TV wall, glossy marble floor reflection, linear ceiling lights, sophisticated sofa area, open dining and kitchen, balanced luxury showroom lighting, controlled soft daylight, preserved black point, cinematic real estate photography, low gimbal camera perspective, ultra realistic, 4K.
```

## 工艺细节广告片提示词

中文说明：
适合生成柜门、灯带、岩板、玻璃、五金和收口细节。

英文提示词：

```text
Luxury custom cabinet detail shot, premium wood veneer, marble and metal junction, hidden LED strip, refined cabinet door gap, glass display cabinet, high-end hardware, macro interior photography, shallow depth of field, warm grey color grading, clean luxury material texture, ultra realistic, 4K.
```

## 空间漫游关键帧提示词

中文说明：
适合生成有纵深、入口感、天花线条、地面反光和视觉中心的图，用于伪空间漫游或高级看房感视频。必须根据本次原创路线改写，不得固定复刻参考视频。

英文提示词：

```text
Luxury residential walkthrough keyframe, wide-angle interior with strong depth, original entrance reveal into the designed space, low camera height, gimbal camera perspective, foreground wall or cabinet edge, ceiling lines leading the eye, clean floor reflection, hidden LED lighting, controlled soft daylight, balanced luxury showroom lighting, rich but visible shadows, preserved contrast, premium built-in furniture, clear focal point, cinematic architectural perspective, natural perspective, clean composition, not overbright, ultra realistic, 4K.
```

## 负面提示词

中文说明：
用于避免低端装修模板、杂乱画面和不真实材质。

英文负面提示词：

```text
low quality, blurry, underexposed, too dark, overexposed, too bright, washed out, flat lighting, milky filter, gloomy room, heavy vignette, crushed blacks, lifted black point, grey shadows, loss of contrast, cluttered room, cheap decoration, over saturated colors, cartoon style, unrealistic furniture, distorted cabinet lines, distorted wide angle, messy background, harsh lighting, over sharpened, fake material, watermark, logo, text overlay, red and yellow promotional text, low-end template, flat front view with no depth, repeated old composition, copied reference video frame.
```
