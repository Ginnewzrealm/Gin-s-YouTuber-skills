# youtube-skills 更新日志
## 2026-09-10

### v0.3.0 — 存储与工作区重构：配置 schema v2 + 三层模型 + 清理检查点

> 背景：规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md——交付物全部原生 .md 上飞书（唯一持久层），
> 本地收敛为各技能内 workspace（机器流转），选题表=索引。
> - 配置 schema v1→v2：`dirs.*`/`workspace_root` 全删，仅余 `feishu_root_folder_token` / `pool` / `workspace_ttl_days`（默认 30）
> - 初始化问答：工作区根目录 → 飞书根文件夹（必填）+ TTL
> - 新增清理检查点（每次 route/progress 执行）：已发布/已淘汰即清 + TTL 兜底 + 当期自清；根文件（频道词库.json）免清
> - 数据契约改三层：飞书 .md 持久层 / 技能内 workspace / 池=索引；跨技能交接一律 +fetch 中转，工作区不跨技能读

## 2026-09-09

### v0.2.0 — 状态机扩容：制作中/待发布 + 阶段五/六拆分（宏观六阶段→七阶段）

> 背景：yt-zhizuo 建成后发现状态机断档——「阶段四：内容制作」之后直接跳「已发布」，
> 视频制作期是黑箱；且发布包装与四件套混在阶段五一格。本次拆格补态：
> 阶段五 内容制作（yt-zhizuo，池状态「制作中」）／阶段六 发布包装（agrici metadata，池状态「待发布」）。
> 硬闸门 3→4（新增④挑标题）；SUB_SKILLS 增 yt-zhizuo；dirs 增 briefs（制作四件套）。

### v0.1.0 — 总路由（主编排）技能诞生

> 背景：三技能（ziliao/fenxi/jiaoben）实战两个选题后暴露——无路由者，agent 靠脑补调兵导致开场角色混乱；
> 工作区路径无唯一事实源；无全局进度视图。按《工作流架构设计方案》"将来阶段"（dbskill 式薄路由）提前落地，
> 设计参考《AI技能进度条设计指南》（core 宏观/子技能 micro 两层）与《技能桥接模式技术规范》（四份五章节桥接文件）。

| 变更 | 说明 | 文件 |
|------|------|------|
| 核心脚本 | yt_core.py：init/route/progress/skills 四子命令；状态机路由纯映射（17 项单测）；宏观六阶段渲染；工作区共享配置落 `~/.config/youtube-skills/config.json` | scripts/yt_core.py |
| 主文件 | 三件职责（初始化/路由/宏观进度）+ 禁区五条 + 状态机语义表（阶段三=已过 N8 归 jiaoben 等易错语义） | SKILL.md |
| 桥接契约 | lark-base + 三个子技能共四份，严格五章节格式（职责边界/依赖检测/输入参数/输出结果/异常处理） | references/*-bridge.md |
| 意图路由表 | 用户说什么→谁接；状态与意图打架的裁决顺序 | references/routing-table.md |
| 子技能衔接 | fenxi/jiaoben/ziliao 各加一行：被 core 调用时不输出宏观/定位句（防重复渲染，指南误区 1） | 三个 SKILL.md |
| 宏观六阶段 | 选题立项→资料采集→选题分析→脚本制作→发布包装→数据复盘；硬闸门①②③对应状态迁移点；阶段 5/6 占位待开工 | scripts/yt_core.py PHASES |

> 红线重申：薄路由 ≤300 行业务零逻辑；不替人过硬闸门；agrici 式重协调器仍为明确不排项。
