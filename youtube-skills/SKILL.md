---
name: youtube-skills
description: |
  YouTuber 创作工作流总路由（主编排技能，薄路由）。当用户说"推进选题 X / 这个选题下一步做什么 /
  初始化 YouTuber 工作流 / 配置工作区 / 整体进度 / 安装好了吗"等跨技能衔接诉求时触发：
  读选题池状态 → 渲染宏观六阶段进度 → 指出该调用 yt-ziliao / yt-fenxi / yt-jiaoben 中的哪个 → 停。
  不用于：具体资料采集（归 yt-ziliao）、具体分析（归 yt-fenxi）、具体写脚本（归 yt-jiaoben）——本技能只做路由与进度，不碰业务。
---

# youtube-skills 总路由

> 定位：**主编排（core）**——全工作流唯一的路由者与进度渲染者。设计参考《AI技能进度条设计指南》：
> core 渲染宏观仪表盘，子技能只出 micro-checklist，不重复宏观。

## 本技能只做三件事

1. **安装初始化**：问一次工作区根路径 → 落共享配置（全系统路径唯一事实源）
2. **路由**：读用户意图 + 池状态 → 输出"当前处于阶段 N/6，该调 yt-XXX"→ **停**
3. **宏观进度**：每次触发 / 跳转 / 会话恢复，渲染六阶段仪表盘

## 禁区（违反即返工）

- **不做任何业务**：不采集、不分析、不写脚本——越权代劳即违反桥接规范"只桥接"原则
- **不替人过硬闸门**：三处硬闸门（①立项②N8 人审③定稿终审）只标注、不推进
- **不重复渲染子技能微观进度**：core 出宏观，子技能出 micro（指南误区 1）
- **不持有凭证**：lark 鉴权归 lark-* 技能内部；本技能配置只存路径与池定位符
- **不直连飞书 API**：读池经 `references/lark-base-bridge.md` 调 lark-base 技能

## 状态机语义（路由正确性的根基）

| 池状态 | 含义 | 路由到 |
|--------|------|--------|
| 阶段一：想法记录（旧名：想法记录） | 待立项 | 人（硬闸门①）→ 立项后调 yt-ziliao |
| 阶段二：资料研究 | **双义态**：资料未就绪 / 就绪 | 未就绪→yt-ziliao；就绪（有链接+完整度≥60）→yt-fenxi |
| 阶段三：确认选题 | **已过 N8 人审、已立项** | yt-jiaoben（不是 fenxi！fenxi 干完才迁到此状态） |
| 阶段四：内容制作 | 脚本已交付 | 人（硬闸门③定稿终审） |
| 已发布 | 上线完成 | fupan [待开工] |
| 已淘汰 | 终态 | 仅档案 |

## 执行流程

### 触发反馈

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 已触发 YouTuber 工作流总路由
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 步骤 1：初始化检查

读 `~/.config/youtube-skills/config.json`（脚本：`python3 scripts/yt_core.py` 子命令）：

- 不存在 → 走**初始化问答**（一次问一轮，带回车默认）：
  1. 飞书根文件夹？→ 云盘文件夹 token 或链接（各选题交付物以原生 .md 存入其下 `<编号> <标题>/` 子文件夹）→ 必填
  2. 选题池链接（解析 base_token + table_id）？→ 可回车跳过（空则路由时现场问或读 yt-fenxi config.yaml）
  3. 工作区 TTL？→ 默认 30（天，workspace 目录超期未动即清）
- 存在 → 继续；并跑 `skills` 子命令展示子技能安装状态表

### 步骤 2：意图识别与定位

- 用户指名选题（编号/标题）→ 经 lark-base 桥接读池行，取「选题状态」「资料采集」「资料完整度」
- 用户未指名 → 展示池内各状态计数分布，请人指题（不批量推进）

### 步骤 3：渲染与路由（停）

```
python3 scripts/yt_core.py progress --state "<池状态>"     # 宏观仪表盘
python3 scripts/yt_core.py route --state "<池状态>" \
    [--has-materials] [--completeness N]                   # 路由建议（纯映射）
```

输出后**停住**，把路由结论交给用户或按用户事先授权调用子技能：

> 当前处于 YouTuber 工作流阶段 2/6：资料采集。该调：yt-ziliao。等你指令。

调用子技能时按对应桥接文件传参（`references/yt-*-bridge.md`）；子技能开工即切换为其 micro-checklist，core 的宏观仪表盘在**下一次阶段跳转**时再渲染。

### 清理检查点（每次 route/progress 时顺手执行）

遍历各技能 `workspace/<编号>/` 目录，命中任一即删除并打印一行日志（"清理 T-XXXX-XXX 工作区（依据：已发布）"）：
- 选题状态 = 已发布 / 已淘汰 → 立即清
- 目录 mtime 超 `workspace_ttl_days` → 清
- 删除范围只含 `<编号>/` 子目录；`yt-guanjianci/workspace/频道词库.json` 等根文件永不删

### 会话恢复

中断后用户回来 → 重新执行步骤 2-3（读池取最新状态，不凭对话记忆）→ 先输出完整宏观仪表盘，再继续。

## 数据契约

| 项 | 约定 |
|---|---|
| 共享配置 | `~/.config/youtube-skills/config.json`（schema 由 `yt_core.py default_config` 定义；子技能**只读**）。仅三项：`feishu_root_folder_token` / `pool` / `workspace_ttl_days`——无任何本地目录项 |
| 持久层 | 飞书云盘原生 `.md`（`markdown +create/overwrite`）；飞书 `<编号> <标题>/` 文件夹永不删，版本历史 `drive +version-history` |
| 本地工作区 | 各技能内 `<技能>/workspace/<编号>/`，机器流转专用；子技能运行时自清非当前编号目录（当期自清档） |
| 选题池 | 状态机主表，经 lark-base 桥接读写；core 只读状态/资料字段，**不迁移状态**（迁移归子技能 N9 与人） |
| 子技能交接 | 上家推飞书 .md → 下家 `markdown +fetch` 拉回消费（含 keywords.json 经 `05-关键词包.md`、manifest 经 `01b-资料清单.md` 中转）；**工作区不跨技能读**；core 不中介产物内容，只确认产物存在性 |

## 依赖

| 技能 | 强度 | 桥接文件 |
|---|---|---|
| lark-base | 硬依赖（读池定位） | `references/lark-base-bridge.md` |
| yt-ziliao / yt-fenxi / yt-jiaoben | 路由对象（软依赖，未装则路由表标灰+提醒） | `references/yt-ziliao-bridge.md` 等三份 |

## 常见错误

| 错误 | 正确做法 |
|---|---|
| 用户说"分析这个选题"，core 自己动手分析 | core 只定位+路由；分析是 yt-fenxi 的活，按桥接文件转交 |
| 把「阶段三：确认选题」路由回 yt-fenxi | 该状态=已过 N8 人审，路由到 yt-jiaoben（状态机语义表） |
| 一次渲染宏观+微观全套 | core 只渲染宏观；micro 归子技能（指南误区 1） |
| 把本地路径写进表格字段 | 字段只存飞书 URL 或人读摘要；本地路径机器自己算（编号为主键），写进表是无效信息 |
| 跨技能直接读对方 workspace | 一律经飞书 .md `+fetch` 中转；工作区不跨技能读 |
| 人没过硬闸门就推进下一阶段 | 只标注闸门位置，等人明确拍板（指南误区 3） |

### lark-cli 已验证命令序列（2026-09-10 实战沉淀，别再试错）

```bash
# Markdown 文件（--file 必须当前目录相对路径，先 cd 到文件所在目录）
lark-cli markdown +create --file 01-资料报告.md --folder <folder_token>
lark-cli markdown +fetch --file <file_token>          # 拉回本地
lark-cli markdown +overwrite --file <file_token> --content-file 01b-资料清单.md

# 多维表格（--json 必须 ./相对路径，/tmp 绝对路径会被拒）
lark-cli base +record-search --base <token> --table <tbl_id> --keyword "脑白金"
lark-cli base +record-batch-create --base <token> --table <tbl_id> --json @./payload.json
lark-cli base +record-batch-update --base <token> --table <tbl_id> --json @./payload.json
lark-cli base +field-list --base <token> --table <tbl_id>

# 字段类型坑（实战踩过）
# text 字段：URL 回填用裸字符串，不是 {"link":...} 对象
# url 字段：同理裸字符串；select 字段：值=["选项名"] 数组
# field-update 是 PUT 全量语义；ndjson 输出是 manifest，真实数据在 record_file 指针里
```
