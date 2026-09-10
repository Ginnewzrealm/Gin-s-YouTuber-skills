# yt-guanjianci 更新日志
## v0.2.0（2026-09-10）——存储契约重构：workspace 落盘 + 05-关键词包.md 中转 + 字段摘要

> 规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md。
> - 落盘：core `关键词库/` → 本技能 `workspace/<编号>/keywords.json`；同内容推飞书 `05-关键词包.md`（JSON 原文包代码块），下游 +fetch 读回——工作区不跨技能读
> - 频道词库：`workspace/频道词库.json` 根文件免清（唯一本地持久文件）
> - 新增：选题表「关键词包」字段写**文字摘要**（主关键词/候选标题 3-6 条带公式编号/封面词/档位；空则填不覆盖，推荐期换标题后同步更新）
> - 四级分级/标题公式/封面词方法论零改动（15/15 回归绿）

## v0.1.0（2026-09-10）——初版：关键词+标题库（TDD 全程：9 测试先行）

> 定位：服务性技能（被 tansuo/fenxi/发布三方调用 + core 在推荐期触发换标题）。
> 频道级资产：关键词包（JSON 落盘）+ 标题矩阵（钩子词×句式）+ 频道词库（句式/钩子/验证记录累积）。
> 方法论出处：vidIQ/Ahrefs 四级分级与 KD 框架｜中文运营社区四维扩词矩阵｜TubeBuddy/vidIQ CTR 研究+
> 中文爆款 4 公式｜蝉妈妈 AI 三元拆解 SOP（2026-09 两轮调研归档）。

| 组件 | 内容 |
|---|---|
| 机械闸 | scripts/keyword_brief.py：schema 齐/档位合法(A=DataForSEO精确,B=Trends相对,C=手工定性)/标题 8-35 字/禁逗句号叹号/无占位符；exit 0 才准交付 |
| 方法论×4 | references/keyword-grading.md（四级分级+KD选词+意图三分+保鲜）｜longtail-matrix.md（A动作/B冲突/C疑问/D时间四维算子+中文特有规则）｜title-formulas.md（4公式+CTR规范+两阶段策略）｜reverse-engineering.md（Outlier系数+三元拆解+四步SOP） |
| 配置 | config.template.yaml：数据源档位 A/B/C（默认 C 零依赖）+ YouTube Data API 预留（未注册，走手工贴数降级） |
| 测试 | tests/test_keyword_brief.py 9 项（长度/标点/占位符/schema/档位/exit code） |

> 关键设计：两阶段标题策略（冷启动搜索友好 0-14 天 → 推荐期高情绪 Hook）；
> core 状态机已拆「已发布(冷启动)」→「推荐期」两个阶段，换标题动作由 core 触发本技能。
> 保鲜：关键词 30 天/竞品 7 天，挂 fupan 复盘时刷新（fupan 待建，此前人工）。
