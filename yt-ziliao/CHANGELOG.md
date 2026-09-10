# yt-ziliao 更新日志

## 2026-09-10

### v2.9.0 — 网页 AI 粗采层（步骤 4.7，最小侵入）

> 背景：资料采集环节读网页 Token 消耗占整条链路 60-70%。本版引入"粗采层"——通过 AgentChat 桥接免费网页 AI（DeepSeek/千问/Kimi 轮换）出线索，我方只精读已验证页面，预期 ziliao 读网页 Token 省 60-75%。

- **新增步骤 4.7**：默认优先粗采层，不可用时静默降级纯 WebSearch（记入 runtime/.runs）
- **轮换协议**：provider_pool 轮转 + 频率控制（单家冷却 60s / 时上限 20 / 日上限 80），防封号
- **质量红线**：无有效 URL 的线索物理进不了 materials.json；URL curl 复核 + 数字双源核验 + 零静默丢弃——质量闸门与纯 WebSearch 路线完全一致
- **新增 `references/网页AI粗采层.md`**：调度协议 / 提示词三段式模板 / 复核协议 / 审计链规则
- **新增 `config.template.yaml`**：`webai_collection: true|false` 开关（默认 true，改 false 即永久回退）
- **下游契约不变**：materials.json schema、score_materials.py、六阶段编排、飞书交付物全不动；条目仅多可选 `collection_route: "webai"` 溯源字段
- 外部依赖：AgentChat（`~/.agents/skills/agentchat`）+ 专用 Chrome CDP 9222 + 三家登录态

### v2.9.1 — 评分 bug 修复 + TOC 生成器 + 粗采层视频线索（优化轮）

- **score_materials.py 修复**：stance 前缀归一（"质疑方(括注)"不再被丢弃，D4 从 0→60）；language 别名归一 + D2 公式改"主语言 60 基础 + 次语言加成"（中文选题不再恒 0，D2 0→62.9）；platform 别名 + URL 域名兜底（D1 20→100）。脑白金 35 条回归：overall 46.8→75.8，评分首次真实反映数据质量
- **新增 scripts/generate_toc.py**：推送飞书前自动生成目录区块（<!-- TOC --> 标记，幂等可重复跑），解决飞书 .md 无大纲问题
- **粗采层增强**：新增子任务④视频线索（千问/Kimi 出"节目名+年份"，B 站 API 按图索骥）
- **双源制制度化**：步骤 6 标注节明文硬规则——数字/引语双源印证，单源降档，无源 rejected

### v2.10.0 — 文书员模式（步骤 5'：网页 AI 精读+结构化）

- **默认启用**：对已验证 URL 清单，网页 AI 逐页读+吐 JSON 结构化条目（强约束 prompt：逐字照抄/禁归纳/原文没有填空），子 Agent 只做抽验 20% + 双源核验 + 立场标注——省 Token 的本质从"每页 WebFetch"变"抽验 20% 页"
- **三重降级**：配置级（webai_structured:false）/ 运行时级（CDP 或 provider 不可用）/ 质量级（抽验变形率>10% 或单页 unreadable → 该页精准降级 WebFetch，不整批作废）
- **新中间产物**：raw/webai_structured.json（带 receipt，审计链不断）；materials.json schema 不变
- **实测依据**：DeepSeek 强约束提取 8/8 字段忠实原文、无编造；publish_date 比手工条目更准；暴露我方 v1.1 手工条目污染——双源核验对 AI 与人工一视同仁
- 局限：单样本单 provider，试点期须 3-5 个不同来源类型验证
