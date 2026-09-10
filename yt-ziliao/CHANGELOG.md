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
