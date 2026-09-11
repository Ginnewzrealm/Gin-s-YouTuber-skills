# yt-jiaoben 更新日志

## 2026-09-10

### v0.5.3 — 防编造机械防线三连（2026-09-10 美的选题事故复盘落地）

> 事故：编人名「马库斯」进黄金 Hook、无源因果断言（库卡→除霜算法）、两个 Part 4 自检全 ✅ 却漏 BV 号补采义务。
> 第一性原理：编造在无成本结构里必然发生，给成本的方式是映射校验+销号闸门，不是提醒。
- **新增 scripts/scan_provenance.py**（交付硬闸）：口播行数字事实必带溯源标注（`（C-05）` 组合 `（C-03/C-05）`）；「他叫X」人名必须在素材语料或标 `（演绎：…）`；演绎全文必有免责句；标注 ID 必须存在于 manifest。实测：对 T-2026-002 事故脚本拦 31 处（含马库斯）；正例 fixture-provenance-good.md 通过
- **scan_script.py 结构闸**：同名章节重复硬拦截（归一化括号后缀——事故中"Part 4 自检报告（人审前过）"与"Part 4 自检报告"精确匹配抓不到）
- **新增 scripts/close_obligations.py**（义务销号闸）：manifest.pending_obligations 中本 stage 阻塞义务未销号不得开工；销号三终态 resolved/escalated/waived，escalated 必须留 evidence 且 ID 出现在交付物「未决义务」节；第四种状态（消失）不允许
- **HR-5.5 口播溯源标注**：事实/演绎/无源三类标注语法与红线（隐瞒的演绎才是事故，标注的演绎是工具）
- **script-template.md**：审查清单改 A/B 分类——A 类（机器可数）只能粘贴脚本输出，模型无权自报；B 类标 ⏳待人审；B-Roll 示例行的脑白金/江阴真实案例换为中性占位（污染源清除）
- **回填唯一通道** scripts/lark_writeback.py：schema 前置→本地校验→一次写入→回读对账闭环，取代手工 payload 试错（实战验证：选题状态单选字符串/数组自动规范化）
- **SKILL.md**：Step 0.3 义务销号闸（硬闸门）、Step 10 并跑溯源扫描、质量闸门取代完整度≥60（与 fenxi 单决策函数对齐）

### v0.5.1 — 交付改 03-脚本.md 推送（存储重构配套）

> 规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md。
> - 阶段6 交付：lark-doc 建 docx → lark-markdown 推 `03-脚本.md`（Part 3a A 稿 + Part 3b B 稿同文档两节，+create/+overwrite）
> - 本地主档=本技能 `workspace/<编号>/script-A.md` / `script-B.md`；飞书目标=core feishu_root + `<编号> <标题>/`
> - 删「脚本字数」回填（池内无此字段，存量矛盾修复）；回填只留「选题脚本链接」URL（空则填）
> - 英雄之旅/钩子六变体/CTA 两触点方法论零改动（双夹具结论不变）

（v0.5 及更早批次记录见 git 历史：8add316 v0.5 英雄之旅主线换轴等）

### v0.5.2 — Part 2 视频素材总表规范（优化轮）

- **Part 2 升级为"视频素材总表"**：镜头号 S## ↔ B 稿 [MM:SS-MM:SS] 块一一对应；列=镜头号/时间码/画面内容/来源网站/视频链接/片段位置/状态
- **三条硬规则**：①链接 curl 复核 200 才标 ✅；②状态三态（✅/⚠️待补/❌失效当场改写画面）；③只收视频，图文不进表（01b 已有，避免重复）
- material-to-visual.md §四同步：视频类进总表、图文类沿用凭证编号
- 用户按总表批量自下载素材，不再翻全文找链接
