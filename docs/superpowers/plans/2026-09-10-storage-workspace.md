# 存储与工作区重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 交付物全部以原生 .md 上飞书（唯一持久层），本地收敛为各技能内 workspace（三档自清），core 配置从 dirs.* 塌缩为 3 值，跨技能交接全部经飞书 +fetch。

**架构：** 规格见 `docs/superpowers/specs/2026-09-10-storage-workspace-design.md`（commit ad69ad9）。唯一代码改动在 youtube-skills/scripts/yt_core.py（config schema v1→v2）；其余全部为 SKILL.md/references 文本层改动 + 既有机械闸回归。

**技术栈：** Python 3.9+ / pytest / lark-cli（markdown +create/+overwrite/+fetch）

**全局铁律（每个任务都适用）：**
- 池 token `DvQtb4yCAaFw1FsSbXBcYiPdnhc` 原样全文，禁缩写
- 表格字段一律"空则填、不覆盖"（状态机/资料完整度除外）
- 只改列出的文件，不动扫描闸脚本逻辑

---

## 文件清单

| 文件 | 变更 | 职责 |
|---|---|---|
| `youtube-skills/scripts/yt_core.py` | 改 | default_config schema v2（feishu_root/pool/ttl），删 dirs 与 resolve_dir |
| `youtube-skills/tests/test_yt_core.py` | 改 | test_default_config 适配 v2 |
| `youtube-skills/SKILL.md` | 改 | 初始化问答、数据契约、清理检查点 |
| `yt-ziliao/SKILL.md` | 改 | 步骤8/9 交付改 .md 推送；manifest 改 01b 中转；删 doc_folder 问答 |
| `yt-ziliao/references/write-strategy.md` | 改 | lark-doc→lark-markdown；分块/四级降级→整文件+pending |
| `yt-ziliao/references/report-template.md` | 改 | 头部交付说明 |
| `yt-fenxi/SKILL.md` | 改 | 铁律42（卡可进飞书）、init 删问答2、N9 加分析卡链接、数据契约 |
| `yt-fenxi/references/analysis-card-template.md` | 改 | 交付说明（工作区+飞书双写） |
| `yt-fenxi/references/pool-field-map.md` | 改 | A 区加「分析卡链接」；字段计数 36→26；决定#5 扩为 4 字段 |
| `yt-jiaoben/SKILL.md` | 改 | 阶段6 交付改 .md；删「脚本字数」回填（字段不存在） |
| `yt-zhizuo/SKILL.md` | 改 | 输出目录→技能内 workspace；交付改 .md |
| `yt-zhizuo/references/briefs-template.md` | 改 | 头部交付说明 |
| `yt-guanjianci/SKILL.md` | 改 | 落盘→workspace；新增 05-关键词包.md 推送与字段摘要回填 |
| 六技能的 `references/CHANGELOG.md` | 改 | 每任务末尾加条目 |

---

### 任务 1：core 配置收敛（唯一代码改动，TDD）

**文件：**
- 修改：`youtube-skills/scripts/yt_core.py:146-181`（default_config/resolve_dir）、`:205-231`（init 子命令）
- 测试：`youtube-skills/tests/test_yt_core.py:103-118`（test_default_config）

- [ ] **步骤 1：改写失败测试**

把 `test_default_config` 方法整体替换为：

```python
    def test_default_config(self):
        cfg = default_config()
        self.assertEqual(cfg["version"], 2)
        self.assertIn("feishu_root_folder_token", cfg)
        self.assertIn("pool", cfg)
        self.assertIn("workspace_ttl_days", cfg)
        self.assertEqual(cfg["workspace_ttl_days"], 30)
        self.assertNotIn("dirs", cfg)
        self.assertNotIn("workspace_root", cfg)
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd youtube-skills && python3 -m pytest tests/test_yt_core.py::TestYtCore::test_default_config -q
```
预期：FAIL（`dirs` 仍存在 / `workspace_root` 仍在）

- [ ] **步骤 3：改 default_config 与 CLI**

`yt_core.py` 中 `def default_config(workspace_root: str = "~/Documents/YouTuber工作流") -> dict:` 整函数替换为：

```python
def default_config() -> dict:
    return {
        "version": 2,
        "feishu_root_folder_token": "",
        "pool": {"base_token": "", "table_id": "",
                 "note": "选题池定位符；空则路由时现场问用户或读 yt-fenxi config.yaml"},
        "workspace_ttl_days": 30,
        "initialized_at": datetime.now(timezone.utc).isoformat(),
    }
```

删除 `resolve_dir` 函数（179-180 行）。`p_init` 参数 `--workspace` 改为 `--feishu-root`，`init` 分支替换为：

```python
    if args.cmd == "init":
        cfg = default_config()
        cfg["feishu_root_folder_token"] = args.feishu_root
        cfg["pool"]["base_token"] = args.base_token
        cfg["pool"]["table_id"] = args.table_id
        save_config(CONFIG_PATH, cfg)
        print(json.dumps({"config_path": CONFIG_PATH, "config": cfg}, ensure_ascii=False, indent=2))
```

- [ ] **步骤 4：全量回归 core**

```bash
cd youtube-skills && python3 -m pytest tests/ -q
```
预期：全部 PASS（test_yt_core 全部，含 13 条路由用例不受影响）

- [ ] **步骤 5：Commit**

```bash
git add youtube-skills/scripts/yt_core.py youtube-skills/tests/test_yt_core.py
git commit -m "refactor(core): 配置schema v2收敛——feishu_root+pool+ttl，删dirs/workspace_root"
```

---

### 任务 2：core SKILL.md 数据契约与初始化

**文件：**
- 修改：`youtube-skills/SKILL.md`（步骤1 初始化问答 54-57 行、步骤3 后加清理检查点、数据契约 82-89 行、常见错误 105 行）

- [ ] **步骤 1：改初始化问答**

把：
```
  1. 工作区根目录？→ 默认 `~/Documents/YouTuber工作流`
  2. 选题池链接（解析 base_token + table_id）？→ 可回车跳过（空则路由时现场问或读 yt-fenxi config.yaml）
```
替换为：
```
  1. 飞书根文件夹？→ 云盘文件夹 token 或链接（各选题交付物以原生 .md 存入其下 `<编号> <标题>/` 子文件夹）→ 必填
  2. 选题池链接（解析 base_token + table_id）？→ 可回车跳过（空则路由时现场问或读 yt-fenxi config.yaml）
  3. 工作区 TTL？→ 默认 30（天，workspace 目录超期未动即清）
```

- [ ] **步骤 2：步骤3 末尾加清理检查点**

在 `输出后**停住**` 段（72-76 行）之后加一节：

```markdown
### 清理检查点（每次 route/progress 时顺手执行）

遍历各技能 `workspace/<编号>/` 目录，命中任一即删除并打印一行日志（"清理 T-XXXX-XXX 工作区（依据：已发布）"）：
- 选题状态 = 已发布 / 已淘汰 → 立即清
- 目录 mtime 超 `workspace_ttl_days` → 清
- 删除范围只含 `<编号>/` 子目录；`yt-guanjianci/workspace/频道词库.json` 等根文件永不删
```

- [ ] **步骤 3：改数据契约表**

把 86-89 行四行替换为：

```markdown
| 共享配置 | `~/.config/youtube-skills/config.json`（schema 由 `yt_core.py default_config` 定义；子技能**只读**）。仅三项：`feishu_root_folder_token` / `pool` / `workspace_ttl_days`——无任何本地目录项 |
| 持久层 | 飞书云盘原生 `.md`（`markdown +create/overwrite`）；飞书 `<编号> <标题>/` 文件夹永不删，版本历史 `drive +version-history` |
| 本地工作区 | 各技能内 `<技能>/workspace/<编号>/`，机器流转专用；子技能运行时自清非当前编号目录（当期自清档） |
| 子技能交接 | 上家推飞书 .md → 下家 `markdown +fetch` 拉回消费（含 keywords.json 经 `05-关键词包.md`、manifest 经 `01b-资料清单.md` 中转）；**工作区不跨技能读**；core 不中介产物内容 |
```

- [ ] **步骤 4：改常见错误表**

把 105 行 `| 工作区路径写死在技能文件里 | 一律读共享配置；配置缺失先初始化，不猜默认 |` 替换为：

```markdown
| 把本地路径写进表格字段 | 字段只存飞书 URL 或人读摘要；本地路径机器自己算（编号为主键），写进表是无效信息 |
| 跨技能直接读对方 workspace | 一律经飞书 .md +fetch 中转；工作区不跨技能读 |
```

- [ ] **步骤 5：回归 + Commit**

```bash
cd youtube-skills && python3 -m pytest tests/ -q   # 预期全 PASS
git add youtube-skills/SKILL.md
git commit -m "docs(core): 数据契约改三层模型——飞书md持久层+技能内workspace+清理检查点"
```

---

### 任务 3：yt-ziliao 交付改 .md + manifest 走 01b 中转

**文件：**
- 修改：`yt-ziliao/SKILL.md`（11 行概述、270/310-311 行 doc_folder、步骤8、440/451-458 行 manifest）、`references/write-strategy.md`（全文件改写）、`references/report-template.md`（头部）

- [ ] **步骤 1：概述行**

11 行 `→ 写入飞书文档 → 将文档链接回填到表格「资料采集」列。` → `→ 推飞书 01-资料报告.md（原生 .md，lark-markdown）→ 将文档链接回填到表格「资料采集」列。`

- [ ] **步骤 2：删 doc_folder 问答**

270 行附近 `若 doc_folder 为空且用户拒绝提供，干净退出` 整段与 310-311 行 doc_folder 相关判断删除；初始化保留项：`table_id` / `field_read` / `field_write`。飞书目标文件夹 = core 共享配置 `feishu_root_folder_token` + `<编号> <标题>/`（不存在则由 lark-drive 先建）。

- [ ] **步骤 3：步骤8 飞书文档输出整节替换**

```markdown
### 步骤 8：飞书文档输出

经 `Skill(skill="lark-markdown")` 推送（不直接调 lark-cli）：
- 首次交付：`markdown +create` 推 `01-资料报告.md` 至飞书根下 `<编号> <标题>/` 文件夹
- 修订（核实性重采等）：`markdown +overwrite` 同路径覆盖，URL 不变
- 文件名与文档标题过白名单清洗（write-strategy.md §〇，规则不变）
- 失败重试一次后仍失败 → 写 `runtime/.pending/<topic>.json`，下次触发恢复
```

- [ ] **步骤 4：write-strategy.md 改写**

全文替换为（保留标题清洗节，删除分块/四级降级节——.md 是整文件上传，无 block 写入）：

```markdown
# 文档写入策略

> `yt-ziliao` 不直接调用 `lark-cli`。通过 `Skill(skill="lark-markdown")` 推送原生 `.md`；
> lark-markdown 内部可能使用 `lark-cli`，但对本技能不透明。

## 〇、文件名/标题清洗（create 前必做）

> 2026-09-09 实战踩坑：标题含长破折号（——）+ 编号连撞 400 安全校验。
> 白名单字符集：中文、英文字母、数字、短横线 `-`、下划线 `_`、空格、半角冒号 `:`。
> 规则：`——`/`—`/`–`→`-`；emoji 删除；连续空白→单空格；首尾空白/横线删除。
> 清洗后为空 → 兜底名 `资料报告-<日期>` 并告知用户。

## 一、推送动作

| 场景 | 命令（经 lark-markdown skill） | 说明 |
|---|---|---|
| 首次交付 | `markdown +create --folder-token <飞书<编号> <标题>/token> --name 01-资料报告.md --file <本地report.md>` | 本地稿=技能内 `workspace/<编号>/report.md` |
| 修订 | `markdown +overwrite` 同文件 | URL 不变，表格回填一次终身有效 |

## 二、失败降级

失败重试一次 → 仍失败写 `runtime/.pending/<topic>.json`（含本地稿路径与目标文件夹），下次触发恢复。禁止静默丢稿——本地 workspace 稿永在。
```

- [ ] **步骤 5：manifest 改 01b 中转**

440 行表格末行（manifest 行）中 `落盘路径=core 共享配置 \`dirs.reports\`；缺 manifest → fenxi 降级为"文档 URL 抽取"模式` → `随 \`01b-资料清单.md\` 推飞书（manifest JSON 包在代码块内，fenxi +fetch 提取）；本地存 \`workspace/<编号>/manifest.json\`；缺 manifest → fenxi 降级为"文档 URL 抽取"模式`。

451-456 行 build_manifest 命令块替换为：

```bash
python3 scripts/build_manifest.py <报告.md> --topic-id <编号> \
    --report-url <飞书链接> [--score score输出.json] --out workspace/<编号>/manifest.json
# 随后把 manifest.json 全文包进代码块推飞书 01b-资料清单.md（同 01-资料报告.md 同文件夹）
```

- [ ] **步骤 6：report-template.md 头部加交付行**

首行 `# 资料汇总分析报告模板` 下加：

```markdown
> 交付：本地稿=技能内 `workspace/<编号>/report.md` → `markdown +create` 推飞书 `<编号> <标题>/01-资料报告.md`；URL 回填「资料采集」（空则填不覆盖）。
```

- [ ] **步骤 7：回归 + Commit**

```bash
cd yt-ziliao && python3 -m pytest tests/ -q   # 预期 15/15 PASS
git add yt-ziliao/ && git commit -m "docs(ziliao): 交付改原生md推送——lark-markdown+01b清单中转，删doc_folder问答"
```

---

### 任务 4：yt-fenxi 双写改造

**文件：**
- 修改：`yt-fenxi/SKILL.md`（42 行铁律、99-101 行 init、157-161 行 N9、163-172 行数据契约、179 行依赖表）、`references/analysis-card-template.md`、`references/pool-field-map.md`

- [ ] **步骤 1：铁律 42 行替换**

```markdown
- **分析卡=工作区 md 主档 + 飞书 .md 副本，双写一主一副**（2026-09-10 存储重构）：本地 `workspace/<编号>/analysis-card.md` 是唯一可编辑源（机器下游消费+版本演进）；定稿/修订后 `markdown +overwrite` 推飞书 `<编号> <标题>/02-分析卡.md`（人审入口），URL 回填「分析卡链接」。改卡只改本地再重推，绝不在飞书文档直接改（防两端漂移）。飞书表格除池字段外不另建 docx；资料报告归 yt-ziliao，fenxi 不越权代建。
```

- [ ] **步骤 2：init 删问答 2**

100 行 `2. 分析卡存哪个目录？→ 默认 \`~/Documents/YouTuber工作流/选题分析卡\`，可改` 删除（原 3 顺位前提问 2）。

- [ ] **步骤 3：N9 加分析卡链接回填**

158 行 `**做** → 状态迁 \`阶段三：确认选题\`；回写 \`核心钩子\`、\`目标受众\`（**空则填、不覆盖**）；` 中插入：`` 回写 `核心钩子`、`目标受众`、**`分析卡链接`（飞书文档 URL，空则填）**（**空则填、不覆盖**）；``

161 行输出契约"九字段"改"十字段"，清单末尾 `**消费对账（audit_consumption.py exit 0）**` 前插入 `分析卡链接（N9 回填池字段）、`。

- [ ] **步骤 4：数据契约表更新**

167 行 `36 字段` → `26 字段`（23 现有 + 分析卡链接/发布包装/关键词包 3 新建）。

168-169 行替换为：

```markdown
| 分析卡路径 | 本技能 `workspace/<编号>/analysis-card.md`（主档，唯一可编辑源）；同内容推飞书 `02-分析卡.md`（+overwrite 修订，URL 不变） |
| 淘汰卡归档 | 已淘汰选题的分析卡照常推飞书（飞书不删，KW-06 留痕由持久层承担）；本地按 core 清理检查点③档删除 |
```

数据契约表末加一行：

```markdown
| 机器回读归档卡 | fupan 等低频场景经 `markdown +fetch 02-分析卡.md` 拿回原文，不回捞本地 |
```

- [ ] **步骤 5：消费方式与依赖表**

34 行消费对账铁律中 `yt-ziliao 交付的素材/争议/角度（manifest ID 集合）` 后补一句：`(manifest 经 +fetch \`01b-资料清单.md\` 提取 JSON 落 \`workspace/<编号>/manifest.json\`，再喂 audit_consumption.py)`。

179 行依赖表 `| lark-base | 硬依赖（池读写） |` 后加一行：`| lark-markdown / lark-doc | 硬依赖（交付） | 推 02-分析卡.md（+create/+overwrite），经 Skill() 调用 |`

- [ ] **步骤 6：analysis-card-template.md 头部加交付行**

首行 `# 选题分析卡模板`（或等效标题）下加：

```markdown
> 交付：本地主档 `workspace/<编号>/analysis-card.md`（唯一可编辑源）→ `markdown +create/overwrite` 推飞书 `<编号> <标题>/02-分析卡.md`；N9 将 URL 回填「分析卡链接」（空则填不覆盖）。版本演进只发生本地，飞书为同内容快照。
```

- [ ] **步骤 7：pool-field-map.md 更新**

A 区表格（选题状态行之后）加一行：`| 分析卡链接 | text(url) | N9 回填（空则填）：分析卡飞书文档 URL |`。

"五个拍板决定"第 5 条改为：`5. N9 回填范围 = 状态 + 核心钩子 + 目标受众 + 分析卡链接（**空则填、不覆盖**）`。

文件头 `36 字段` → `26 字段`。

- [ ] **步骤 8：回归 + Commit**

```bash
cd yt-fenxi && python3 -m pytest tests/ -q   # 预期全 PASS（audit_consumption 对账逻辑不动）
git add yt-fenxi/ && git commit -m "docs(fenxi): 分析卡双写改造——工作区主档+飞书md副本+N9回填分析卡链接"
```

---

### 任务 5：yt-jiaoben 交付改 .md + 删脚本字数回填

**文件：**
- 修改：`yt-jiaoben/SKILL.md`（10 行概述、92 行 init、123-129 行阶段6、137 行数据契约）

- [ ] **步骤 1：概述行**

10 行 `交付（A+B 双稿：飞书 doc + 本地存档 + 有限回填）` → `交付（A+B 双稿：推飞书 03-脚本.md + 「选题脚本链接」回填）`

- [ ] **步骤 2：init 92 行**

`config.yaml 缺失 → 从 config.template.yaml 复制，走初始化问答（池 token/存档目录/飞书文件夹/频道阶段）后重跑` → `config.yaml 缺失 → 从 config.template.yaml 复制，走初始化问答（池 token/频道阶段）后重跑；飞书目标文件夹=core 共享配置 feishu_root_folder_token + <编号> <标题>/；本地=本技能 workspace/<编号>/（运行时自清非当前编号目录）`

- [ ] **步骤 3：阶段6 交付四行替换**

126-129 行替换为：

```markdown
- 飞书：`markdown +create` 推 `03-脚本.md`（Part 3a A 稿 + Part 3b B 稿同文档两节，结构见 script-template.md §四）至 `<编号> <标题>/`；文件名过白名单清洗；修订用 `+overwrite`（URL 不变）
- 本地存档：本技能 `workspace/<编号>/script-A.md` 与 `script-B.md`（主档，机器下游消费）
- 回填：「选题脚本链接」= 文档 URL（空则填不覆盖）；状态**不动**
- 汇报：一句话交付摘要 + 预期留存档位 + 待 fupan 校准项
```

- [ ] **步骤 4：数据契约输出/下游行**

137 行输出格 `飞书 doc（含 Part 3a A 稿 + Part 3b B 稿，结构见模板 §四）+ 本地 A/B 双 md 存档 + 脚本字数回填（空则填）` → `飞书 03-脚本.md（Part 3a A 稿 + Part 3b B 稿）+ 本技能 workspace/<编号>/ 本地 A/B 双 md 主档 + 「选题脚本链接」URL 回填（空则填）`

- [ ] **步骤 5：回归（两夹具结论不变）+ Commit**

```bash
cd yt-jiaoben
python3 scripts/scan_script.py tests/fixture-dual-good.md --duration 24   # 预期 exit 0
python3 scripts/scan_script.py tests/fixture-fenced-3track-bad.md --duration 24  # 预期 exit 1
git add yt-jiaoben/ && git commit -m "docs(jiaoben): 交付改03-脚本md推送——删脚本字数回填（字段不存在）"
```

---

### 任务 6：yt-zhizuo 交付改 .md + 输出目录收敛

**文件：**
- 修改：`yt-zhizuo/SKILL.md`（概述10 行、阶段1 的 65/67 行、Step6 的 56 行、阶段4 的 84-87 行）、`references/briefs-template.md`（头部回填行）

- [ ] **步骤 1：概述与阶段1**

10 行 `产出飞书文档并回填选题表链接` → `推飞书 04-制作四件套.md（原生 .md）并回填选题表「制作四件套」`。

65 行 `读 config.yaml（缺失→从 config.template.yaml 复制走初始化问答：池 token/文档文件夹/输出目录）。校验输入：` → `读 config.yaml（缺失→从 config.template.yaml 复制走初始化问答：池 token）。飞书目标文件夹=core 共享配置 feishu_root_folder_token + <编号> <标题>/。运行时先清本技能 workspace 下非当前编号目录。校验输入：`

67 行 `输出目录 = core 共享配置 \`dirs.briefs\`（默认 \`~/Documents/YouTuber工作流/制作四件套/<编号>/\`）` → `输出目录 = 本技能 \`workspace/<编号>/\``

- [ ] **步骤 2：Step6 与阶段4**

56 行 `飞书文档（五节结构）+ 回填「制作四件套」字段 + 本地存档` → `推飞书 04-制作四件套.md（五节结构，markdown +create/overwrite）+ 回填「制作四件套」字段 + workspace 本地存档`。

84-87 行阶段4 前三条替换为：

```markdown
- 本地草稿存本技能 `workspace/<编号>/briefs.md`
- 飞书：`markdown +create` 推 `04-制作四件套.md` 至 `<编号> <标题>/`（文件夹不存在则经 lark-drive 先建）；修订 `+overwrite`，URL 不变
- 回填：选题表「制作四件套」字段=文档 URL（**先 `+field-list` 查字段类型**，text 类型收裸字符串；字段不存在则报人建字段）
```

- [ ] **步骤 3：briefs-template.md 头部**

`> 回填：文档 URL 写入选题表「制作四件套」字段（text 类型，裸字符串）。` 行改为：

```markdown
> 交付：本地稿=本技能 `workspace/<编号>/briefs.md` → `markdown +create/overwrite` 推飞书 `<编号> <标题>/04-制作四件套.md`；回填：文档 URL 写入选题表「制作四件套」字段（text 类型，裸字符串）。
```

- [ ] **步骤 4：回归 + Commit**

```bash
cd yt-zhizuo && python3 -m pytest tests/ -q   # 预期 11/11 PASS
python3 scripts/scan_briefs.py references/briefs-template.md  # 预期 exit 0（模板自扫）
git add yt-zhizuo/ && git commit -m "docs(zhizuo): 交付改04-md推送+输出目录收敛技能内workspace"
```

---

### 任务 7：yt-guanjianci 落盘收敛 + 05 中转 + 字段摘要

**文件：**
- 修改：`yt-guanjianci/SKILL.md`（概述10 行、步骤5 的 60-61 行、数据契约 67-68 行）

- [ ] **步骤 1：概述行**

10 行 `机械闸过检 → 落盘 core 共享工作区 \`关键词库/\` → 消费方各取所需` → `机械闸过检 → 落盘本技能 \`workspace/<编号>/\` + 推飞书 \`05-关键词包.md\` → 消费方各取所需（+fetch 读回）`

- [ ] **步骤 2：步骤5 落盘与累积**

60 行替换为：

```markdown
- 关键词包存本技能 `workspace/<编号>/keywords.json`；同内容推飞书 `05-关键词包.md`（JSON 原文包在代码块内），供下游 `+fetch`
- 频道词库累积更新本技能 `workspace/频道词库.json`（根文件免清，唯一本地持久文件；30 天保鲜由 fupan 触发）
```

61 行 `输出给调用方` 行末加：`；同时向选题表「关键词包」字段写**文字摘要**（多行文本：主关键词/候选标题 3-6 条（带公式编号）/封面词/数据源档位；推荐期换标题后同步更新）`

- [ ] **步骤 3：数据契约表**

`输出路径` 格 `core 共享配置 \`dirs.keywords\`（默认 \`~/Documents/YouTuber工作流/关键词库/\`）` → `本技能 \`workspace/<编号>/\`（JSON 落盘）+ 飞书 \`05-关键词包.md\`（代码块中转）`。

`文件格式` 格后加：`；「关键词包」字段=文字摘要（非 URL）`；并加一行：

```markdown
| 字段摘要格式 | 主关键词（分级）/候选标题 3-6 条带公式编号/封面词 2-4 个/档位标注；空则填不覆盖 |
```

- [ ] **步骤 4：回归 + Commit**

```bash
cd yt-guanjianci && python3 -m pytest tests/ -q   # 预期 15/15 PASS
git add yt-guanjianci/ && git commit -m "docs(guanjianci): 落盘收敛workspace+05-md中转+关键词包字段摘要回填"
```

---

### 任务 8：CHANGELOG 汇总 + 全链路最终回归

**文件：** 六技能 `references/CHANGELOG.md`（各加一条）

- [ ] **步骤 1：六个 CHANGELOG 各加条目**

统一格式（以 ziliao 为例，其余替换技能名与要点）：

```markdown
## v2.8.0（2026-09-10）
- 存储契约重构（规格 docs/superpowers/specs/2026-09-10-storage-workspace-design.md）：交付改原生 .md 上飞书（lark-markdown +create/overwrite）；manifest 经 01b-资料清单.md 中转；删 doc_folder 问答；本地稿落技能内 workspace/<编号>/。方法论文本零改动，扫描闸零改动。
```

（fenxi 要点：分析卡双写一主一副 + N9 回填分析卡链接；jiaoben：03-脚本.md 推送 + 删脚本字数回填；zhizuo：04-制作四件套.md + 输出目录收敛；guanjianci：workspace 落盘 + 05 中转 + 字段摘要；core：配置 schema v2 + 清理检查点。版本号各技能顺延当前版本。）

- [ ] **步骤 2：全链路回归**

```bash
cd youtube-skills && python3 -m pytest tests/ -q      # 全 PASS
cd ../yt-ziliao && python3 -m pytest tests/ -q         # 15/15
cd ../yt-fenxi && python3 -m pytest tests/ -q          # 全 PASS
cd ../yt-jiaoben && python3 scripts/scan_script.py tests/fixture-dual-good.md --duration 24        # exit 0
cd ../yt-jiaoben && python3 scripts/scan_script.py tests/fixture-fenced-3track-bad.md --duration 24 # exit 1
cd ../yt-guanjianci && python3 -m pytest tests/ -q    # 15/15
cd ../yt-zhizuo && python3 -m pytest tests/ -q         # 11/11
cd ../yt-zhizuo && python3 scripts/scan_briefs.py references/briefs-template.md  # exit 0
```

- [ ] **步骤 3：Commit**

```bash
git add */references/CHANGELOG.md
git commit -m "docs(all): 六技能CHANGELOG记录存储重构批次"
```

- [ ] **步骤 4：推送**

```bash
git push origin main
```

---

## 自检记录

1. **规格覆盖度**：规格 §3 交付物矩阵→任务3-7 各交付物；§4 工作区→任务2/5/6/7；§4.2 三档清理→任务2 清理检查点 + 任务3/5/6 的当期自清；§5 逐技能→任务3-7；core 配置收敛→任务1/2；关键词包 05 中转→任务7。规格 §8 迁移脚本与 §5 yt-fabu 新建**不在本计划**（另起计划）。
2. **占位符扫描**：CHANGELOG 步骤中"版本号各技能顺延当前版本"是唯一弹性项——执行时读各技能 CHANGELOG 首行现版本号 +1 即可，非 TODO。
3. **类型一致性**：default_config v2 三键（feishu_root_folder_token/pool/workspace_ttl_days）在任务1 定义、任务2 SKILL.md 引用、清理检查点引用 ttl——一致；`+create/+overwrite/+fetch` 三动作全文一致；01b/05 中转编号一致。
