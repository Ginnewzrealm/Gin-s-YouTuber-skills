# youtube-skills 更新日志

## 2026-09-09

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
