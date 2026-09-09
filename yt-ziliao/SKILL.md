---
name: yt-ziliao
description: |
  当用户围绕某个选题或事件，要求进行**多源资料调研、整理和报告输出**时，使用本技能。

  本技能的典型触发场景：
  - 用户提到选题表中的某个选题，要求搜集全网资料
  - 用户要求为某个事件/人物/产品梳理来龙去脉
  - 用户要求整理素材并生成结构化的资料报告

  执行流程：读取选题表定位选题 → 全网多源搜索 → 资料筛选与可信度评分 → 按六章模板生成报告 → 写入飞书文档 → 将文档链接回填到表格「资料采集」列。

  关键判定：用户意图是**围绕一个主题做系统性资料调研并输出报告**，而不是保存单条 URL 或单个文件到本地。

  不要用于简单的名词解释、深度叙事研究报告（横纵分析法）、纯标题生成，也不要用于不需要表格回填的纯搜索请求。
---

# 自媒体选题资料采集

> 触发 → 读表定位 → 全网搜索 → 资料梳理 → 生成报告 → 飞书输出 → 回填链接

## 文件结构

```text
yt-ziliao/
├── SKILL.md              # 本文件
├── references/           # 静态参考文件（只读）
│   ├── report-template.md
│   ├── search-strategy.md
│   ├── write-strategy.md
│   ├── feishu-table-rules.md
│   ├── lark-field-formats.md
│   ├── platform-mappings.md
│   └── CHANGELOG.md
├── runtime/              # 运行时生成文件
│   ├── config.json
│   ├── .runs/
│   ├── .pending/
│   ├── .verification/
│   └── .paused/
└── scripts/
    ├── score_materials.py
    └── opencli_adapter.py   # OpenCLI 封装层（步骤 4.5/5/11 使用）
```

> 注意：`runtime/` 目录下的文件为运行时生成，**不应打包到分发技能包中**。打包前请清空或排除 `runtime/` 目录。
>
> 版本历史见 [references/CHANGELOG.md](references/CHANGELOG.md)。

## 断点续跑

进度文件 `runtime/.runs/<topic>.json` 维护实时进度。中断后再次触发同一选题时，从第一个 pending 步骤继续。

## 脚本与 Schema

### score_materials.py

调用方式：

```bash
python3 scripts/score_materials.py <materials.json>
```

输入 `materials.json` schema：

```json
{
  "topic": "萝卜快跑在武汉运营",
  "items": [
    {
      "title": "...",
      "url": "https://...",
      "platform": "微博",
      "language": "zh",
      "publish_date": "2024-07-15",
      "type": "新闻报道",
      "authority": "高",
      "verification": "多方证实",
      "stance": "中立"
    }
  ]
}
```

输出 schema：

```json
{
  "topic": "萝卜快跑在武汉运营",
  "input_count": 73,
  "completeness": {
    "D1_平台覆盖": 80.0,
    "D2_语言覆盖": 75.0,
    "D3_来源类型": 100.0,
    "D4_立场覆盖": 60.0,
    "D5_时间分布": 70.0,
    "D6_URL覆盖率": 96.0,
    "overall": 80.2,
    "passed": true
  },
  "selection": {
    "selected_count": 45,
    "avg_credibility": 78.5,
    "distribution": {
      "高权威_多方证实": 0.40,
      "中权威_单一来源": 0.35,
      "低权威_单一来源": 0.10,
      "低权威_存疑": 0.02
    },
    "passed": true,
    "conditional_pass": false,
    "selected": [{ "title": "...", "url": "...", "credibility": 88.0 }]
  },
  "suggestions": ["D4 立场覆盖不足，补搜质疑方观点"]
}
```

### runtime/.paused/<topic>.json

当用户在自检阶段拒绝继续时生成：

```json
{
  "topic": "萝卜快跑在武汉运营",
  "paused_at": "2026-07-19T14:32:00Z",
  "reason": "self_check_rejected",
  "pending_verification": [
    {
      "text": "2024年Q3营收达15亿美元",
      "chapter": "二、已确认事实",
      "source_url": null,
      "status": "open"
    }
  ],
  "generated_report": "# [选题名称] 资料汇总分析报告\n...",
  "next_action": "等待用户补充信息后继续"
}
```

恢复时读取该文件，提示用户补充信息，然后继续流程。

---

## 依赖技能

触发后并行加载：
```
Skill(skill="lark-doc")     # 文档创建与写入
Skill(skill="lark-sheets")  # 电子表格读写
Skill(skill="lark-base")    # 多维表格读写
```

`yt-ziliao` 只通过 `Skill()` 调用上述技能，不直接调用 `lark-cli`。业务层负责决定写什么、如何分块、失败如何降级；lark-* 技能负责实际执行飞书 API 调用（其内部可能使用 lark-cli 等工具，但对本技能不透明）。

---

## 配置持久化

首次触发时确认：
1. 选题表格（名称/链接/ID）→ 自动检测表格类型
2. 字段映射：读取字段（默认：选题标题）→ 写入字段（默认：资料采集）
3. 文档存放路径（必填，不能为空）

配置保存到 `runtime/config.json`，后续存在且完整则直接复用。

### 环境依赖检查

首次初始化或检测到配置不完整（缺少 `schema_version`/`env_check`/`browser_profile`/`browser`）时，执行以下检查。任一关键依赖不满足则提示用户安装/配置，不继续执行；OpenCLI 不可用则降级而非终止。

1. **配置 schema 版本**：检查 `config.json` 是否包含 `schema_version` 以及 `env_check`、`browser_profile`、`browser` 字段
   - 缺失任一字段 → 视为旧版配置，进入初始化补全流程
2. **依赖技能可用性**：当前环境是否已安装 `lark-doc`、`lark-sheets`、`lark-base` 技能
   - 可通过一次轻量级 `Skill(skill="lark-doc")` 调用的返回或错误判断
   - 若不可用，提示用户：「本技能依赖 lark-doc / lark-sheets / lark-base，请先安装这三个技能」
3. **运行时目录**：确认 `runtime/` 目录可读写（默认位于技能安装目录下）
   - 若环境限制无法写入，询问用户指定可写路径，保存到 `config.json` 的 `runtime_dir`
4. **搜索与提取工具**：确认当前环境可用 `WebSearch` 和 `WebFetch` 工具
   - 若不可用，提示用户本技能无法运行，或引导使用手动提供资料模式
5. **OpenCLI 与浏览器环境**：
   - 检查 `opencli` 是否已安装：`opencli --version`
   - 若已安装，执行 `opencli doctor` 检查浏览器桥接状态
   - 若 OpenCLI 未安装或桥接失败，**不终止技能**，标记 `opencli_available: false`，后续全部走 WebSearch/WebFetch 降级
6. **浏览器 profile 绑定（仅首次初始化或 profile 失效时）**：
   - 若 `config.json` 中不存在 `browser_profile.opencli_profile_id`，执行一次性绑定：
     - 调用 `OpenCLIAdapter.list_chrome_profiles()` 从 Local State 读取 Chrome profile 列表（无需 extension 连接），用于展示和设置 `chrome_profile_id` / `chrome_profile_name`
     - 若 OpenCLI extension 已连接（`doctor_check()` 为 true），执行 `opencli profile list` 获取 **OpenCLI 内部 profile ID**（如 `g3a5ehu6`）——这是 extension 识别的真实 ID，与 Chrome 显示名称（`Profile 1`）不同
     - 若 extension 未连接，**自动选择 email 包含 `openclaw` 或 `opencli` 的 Chrome profile**（通常即安装了 OpenCLI 扩展的账号），并尝试验证 extension 连接后获取真实 OpenCLI ID；若无法自动判断，列出 profiles 让用户选择
     - 若所有方式均无法获取 profile，标记 `opencli_available=false`，走 WebSearch/WebFetch 降级
     - 调用 `OpenCLIAdapter.profile_use()` 切换到 `opencli_profile_id`
     - 保存到 `config.json` 的 `browser_profile` 字段

环境依赖检查结果保存到 `runtime/config.json`：

```json
{
  "schema_version": "2.2.6",
  "env_check": {
    "checked_at": "2026-07-19T...",
    "lark_doc_available": true,
    "lark_sheets_available": true,
    "lark_base_available": true,
    "web_search_available": true,
    "web_fetch_available": true,
    "opencli_available": true,
    "opencli_doctor_passed": true,
    "runtime_dir": "./runtime"
  },
  "browser_profile": {
    "chrome_profile_id": "Profile 1",
    "chrome_profile_name": "Mira",
    "opencli_profile_id": "g3a5ehu6"
  },
  "browser": {
    "auto_open_browser": true,
    "auto_close_browser": true,
    "connection_retry_interval": 2,
    "connection_retry_max": 5
  }
}
```

后续触发时，如 `env_check` 已存在且通过，跳过环境检查；如任一依赖变为不可用，重新提示。

### 配置切换

当用户提到的表格与 `config.json` 中的 `table_id`/`base_token` 不一致时，询问用户是否切换到新表格：
- 用户确认 → 重新执行初始化并覆盖 `runtime/config.json`
- 用户拒绝 → 仍用旧表尝试匹配

### 配置健康检查

每次读表前，比对 `config.json` 中的 `table_id`/`field_read`/`field_write` 与实时字段清单。若不一致，要求用户重新初始化。

### 用户拒绝提供文档路径

若 `doc_folder` 为空且用户拒绝提供，干净退出，不保存不完整配置，不生成任何输出。

---

## 执行流程

### 步骤 1：触发反馈

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 已触发选题资料采集
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

并行加载 lark-doc、lark-sheets、lark-base。

### 步骤 2：选题名解析 + 关键词提炼

**解析选题名**（按优先级）：
1. 引号包裹：`对选题表的'萝卜快跑'搜集` → 提取引号内文字
2. "的"字指代：`选题表里的萝卜快跑搜集一下` → 提取"选题表里的"之后部分
3. 直接描述：`帮我搜一下萝卜快跑的资料` → 提取"搜一下"和"的资料"之间

**输入校验**：
- 解析不到选题名 → 要求用户重新提供
- 一次提及多个选题 → 列出候选，询问先处理哪一个
- 特殊字符 → 转义或提示

**提炼搜索关键词**：中英文各 3-5 个，覆盖官方名称、俗称、相关人物/公司、关键概念。

```
🎯 选题名称：「萝卜快跑在武汉运营」
🔑 中文关键词：萝卜快跑 武汉 无人驾驶 网约车 百度Apollo
🔑 英文关键词：Baidu Apollo Go Wuhan robotaxi autonomous driving
```

### 步骤 3：初始化检查 + Pending 检测

1. 检查 `runtime/config.json`：
   - 不存在 → 执行初始化
   - 存在但 `doc_folder` 为空 → **强制要求用户确认文档存放路径**；拒绝则退出
   - 存在但缺少 `schema_version`、`env_check`、`browser_profile` 或 `browser` 任一字段 → **视为旧版/不完整配置，重新执行初始化**，保留用户已确认的 table_id/field_read/field_write/doc_folder 等有效字段，仅补充缺失的默认配置并重新检测环境
   - 存在且完整 → 执行配置健康检查 → 继续
2. 检查 `runtime/.runs/<topic>.json` — 存在则从 pending 步骤继续
3. 检查 `runtime/.pending/<topic>.json` — 存在则询问用户是否恢复写入
4. 检查 `runtime/.verification/<topic>.json` — 存在则恢复待核实清单
5. 检查 `runtime/.paused/<topic>.json` — 存在则进入步骤 7.5 恢复流程（见步骤 7.5）

### 步骤 4：读表定位

1. 实时获取字段清单（不依赖缓存字段名）
2. 读取完整行数据
   - `field_read`（默认：选题标题）用于匹配
   - `field_write`（默认：资料采集）用于回填
   - 其他字段作为可选元数据，采用语义启发式识别（切入视角、语言版本、法律风险等），有则纳入决策，没有不阻塞
3. 搜索匹配行：先精确匹配，再模糊匹配

结果处理：
- **成功**：`📖 已定位选题 → 🔍 开始全网搜索...`
- **未找到**：列出最接近的 2-3 个选题，询问用户
- **表格不可用**：提示原因，询问是否跳过表格先执行
  - 用户选择跳过 → 仍生成飞书文档，但不执行回填，完成汇报标注「⚠️ 未回填表格」

### 步骤 4.5：浏览器就位检查（OpenCLI 前置）

如果 `config.json` 中 `env_check.opencli_available` 为 true，则在搜索前通过 `scripts/opencli_adapter.py` 执行浏览器就位检查：

1. **确保 Chrome 已打开并连接到目标 profile**：调用 `OpenCLIAdapter.ensure_browser_with_profile(<browser_profile.opencli_profile_id>, <browser_profile.chrome_profile_id>)`
   - 该方法会自动处理以下情况：
     - Chrome 未运行 → 用目标 Chrome profile 启动
     - Chrome 已运行但目标 OpenCLI profile 未连接 → **强制退出 Chrome 并重启到目标 profile**（会关闭当前所有 Chrome 窗口）
     - 目标 profile 已连接 → 直接返回成功
   - 成功 → 继续下一步
   - 失败 → 记录原因，标记 `opencli_available=false`，降级为 WebSearch/WebFetch 并继续
2. **连接探测（二次确认）**：调用 `OpenCLIAdapter.doctor_check()`
   - 成功 → 继续下一步
   - 失败 → 提示用户：「请在 Chrome 中点击 OpenCLI 扩展图标激活连接，激活后告诉我继续，或回复“跳过”直接降级到 WebSearch」；用户选择跳过时标记 `opencli_available=false` 并降级到 WebSearch/WebFetch

**注意**：
- 此步骤由主流程串行执行，子 Agent 不操作浏览器开关。
- `ensure_browser_with_profile` 会在 profile 不匹配时强制重启 Chrome，**会关闭用户当前所有 Chrome 窗口**，这是策略 B 的自动行为。

### 步骤 4.6：降级态规则（`opencli_available=false` 时强制生效）

**显式告知（强制）**：进入降级态时，必须向用户打印一行告知并**等确认**后方可继续：

> ⚠️ 本次采集走 WebSearch/WebFetch 降级档（OpenCLI 不可用，原因：___）。精度损失：登录墙平台内容取不到、视频元数据缺失、JS 渲染页面只能拿到摘要。确认继续请回复"继续"，或修复 Chrome/OpenCLI 后重试。

**损失范围（明文）**：
- 登录墙内容（部分社媒、论坛）→ 不可达，对应维度得分按实际缺失计
- 视频平台 → 只有标题/简介级元数据，无逐字稿
- 依赖 JS 渲染的页面 → WebFetch 只能拿到服务端渲染部分

**精选阈值收紧（降级态）**：
- 平均可信度分 ≥85（常态 ≥70）
- 低权威+存疑 占比 0%（常态 ≤5%）
- 降级原因写入报告头部元信息，供下游 yt-fenxi 判断原料质量

### 步骤 5：全网搜索

4个子Agent并行，但**不直接操作浏览器**：
- **中文新闻/社交媒体**：微博、知乎、百度、36氪等
- **英文新闻/社交媒体**：BBC、NYT、Reddit、Hacker News等
- **官方信息/深度来源**：官方公告、学术论文、行业报告
- **视频平台**（仅复杂选题）：B站、YouTube

子 Agent 生成搜索词和候选 URL 后，主流程统一调用 OpenCLI 或 WebSearch/WebFetch 读取内容。

视频 Agent 启动条件：
- 自动启动：选题涉及事件/产品/人物，或包含「评测」「体验」「发布会」等高相关词
- 自动跳过：选题偏向政策、法律、学术论文
- 用户显式覆盖：用户说「多找点视频素材」时强制启动

搜索要求：
- 每个 Agent **目标** ≥20条有效资料，合计 **目标** ≥60条
- 单 Agent 未达 20 条不阻断，以综合完整度评分为准
- 素材记录：标题、URL、来源平台、发布日期、语言、可信度

搜索完成后调用 `scripts/score_materials.py` 计算完整度评分（D1-D7，含 D7 历史脉络）。

**完整度评分结果处理**：
- overall ≥80 且 D6 ≥95% → 进入资料梳理
- overall 60-79 且 D6 ≥95% → 按补搜动作表补搜
- D6 < 95% → **直接降级 pending，不补搜**，提示用户资料 URL 缺失过多

**搜索工具完全失败处理**：
- 记录失败原因到 `runtime/.runs/<topic>.json`
- 向用户报告搜索工具不可用
- 提供选项：稍后重试 / 手动提供资料 / 取消任务
- 禁止在搜索失败时生成空报告

### 步骤 6：资料梳理

子 Agent 只负责本平台内去重。中央合并节点收到所有结果后执行全局去重（URL 完全一致 + 标题相似度 >85%）。

对每条资料标注：
- **类型**：新闻报道/官方发布/社交媒体/论坛/视频/学术等
- **权威性**：高/中/低
- **核实状态**：多方证实/单一来源/存疑待核实
- **立场**：支持方/质疑方/中立

调用 `scripts/score_materials.py` 计算可信度分与精选分布：
- 可信度分 = 权威性×40% + 核实状态×40% + 新鲜度×20%
- 精选 30-80 条，分布约束：
  - 高权威+多方证实 ≥30%
  - 中权威+单一来源 ≤40%
  - 低权威+单一来源 ≤15%
  - 低权威+存疑 ≤5%
  - 平均可信度分 ≥70
- `passed=true` → 进入步骤 7
- `passed=false` 且 `conditional_pass=true`（冷门领域，总素材 <10 条）→ 向用户说明分布约束已放宽，询问是否继续生成报告；用户确认后继续，用户拒绝时进入步骤 11 清理后退出
- `passed=false` 且 `conditional_pass=false` → 按 suggestions 补搜或用户豁免

### 输出契约（下游 yt-fenxi 收货单）

yt-ziliao 的产物被 yt-fenxi 按以下映射消费，字段名以 `materials.json` 为准：

| yt-ziliao 产物 | yt-fenxi 消费节点 | 用途 |
|---|---|---|
| 报告 URL（回填「资料采集」字段） | N2 资料就绪检查 | 链接有效 + `overall ≥ 60` 才算就绪 |
| `overall` + D1-D7 分项 | N2 / N3 | 就绪判定 + 机评 Archive 维度参考 |
| **D7 历史脉络覆盖度** | N6 深度揭示力评分 | D7 < 40 → 深度评分旁标"原料不足" |
| 素材清单（标题/URL/平台/日期/可信度） | N5 核验 + N4 闸门① | 信源计数（工商/司法/深度报道级 ≥2）与逐条核验 |
| 报告「观点分析」章 + 反常识点 | N4 闸门③ | 获得感 ≥40 的计分原料 |
| 涉及敏感主体（报告内标注） | N4 闸门② | 标雷区，供下游法律预审 |
| 报告「历史沿革」类素材 | N6 ②历史脉络层 | 历史层角度的论据原料 |

缺 `overall`/`D7`/报告 URL 任一项 = 交付未完工，yt-fenxi 有权按"资料未就绪"退回。

### 步骤 7：生成报告

按六章模板撰写，格式见 [references/report-template.md](references/report-template.md)。

每写完一章更新进度文件 `report_chN: done`。

**章节生成失败处理**：
- 单章失败先重试 3 次
- 仍失败 → 记录 `report_chN: failed` 和失败原因
- 询问用户：跳过该章 / 重试 / 中止任务

### 步骤 7.5：自检（硬约束）

**在写入飞书文档之前必须执行，且自检失败则阻断写入**：

1. 逐章扫描具体数字、人名、时间、机构名、金额
2. 无来源链接的强制追加 `[待核实]`
3. 生成待核实清单，保存到 `runtime/.verification/<topic>.json`
4. 将清单中**独特且必要**的质量检查项（搜索覆盖、资料质量、报告完整性、飞书输出、写作禁区）纳入自检范围

**自检失败处理**：
- 阻断写入飞书文档
- 询问用户：「自检发现N条待核实信息，是否继续写入？确认后强制写入，跳过待核实标注。」
- 用户确认 → 强制写入，交付时附带待核实清单
- 用户拒绝 → 暂停，保存状态到 `runtime/.paused/<topic>.json`，等用户补充信息后再继续

**从 `.paused` 恢复**：
- 步骤 3 检测到 `runtime/.paused/<topic>.json` 存在时，读取其中的 `generated_report` 和 `pending_verification`
- 向用户展示待核实清单，询问是否已补充信息
- 用户确认已补充 → 回到步骤 7.5 重新自检，然后继续步骤 8
- 用户选择取消 → 进入步骤 11 清理后退出
- 用户要求重新搜集 → 删除 `.paused` 文件，回到步骤 5 重新搜索

### 步骤 8：飞书文档输出

见 [references/write-strategy.md](references/write-strategy.md)：
- 通过 `Skill(skill="lark-doc")` 创建/写入文档
- **创建前文档标题必须按 write-strategy.md §〇 白名单清洗**（长破折号/emoji 会触发 400 安全校验）
- 分块策略（<30KB整体 / 30-50KB按章 / >50KB二次切分）
- 超长段落增加段落内部切分兜底
- 四级降级：write → append → table → pending

### 步骤 9：链接回填

通过 `Skill(skill="lark-sheets")` 或 `Skill(skill="lark-base")` 回填 `field_write`（资料采集）字段：
- 值为空 → 直接写入
- 值已有 → 询问用户是否覆盖
- 重新搜集 → 覆盖旧链接，无需确认（仅当用户明确说「重新搜集」「再搜一次」「更新资料」时触发）

回填后复查，不一致则重试。

**格式铁规**：「资料采集」是 URL 字段，必须写 `{"text": "显示文本", "link": "https://..."}` 对象（text 在前 link 在后），裸字符串必报 URLFieldConvFail；token/ID 从 `runtime/config.json` 原样全文取、禁缩写。格式真源见 [references/lark-field-formats.md](references/lark-field-formats.md)。

### 步骤 10：完成汇报

```
✅ 资料汇总报告已完成
📄 飞书文档：[选题名称] 资料汇总分析报告
🔗 文档链接：https://....feishu.cn/docx/...
📋 已更新选题清单「资料采集」字段
⚠️ 待核实项：N条（见上方清单）
⏱️ 本次资料采集耗时 X 分 X 秒
```

若跳过表格，则改为：
```
⚠️ 本次未回填表格：[原因]
```

### 步骤 11：浏览器善后（无论成功失败都执行）

主流程应使用 `try/finally`（或等效机制）确保本步骤在所有分支上执行：

1. **释放 OpenCLI 会话**：调用 `OpenCLIAdapter.close_session("yt-ziliao")`
   - 返回 False 时记录失败原因，不阻断汇报
   - 若 `opencli_available=false`，`close_session()` 内部检查后会安全跳过
2. **清理残留窗口/标签**：调用 `OpenCLIAdapter.cleanup_leaked_windows()`（macOS）
   - 关闭仅包含 `about:blank` / `chrome://newtab` / `OpenCLI Browser` 标题的窗口
   - 不会关闭用户正常浏览的窗口
3. **清理标签**：站点适配器命令已带 `--keep-tab false`；`browser open/extract` 由 `OpenCLIAdapter.fetch_url()` 内部通过 `browser tab close` 清理。`close_session()` 会先 `browser tab list` 关闭全部会话标签，再释放会话
3. **不关闭浏览器进程**：由于 Chrome 是用户可能正在使用的进程，技能只清理标签和会话，不执行退出整个 Chrome 的操作

> 注意：此步骤在业务成功、失败、报错退出、用户取消、自检暂停、D6 降级 pending 等所有路径上都必须执行。任何提前终态分支在返回用户前必须先调用 `OpenCLIAdapter.close_session()`。

---

## 关键规则

- 不硬编码字段名，每次操作前实时读取字段清单
- 事实和观点严格分开，事实标注核实状态，观点标注立场
- 不编造信息，搜不到标注「暂缺/存疑」
- 禁止在未经复查的情况下回复"已写入"
- **自检失败必须阻断写入**，等待用户确认
- 技能层不设超时，依赖底层工具超时和断点续跑
