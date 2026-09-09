# yt-ziliao 更新日志

---

## 2026-09-09

### v2.5.0 — 专注化改造 + 审计链（采集层不做分析层的活）

> 背景：星宇案实战暴露三层角色混乱——采集阶段写出"推荐理由/核心论点/主线倾向"，干了分析的活。
> 本版借鉴 gin-tutorial-source-scan 的两个核心机制：**schema 里不给分析留座位** + **拒绝也落盘的可追溯审计链**。

| 变更 | 说明 | 文件 |
|------|------|------|
| 禁区声明 | SKILL.md 新增"采集层不做分析层的活"：不归纳核心论点/不推荐角度/不写难度优势风险/不站队/不静默丢弃 | SKILL.md |
| 模板 §三 | 「观点分析」→「观点整理（条目清单）」：删"核心论点"归纳段，3.1 只数条数不归纳主张，3.2-3.4 改条目表（主张/归属方/来源/链接） | references/report-template.md |
| 模板 §5.2 | 「主流方式分析」→「竞品覆盖清点」：删"被做透/还有空间"结论词，只留事实记录（谁讲过什么+证据） | references/report-template.md |
| 模板 §5.3 | 「差异化切入建议」→「候选角度清单」：删推荐理由/适合平台/预估难度/差异化优势/潜在风险，只留角度/类型/代表内容/关联素材索引四列 | references/report-template.md |
| 附录审计链 | 新增「拒收与跳过清单」A.1 rejected / A.2 skipped / A.3 unselected，三类为空填"无"不得省略 | references/report-template.md |
| 审计链脚本 | score_materials.py：输入支持 rejected[]/skipped[]（reason 必填，缺行进 invalid）；输出新增 audit 块 + selection.unselected（落选逐条带理由，零静默丢弃）；main() 拆出 main_argv() 供测试 | scripts/score_materials.py |
| 回归测试 | 新增 tests/test_score_materials.py（9 项）：全量可追溯（selected+unselected=input）、理由非空、rejected/skipped 校验、分布约束回归 | tests/ |
| 流程落盘点 | 步骤 5 搜索拒收/跳过当场记 materials.json；步骤 6 去重丢弃记 rejected；步骤 7 附录从 audit 块抄录 | SKILL.md |
| 输出契约 | 「观点分析」章措辞同步为「观点整理」（条目清单，无倾向归纳），fenxi N4 闸门③消费路径不变 | SKILL.md |
| 自检清单 | 新增三项：无核心论点归纳段/角度只盘点不评价/审计附录齐全 | references/report-template.md |

---

### v2.4.0 — 争议点原料清单（四层内容链上游补全）

| 变更 | 说明 | 文件 |
|------|------|------|
| 报告模板 §3.5 | 「争议点原料清单」：同一事实/决策上对立双方主张显式配对（双方主张+来源+可裁决性），只挖掘不判断，禁止倾向性填写；无争议允许注明不硬凑 | references/report-template.md |
| 输出契约 | 新增映射行：报告 3.5 → yt-fenxi N5.5 核心争议点提炼的原料 | SKILL.md |
| 自检清单 | 质量检查新增"争议点原料已显式配对"项 | references/report-template.md |

> 背景：v2.0 脚本实战暴露争议点未被结构化（组委会 vs 车手的救援争议只当普通素材用），
> 四层内容标注（事实/争议/转述/观点）在脚本层立规（yt-jiaoben HR-8）后，上游补挖掘层。

---

### v2.3.0 — siwen 实战摩擦点修复（七项）

| 变更 | 说明 | 文件 |
|------|------|------|
| 新增字段格式真源 | 移植 lark-field-formats.md：URL 字段 `{text, link}` 对象结构（text 在前）、token 原样全文禁缩写；步骤 9 回填处挂铁规指针 | references/lark-field-formats.md, SKILL.md |
| 文档标题白名单 | create 前必做：长破折号→短横线、emoji/特殊符号删除、白名单字符集（中英数+`-_ :`），空标题兜底 `资料报告-<日期>` | references/write-strategy.md §〇, SKILL.md 步骤 8 |
| 降级态规则 | 新增步骤 4.6：进入 WebSearch/WebFetch 降级态必须打印损失范围+等用户确认；损失明文（登录墙/视频元数据/JS 渲染页）；精选阈值收紧（平均可信度 ≥85、低权威存疑 0%） | SKILL.md |
| 输出契约 | 新增「输出契约（下游 yt-fenxi 收货单）」：materials.json/报告字段 → yt-fenxi N2/N4/N5/N6 消费节点映射，缺 overall/D7/URL 即交付未完工 | SKILL.md |
| 反常识探测 | 关键词矩阵新增「反常识探测」行：追问式查询词（为什么/失败原因/争议/背后），为下游 C 闸门③获得感供原料 | references/search-strategy.md |
| 扫描脚本修复 | scan_unsourced.py 豁免 ``` 围栏代码块（JSON 字段名不再被当无出处断言误拦 356 处） | yt-fenxi/scripts/scan_unsourced.py |

> 注：D7 历史脉络维度、降级显式告知（fenxi 侧）、历史沿革关键词为 9/9 早些批次已落地，见 yt-fenxi 仓库提交。

---

## 2026-08-19

### v2.2.0 — OpenCLI 集成与浏览器自动管理

| 变更 | 说明 | 文件 |
|------|------|------|
| 新增 OpenCLI 适配器 | `scripts/opencli_adapter.py` 封装 OpenCLI 安装检测、适配器发现、站点搜索、URL 提取、会话释放 | scripts/opencli_adapter.py |
| 新增平台映射 | `references/platform-mappings.md` 列出 yt-ziliao 场景下可能使用 OpenCLI 的平台及适配器 | references/platform-mappings.md |
| 搜索策略升级 | 明确 OpenCLI 优先、WebSearch/WebFetch 降级；子 Agent 不操作浏览器开关 | references/search-strategy.md |
| 主流程升级 | SKILL.md 增加环境依赖检查中的 OpenCLI 检测、浏览器 profile 一次性绑定、步骤 4.5 浏览器就位检查、步骤 11 浏览器善后清理 | SKILL.md |
| 配置扩展 | `runtime/config.json` 增加 env_check.opencli、browser_profile、browser 配置项 | runtime/config.json |
| 标签防堆积 | 所有 OpenCLI 命令带 `--window background --keep-tab false` | scripts/opencli_adapter.py |

### v2.2.1 — 验证后修复（同日）

| 变更 | 说明 | 文件 |
|------|------|------|
| 配置 schema 校验 | 新增 `schema_version`；步骤 3 检测旧版/不完整配置并重新初始化 | runtime/config.json, SKILL.md |
| profile/doctor 封装 | `opencli_adapter.py` 新增 `profile_use()`、`doctor_check()`、`bridge_status()`、`is_chrome_running()`、`launch_chrome()`、`wait_for_chrome()`；步骤 4.5 统一调用 adapter | scripts/opencli_adapter.py, SKILL.md |
| 清理保证 | 步骤 11 明确要求 try/finally，所有提前终态必须调用 `close_session()` | SKILL.md |
| 字段对齐 | adapter 输出统一使用 `publish_date` 并补充 `language/type/authority/verification/stance` | scripts/opencli_adapter.py, references/platform-mappings.md |
| 返回码检查 | `close_session()` 检查命令返回码 | scripts/opencli_adapter.py |
| 恢复 .paused | 步骤 3 检查 `.paused` 文件，步骤 7.5 增加恢复入口 | SKILL.md |
| 冷门兜底收紧 | `score_materials.py` 少素材时仍保留最低分布约束 | scripts/score_materials.py |
| 文档对齐 | write-strategy.md 四级降级补全；步骤 5 补搜文案修正；profile 绑定路径跨平台说明 | references/write-strategy.md, SKILL.md |

### v2.2.6 -- Agent 自动打开 Chrome 并切换到目标账号

| 变更 | 说明 | 文件 |
|------|------|------|
| 新增 `ensure_browser_with_profile()` | 一步完成：检测 Chrome 状态 → profile 不匹配则强制退出并重启到目标 Chrome profile → 等待 OpenCLI extension 连接 | scripts/opencli_adapter.py |
| `launch_chrome()` 支持 profile | 增加 `profile_dir` 参数，macOS 用 `open -a` + `--profile-directory` 启动指定 profile | scripts/opencli_adapter.py |
| 新增 `quit_chrome()` / `wait_for_chrome_exit()` | 支持策略 B：profile 不匹配时强制退出 Chrome | scripts/opencli_adapter.py |
| 新增 `get_connected_opencli_profile()` | 从 `opencli profile list` 解析当前已连接 profile | scripts/opencli_adapter.py |
| SKILL.md 步骤 4.5 升级 | 改为调用 `ensure_browser_with_profile()`，明确说明会强制重启 Chrome | SKILL.md |
| 版本号 | `schema_version` 更新为 `2.2.6` | SKILL.md, runtime/config.json |

### v2.2.5 -- 修复站点适配器命令遗留空白窗口 + launch_chrome 强制开窗口

| 变更 | 说明 | 文件 |
|------|------|------|
| search() 后清理空白窗口 | 站点适配器命令（如 `youtube search`）即使带 `--keep-tab false` 仍会遗留 `about:blank` 窗口；`search()` 增加 `finally` 调用 `cleanup_leaked_windows()` | scripts/opencli_adapter.py |
| launch_chrome 强制创建窗口 | macOS 下改用 AppleScript `make new window`，确保 Chrome 已在运行但无窗口时也能创建可见窗口，让扩展自动连接 | scripts/opencli_adapter.py |
| 文档同步 | `schema_version` 更新为 `2.2.5` | SKILL.md, runtime/config.json |

### v2.2.4 -- 修复 OpenCLI Browser 标签堆积

| 变更 | 说明 | 文件 |
|------|------|------|
| fetch_url 标签清理 | `browser open/extract` 不支持 `--keep-tab`，改为解析返回的 `page` targetId，提取后用 `browser tab close` 显式关闭标签，避免标签堆积 | scripts/opencli_adapter.py |
| close_session 关闭标签 | 释放会话前先调用 `browser tab list` 关闭所有标签，再 `browser close` 释放会话 | scripts/opencli_adapter.py |
| cleanup_leaked_windows | 新增 macOS 下清理 OpenCLI 残留空白窗口/标签的方法；步骤 11 调用，防止历史堆积 | scripts/opencli_adapter.py, SKILL.md |
| 文档同步 | `SKILL.md` 移除/修正关于 `--keep-tab false` 对 browser 命令的描述；步骤 11 增加残留窗口清理；`schema_version` 更新为 `2.2.4` | SKILL.md, runtime/config.json |

### v2.2.3 — 默认账号绑定 + list_chrome_profiles

| 变更 | 说明 | 文件 |
|------|------|------|
| 新增 `list_chrome_profiles()` | 从 Chrome Local State 直接读取 profile 列表，无需 extension 连接；步骤 6 绑定阶段可完整运行 | scripts/opencli_adapter.py |
| 初始化默认账号绑定 | 步骤 6 新增自动推断逻辑：extension 未连接时按 email 含 `opencli`/`openclaw` 推断；自动选中 Mira 账号 | SKILL.md |
| config 示例更新 | `browser_profile.opencli_profile_id` 示例改为 OpenCLI 内部 ID `g3a5ehu6`；`schema_version` 更新为 `2.2.3` | SKILL.md, runtime/config.json |

### v2.2.2 — 真实环境测试后修复（同日）

| 变更 | 说明 | 文件 |
|------|------|------|
| doctor_check 桥接状态误判 | `opencli doctor` 在扩展未连接时仍返回 0，`doctor_check()` 与 `bridge_status()` 改为同时检查返回码和 stdout 中的 `[FAIL]`/`Connectivity: failed` | scripts/opencli_adapter.py |
| D5 时间分布公式倒置 | `compute_d5_time_distribution()` 原公式奖励集中、惩罚均匀，修正为 `熵/最大熵 × 100` 以奖励时间分布均匀 | scripts/score_materials.py |

### v2.2.1 — 设计审查与结构重构

| 变更 | 说明 | 文件 |
|------|------|------|
| 目录结构重构 | runtime/ 与 references/ 分离；状态文件全部迁移到 runtime/ | 全局 |
| 新增评分脚本 | `scripts/score_materials.py` 统一计算可信度分、D1-D6 完整度评分、精选分布约束 | scripts/score_materials.py |
| 删除 quality-checklist.md | 内容合并到 report-template.md 自检规则 | references/report-template.md |
| 明确依赖边界 | yt-ziliao 只通过 Skill() 调用 lark-* 技能，不直接调用 lark-cli；依赖可用性在初始化阶段检查确认 | SKILL.md |
| 补齐分支终态 | 表格不可用、搜索工具失败、自检拒绝、章节生成失败、配置切换等分支完整定义 | SKILL.md |
| 待核实清单持久化 | 新增 runtime/.verification/<topic>.json | SKILL.md / report-template.md |
| 重新搜集条件 | 仅用户明确表达时才无需确认覆盖 | references/feishu-table-rules.md |
| 全局去重 | 子 Agent 内部去重 + 中央合并节点全局去重 | references/search-strategy.md |
| 超大段落兜底 | 分块策略增加段落内部切分 | references/write-strategy.md |

---

## 2026-07-16

### v2.0.1 — P0 正确性修复

| 问题 | 修复 |
|------|------|
| P0-1: D2公式歧义 | 去掉×100，改为 `min(zh%, en%) - \|zh%-en%\|×0.3`，结果自然在0-100范围 |
| P0-2: D6阻断描述不一致 | quality-checklist.md 同步为"直接降级pending，不补搜" |

---

## 2026-07-16

### v2.0 — 用户反馈问题修复

| 问题 | 修复内容 | 文件 |
|------|---------|------|
| A. D5公式矛盾 | 改为 `(1-熵/最大熵)×100`，阈值≥60 | search-strategy.md |
| B. D6阻断规则不清 | D6<95%直接降级pending，不补搜 | search-strategy.md |
| C. 补搜策略缺失 | 新增补搜动作表（D1-D5各维度） | search-strategy.md §五 |
| D. doc_folder为空 | 为空时强制确认文档存放路径 | SKILL.md 步骤3 |
| E. 自检规则不硬 | 自检失败阻断写入，需用户确认 | SKILL.md 步骤7.5 |

---

## 2026-07-16

### v1.9.1 — 基础设施分层

write-strategy.md 从 216行 精简到 73行：

| 删除 | 保留 |
|------|------|
| 凭证状态判断表（lark-cli自带） | 分块策略（业务判断） |
| 健康检查200ms超时（lark-cli细节） | 四级降级业务语义 |
| 指数退避表格（lark-cli自带） | pending文件结构 |
| folder_token 400绕过（lark-cli bug） | 回读校验业务含义 |
| retry_history详细结构（lark-cli生成） | |

---

## 2026-07-16

### v1.9 — 技能精简与结构优化

| 变更 | 说明 |
|------|------|
| SKILL.md | ~245行 → ~178行 |
| 文件合并 | credibility-rules.md → search-strategy.md |
| 文件合并 | writing-guidelines.md → report-template.md |
| 断裂点修复 | pending恢复逻辑、补搜策略 |

---

## 2026-07-16

### v1.8 — 事故复盘 + 质量门

| 根因 | 防御方案 |
|------|---------|
| 信源URL缺失 | D6 URL覆盖率≥95%阻断写入 |
| token过期不透明 | lark-cli替换封装工具 |
| 重试策略不足 | 指数退避（1s→2s→4s...最多7次） |
| pending状态丢失 | pending离线缓存+下次触发恢复 |
