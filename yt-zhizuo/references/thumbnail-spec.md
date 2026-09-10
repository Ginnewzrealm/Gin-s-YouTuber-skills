# 商业故事频道封面视觉规范（设计 Brief + AI 出图 SOP）

> 来源：2026-09 归档《商业故事类 YouTube 封面设计规范》。
> 标注规则：「规范」=硬性执行；「经验」=经验参数（6°/35-40% 面积等），默认起点，实战后校准。
> 交付形态：**封面词（yt-guanjianci 出）与封面图提示词（本规范出）是两个独立输出**，各自可单独拿走用。

## 一、色彩体系（严格 3+1，禁杂乱/电光渐变）

| 角色 | 色值 | 占比 | 用途 |
|---|---|---|---|
| 背景主色 | 藏青蓝 #051C2C | 60% | 纯色/微渐变暗底，权威商业感 |
| 第一爆点 | 高能橙红 #FF3300 | 15% | 结论大字/暴跌箭头/警示（禁发暗正红） |
| 第二爆点 | 柠檬警示黄 #FFE600 | 15% | 仅核心数字大字（黄蓝=互补色最高对比） |
| 隔离辅助 | 纯黑 #000000 / 纯白 #FFFFFF | 10% | 黑=文字描边硬阴影；白=次要修饰大字 |

## 二、字体与图层

- 字体：中文 蒙纳超刚黑/汉仪超粗黑/思源黑体 Heavy(900)；英文 Bebas Neue/Impact；**禁细体/手写/衬线**
- 封面字：**2-4 个汉字**（经验：越少字号越大，占画面 35-40%）；字组整体向右上倾斜 6°（经验值）
- 图层（PS/Figma，按 1920×1080 画布，其他画布等比缩放）：
  - 第一行纯黄 #FFE600，第二行橙红 #FF3300
  - 纯黑硬描边 15-20px（100% 不透明无羽化）
  - 纯黑投影（Distance 15px, Size 0, Angle 120°）

## 三、构图铁律

1. **左侧 50% 文字区**：倾斜超大字，第一视觉焦点
2. **右侧 50% 图像区**：摩天楼剪影/人物抠图，**压暗融入底色，禁抢字的戏**
3. **视觉动线**：一条粗橙红暴跌折线箭头，右上→左下贯穿
4. **右下角 15% 死区必须留空**——YouTube 播放器强制叠时长标签，放字必被遮

## 四、AI 出图 SOP（五段式提示词法）

> 核心认知：**AI（Midjourney/FLUX/可灵等）渲染中文大字必乱码**——正确分工 =
> AI 只出**无字暗色高对比底图**，字全部后期（PS/剪映/Figma）叠。

### 五段式 Prompt 公式

```
1. 主体与商业隐喻：collapsing sky-scraper / financial stock chart plunge line /
   shadowy corporate executive / cracked golden icon
2. 色彩强控：Deep midnight blue background (#051C2C) / glowing red (#FF3300)
   and yellow (#FFE600) accents / dramatic volumetric lighting
3. 留白与构图：Clean empty dark blue space on the left 50% reserved for large text /
   clean empty area on the bottom right（死区）/ split composition, asymmetrical
4. 风格质感：Cinematic 3D rendering, Unreal Engine 5 render /
   Bloomberg graphics style, McKinsey presentation aesthetic（禁卡通/禁 stock 感）
5. 控制参数：--ar 16:9 --style raw（画幅必须 16:9）
```

### 实战示例（英伟达 3 万亿清算案）

```
A massive 3D glowing green microchip with a visible crack, collapsing on the right
side. Dark midnight navy blue background (#051C2C). A sharp glowing red (#FF3300)
downward chart line slicing from top right to bottom left. High-contrast volumetric
dark lighting, McKinsey presentation graphic style, UE5 render. Left 50% dark and
clear, reserved for large text. Clean bottom-right area. --ar 16:9 --style raw
```

## 五、自检 Checklist（出图后过）

- [ ] 1920×1080 PNG <2MB；缩小到 15%（手机尺寸）核心字 0.1 秒可读
- [ ] 背景严格 #051C2C；爆点严格 #FF3300/#FFE600
- [ ] 文字 15px+ 纯黑硬描边，与底色彻底分离
- [ ] 右下角 15% 完全留空
- [ ] 信息分配：封面字与标题**不重复**（标题=完整逻辑+SEO，封面=情绪诱饵）

## 六、与本技能的接口

- **输入封面词**：`<关键词包>.封面词`（yt-guanjianci 产出，≤6 汉字，过机械闸）
- **输出封面图提示词**：按五段式法生成英文 Prompt → 喂 higgsfield/Midjourney → 无字底图 → 后期叠字
- 形态=AI 的分镜行可复用本规范色彩/留白指令；露脸段封面另走实拍截图+压暗处理
