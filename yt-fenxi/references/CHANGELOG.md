# yt-fenxi 更新日志

## 2026-09-10

### vN6.0 批次 — 拆局价值评分轴改造（频道定位升级配套）

> 背景：频道定位升级为"买方视角商业极境拆局纪录片"（方案见 ~/Downloads/YouTuber技能优化调整方案.md P0②）。
> 原流量四维（Demand/Conflict/Outlier/Archive）评的是"这题有没有流量"，新定位要评的是"这题拆不拆得开"。
> **性质：文本层调整——脚本（scan_unsourced/audit_consumption/preflight）零改动，N5 三分/消费对账闸/N8 硬闸门/N9 收货单结构不动。**

| 变更 | 说明 | 文件 |
|------|------|------|
| 评分轴更换 | N3 主评分轴 = 拆局价值四维：非共识30/齿轮可还原30/决策考古25/关卡流15，锚点表落 scoring-anchors §一；原流量四维降参考层（仍评估附卡，不进总分不进闸门）；重档/轻档机制保留（参考层调 API，主评分轴按资料包打） | scoring-anchors.md / SKILL.md / analysis-card-template.md |
| C 闸门①改造 | "硬核信源≥2" → "三方对照可得"：创始人视角+至少一方反方视角（离职者/对手/投资人）有实料 | scoring-anchors.md §二 / SKILL.md / 卡模板 §三 |
| C 闸门④新增 | 空方压力测试：立项必产 Kill_Thesis 草案（3 年内市值蒸发 50% 的单点崩溃原因），触发条件+崩溃路径+空方证据来源齐全才通过；空泛质疑不通过。推导只到草案级（ziliao 维度五 a 供料，五 b 推导落此） | scoring-anchors.md §二 / SKILL.md / 卡模板 §三 |
| N6 第 5 维 | 切入瞬间穷举：消费 ziliao §5.4 锚点清单 → 三锚点（物件/数字/对话）补挖 → Nieman 4C 全过入候选 → 时机矩阵标注（Crisis/Pivot-MVP/Genesis/Peak，买方视角推荐 Pivot-MVP）→ N8 人审人选；候选<2 个 4C 通过不得交付 | scoring-anchors.md §4.4 / SKILL.md / 卡模板 §六 |
| 常见错误 | 三行更新/新增：三方对照一票否决、Kill_Thesis 禁空泛、4C 不过不硬塞 | SKILL.md |

---

## 2026-09-09

### vN5.6 批次 — 消费对账机械闸（防偷懒/防遗漏）+ 边界声明

> 背景：星宇案复盘暴露——ziliao 交付 22 素材/4 争议/6 角度，fenxi 消费全靠"读懂文档+自觉"，
> 无任何机制阻止"挑顺手的用、其余静默丢弃"。本批补机械闸门：两闸并列——
> 无出处扫描管"写进卡的都要有源"，消费对账管"报告里的都要有着落"。
> 前置依赖：yt-ziliao v2.6.0 manifest.json（本批兼容缺失降级）。

| 变更 | 说明 | 文件 |
|------|------|------|
| 新脚本 | `audit_consumption.py <manifest.json> <分析卡.md>`：素材 URL（规范化去 utm/尾斜杠/host 小写）+ 争议 D-ID + 角度 A-ID 三个集合差集校验；exit 0 才准入 N8；对账表（## 十一、消费对账）内出现即销号 | scripts/audit_consumption.py |
| 测试 | tests/test_audit_consumption.py（6 项）：规范化、懒卡全拦、对账表销号、争议销号、exit code；真实 T-2026-009 manifest vs 空卡冒烟：22/4/6 全拦 ✓ | tests/ |
| 铁律 | 消费对账铁律（静默丢弃即返工）+ 不越权改上游（不改 ziliao 核验结论） | SKILL.md |
| N2 就绪 | 增 manifest 检查：存在=机械原料；缺失=警告降级"文档 URL 抽取"模式不阻断（旧报告兼容） | SKILL.md |
| 流程 | Step 10.5 消费对账扫描（与无出处扫描并列两闸）；Progress checklist 增行 | SKILL.md |
| 模板 | N5.5 增"未选争议点去向"硬行表；N6 增"对照 ziliao §5.1"硬行表；新增"十一、消费对账"节（素材去向/未选争议/未选角度三表） | references/analysis-card-template.md |
| N9 契约 | 收货单第九字段扩为十项：+消费对账（exit 0） | SKILL.md |
| 常见错误 | 增两行：挑顺手素材静默丢弃会被闸拦；凭印象对账不认，只认脚本输出 | SKILL.md |

---

（更早变更见仓库主 CHANGELOG 与 git log）
