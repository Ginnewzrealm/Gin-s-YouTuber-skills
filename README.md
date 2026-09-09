# Gin's YouTuber Skills

YouTuber 创作工作流技能库。

> 状态：**进行中**——总路由 + 三个核心技能已建（ziliao v2.5 / fenxi / jiaoben），制作/复盘技能待建。
> 设计原则：最大化复用成熟技能，只在不满足处微调。

## 工作流与技能分工

```
挖选题 → 评分排序 → 选题池 → 深挖资料(yt-ziliao) → 选题分析 → 脚本(SOP7) → 制作四件套 → 发布包装 → 数据复盘 → 回流选题池/脚本
[选题探索]              [复用]            [选题分析]     [脚本SOP7]   [制作四件套]  [复用]     [数据复盘]
                          ↑ 总路由 youtube-skills：读池状态→渲染宏观六阶段进度→指出该调谁（薄路由，不做业务）
```

## 要建的技能（5+1 个）

| # | 技能 | 状态 | 说明 |
|---|------|------|------|
| 0 | `youtube-skills` 总路由 | ✅ v0.1.0 | 主编排：初始化/路由/宏观进度；工作区路径唯一事实源 |
| 1 | `xuanti-tansuo` 选题探索 | 待建 | 互联网挖选题 → 简单评分排序 → 选题池；检索底层复用 trend-discovery / agrici-ideate |
| 2 | `yt-fenxi` 选题分析 | ✅ 可用 | 惊奇点/事实/观点/争议/切入点/竞品切入与流量/我方调整 → 选题分析卡；上游固定接 yt-ziliao |
| 3 | `yt-jiaoben` 脚本 | ✅ 可用 | 起承转合四幕+A 稿纯口播+B 稿三轨；四层内容标注；机检+法审 |
| 4 | `zhizuo-brief` 制作四件套 | 待建 | 配音 brief / 分镜+B-roll 清单 / 剪辑 brief / 配乐提示，一次出齐 |
| 5 | `fupan` 数据复盘 | 待建 | 底座复用 agrici `/youtube analyze`；自建"掉粉点→脚本段落映射"与"回流选题池/脚本参数" |

## 复用不建的资产

| 资产 | 担任角色 |
|------|---------|
| yt-ziliao | 选题分析的固定上游（原样复用） |
| agrici `/youtube metadata` | 发布包装整格（微调：中文市场参数） |
| agrici `/youtube analyze` | fupan 方法论底座 |
| agrici `/youtube competitor` | 选题分析竞品检索底层 |
| trend-discovery / agrici `/youtube ideate` | 选题探索检索底层 |
| higgsfield-thumbnail | 缩略图生成（接发布包装的缩略图 brief） |

## 开工前待答

- [ ] 频道语言/市场（中/英）
- [ ] 视频形态（口播/无脸）
- [ ] 痛点排序（决定施工顺序）
- [ ] 五维评估法 / SOP 7 步法 / 简单评分标准现成稿
