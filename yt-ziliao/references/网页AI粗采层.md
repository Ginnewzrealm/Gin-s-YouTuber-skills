# 网页 AI 粗采层参考（v1.0）

> 本文档是 yt-ziliao「步骤 4.7：网页 AI 粗采层」的执行细则。
> 定位：**侦察兵**——只出线索，不产素材；凡进 `materials.json` 的条目必须带经我方复核的真实 URL。

---

## 一、铁律

1. **网页 AI 只产"线索"，永不直接成为"素材"**——无有效 URL 的线索物理上无法进入 `materials.json`
2. **优先使用，降级回退**——粗采层是默认路线；不可用（Chrome 未起 / provider 全挂）时自动跳过，静默回退到纯 WebSearch 路线，记入 `runtime/.runs/<topic>.json`
3. **质量闸门不变**——URL 复核、双源核验、审计链、评分体系与纯 WebSearch 路线完全一致

---

## 二、调度协议

### 轮换池

| 顺位 | Provider | 角色 | 登录态 |
|---|---|---|---|
| 1 | DeepSeek | 中文事实/数字/引语线索 | 必需 |
| 2 | 千问 | 联网搜索型线索 | 必需 |
| 3 | Kimi | 联网搜索 + 引用 | 必需 |
| 备选 | 豆包 / MiniMax / MiMo | 前三家挂了顶上 | 用到了再登 |

### 轮换策略（默认轮转模式）

- **轮转**：每个子任务调用轮换池中"最久未使用且未触发限流"的 provider
- **特长定向**（可选）：中文事实→DeepSeek；联网搜索→千问/Kimi；英文视角→DeepSeek（英文提问）
- **故障转移**：单家失败自动降级链下一家，三家全败→回退纯 WebSearch

### 频率控制（防封号）

| 参数 | 值 | 说明 |
|---|---|---|
| 单家冷却 | ≥60 秒 | 同一 provider 两次调用最小间隔 |
| 单家小时上限 | 20 次 | 超过强制轮转下一家 |
| 单家日上限 | 80 次 | 超过当日停用，记 `rate_limited` |
| 提示词规模 | ≤300 字回答 | 控制时延与解析成本 |

调用前先读 `workspace/<编号>/raw/webai_provider_state.json`：
```json
{ "pool": ["deepseek","qwen","kimi"],
  "last_used": {"deepseek": "2026-09-10T17:00:00", "qwen": null, "kimi": null},
  "calls_today": {"deepseek": 3, "qwen": 1, "kimi": 0},
  "disabled_until": {"deepseek": null} }
```

选家算法：`取 pool 中 disabled_until 已过 + calls_today[家]<80 + last_used 最久者`；若选中家距上次调用 <60 秒，顺延下一家；全不满足→回退 WebSearch。

### 命令行

```bash
node ~/.claude/skills/agentchat/skills/AgentChat-OneWeb/index.js \
  --from=<Provider> --single "<提示词>" 2>&1 | tail -30
```

- `--from`：指定起始 provider，失败自动降级链下家
- 输出尾部含 `[receipt] AGENTCHAT_RUN {...}` 回执，必须保留（审计用）
- `exit=0` 成功；`exit=9` 全链失败→回退 WebSearch

---

## 三、提示词模板

### 通用结构（强制三段式）

```
请按以下格式回答，每条一行，不要多余内容：

事实陈述｜来源名称｜可核验URL（可选）

要求：
- 事实必须具体（含数字/日期/人名），拒绝模糊表述
- 不确定的事实标注"存疑"
- 回答控制在 300 字内
- 不要编造 URL，没有可靠来源就留空并标注"来源待补"
```

### 子任务模板

**① 中文事实粗采**（默认 DeepSeek）

```
你是资料采集助理。围绕选题《{选题名}》，梳理{维度}的关键事实（时间/数字/决策/引语）。
{通用结构}
重点关注：{检索语法提示，参考挖掘手册的三层颗粒×五维信源}
```

**② 联网搜索型线索**（千问/Kimi）

```
请联网搜索并回答：关于《{选题名}》的{具体问题}。
{通用结构}
优先给出：官方公告/权威媒体报道/学术论文，给出可核验 URL。
```

**③ 英文视角线索**（DeepSeek 英文提问）

```
You are a research assistant. List verifiable facts about {topic} from English-language sources,
focusing on critical/skeptical perspectives. Format per line:
Fact | Source name | Verifiable URL (optional)
```

### 已知输出噪声（解析时剔除）

- 思考过程/trace 文本（Kimi 常见，含"使用 N 个工具"等）
- `-1` `-10` 类脚注序号残留（DeepSeek 常见，来源清单被丢弃）
- 图片下载产物（`ai-image-*.png`，须删除）
- 末尾无意义后缀（如 `-1-2-3`）

---

## 四、质量复核协议（强制）

### 1. URL 复核（每条必做）

```
curl -s -o /dev/null -w "%{http_code}" --max-time 10 <URL>
```

- HTTP 200 + 正文抽查含关键事实 → 通过
- 死链 / 404 / 内容不符 → 记 `rejected[]`，reason：`网页AI线索：URL不可复核`
- 通过者进入精读队列（子 Agent 用 WebFetch/OpenCLI 读正文）

### 2. 双源核验（数字/引语级事实）

- 数字、日期、直接引语 → 须**两个独立来源**印证
- 单源 → 标 `核实状态：单一来源`，可信度降一档
- 无源 → 标 `存疑待核实`，进 `rejected[]` 或 `materials.json` 低权威区（须人审）

### 3. 立场标注

- 立场（支持/质疑/中立）由**我方读原文后判断**，不信网页 AI 的自评

### 4. 审计链（零静默丢弃）

| 线索去向 | 记录位置 |
|---|---|
| URL 复核通过 → 精读 | `raw/webai_clues.json` 标 `accepted` |
| URL 复核失败 | `materials.json rejected[]` + `raw/webai_clues.json` 标 `rejected` |
| 事实双源核验失败 | `materials.json rejected[]`，reason：`网页AI线索：事实无法双源印证` |
| provider 调用失败 | `runtime/.runs/<topic>.json` + `webai_clues.json` 标 `provider_error` |

---

## 五、粗采层产出物

`workspace/<编号>/raw/webai_clues.json`（中间产物，TTL 自清）：

```json
{
  "_meta": {
    "topic_id": "T-2026-XXX",
    "generated_at": "2026-09-10T17:00:00+08:00",
    "providers_used": ["deepseek", "qwen"],
    "calls_total": 5,
    "degraded_to_websearch": false
  },
  "clues": [
    {
      "id": "W-01",
      "task": "中文事实粗采",
      "provider": "deepseek",
      "fact": "1998年史玉柱借50万二次创业，15万砸江阴广告",
      "source_name": "搜狐财经",
      "url": "https://www.sohu.com/a/1024476663_122507431",
      "verify_status": "accepted",
      "verify_note": "curl 200，正文含关键事实",
      "collected_by": "webai"
    }
  ]
}
```

**进入 `materials.json` 时**：条目补 `collection_route: "webai"` 溯源字段，其余字段与 WebSearch 路线完全一致。

---

## 六、前置检查

进入步骤 4.7 前先确认（任一项不满足→直接跳过，回退 WebSearch）：

```bash
# 1. Chrome CDP 可达
curl -s --max-time 3 http://127.0.0.1:9222/json/version > /dev/null || exit 0

# 2. 至少一家 provider 可达（smoke 前置）
node ~/.claude/skills/agentchat/skills/AgentChat-OneWeb/index.js --smoke 2>&1 | grep -c "REACHABLE"
```

---

## 七、Token 节省预期

| 场景 | 节省幅度 |
|---|---|
| ziliao 采集环节（读网页 Token） | 60-75% |
| 整条选题链路综合 | 40-50% |

**前提**：URL 有效率 ≥80%、子 Agent 保留补缺口职责、provider 可用性正常。
