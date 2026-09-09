# yt-fenxi 更新日志

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
