# 文档写入策略

> `yt-ziliao` 不直接调用 `lark-cli`。通过 `Skill(skill="lark-markdown")` 推送原生 `.md`；
> lark-markdown 内部可能使用 `lark-cli`，但对本技能不透明。

---

## 〇、文件名/标题清洗（create 前必做）

> 2026-09-09 实战踩坑：标题含长破折号（——）+ 编号（T-2026-008）连撞 400 安全校验。
> 不清洗不得调用 create。

**白名单字符集**：中文、英文字母、数字、短横线 `-`、下划线 `_`、空格、半角冒号 `:`。

**清洗规则**（按序执行）：

| 原字符 | 替换为 | 例 |
|--------|--------|-----|
| 长破折号 `——` / `—` | `-` | `起火事故——运营公司视角` → `起火事故-运营公司视角` |
| 连接号 `–` / `‐` 等非 ASCII 横线 | `-` | — |
| emoji / 特殊符号 | 删除 | `🔥选题` → `选题` |
| 连续空白 | 单个空格 | — |
| 首尾空白 / 横线 | 删除 | `-标题-` → `标题` |

清洗后标题为空 → 用兜底名 `资料报告-<日期>`，并在交付消息里告知用户原标题被清洗。

---

## 一、推送动作

| 场景 | 动作（经 lark-markdown skill） | 说明 |
|---|---|---|
| 首次交付 | `markdown +create` 推 `01-资料报告.md` | 本地稿=本技能 `workspace/<编号>/report.md`；目标=飞书根下 `<编号> <标题>/`（文件夹不存在则经 lark-drive 先建） |
| 修订 | `markdown +overwrite` 同文件 | URL 不变，表格字段回填一次终身有效 |

原生 `.md` 为整文件上传，**无分块写入**；取消旧 docx 时代的分块策略与四级降级（write→append→table）。

## 二、失败降级

失败重试一次 → 仍失败写 `runtime/.pending/<topic>.json`：

```json
{
  "topic": "选题名称",
  "created_at": "ISO时间",
  "target": { "type": "feishu_md", "folder_token": "..." , "name": "01-资料报告.md"},
  "payload": { "local_file": "workspace/<编号>/report.md" },
  "status": "pending"
}
```

**pending 恢复**：下次触发同一选题时检测 pending 文件，询问用户是否恢复写入。
禁止静默丢稿——本地 workspace 稿永在。

---

## 三、回读校验

`markdown +create` 成功后 `+fetch` 读回，校验六章 H2 标题齐全：事件概述/已确认事实/观点分析/证据与可信度评估/切入视角分析/信息来源总表。

缺失章节补写（最多3次），仍失败则标注。

---

## 四、文档权限与分享

`yt-ziliao` 生成的飞书 .md 默认继承所在文件夹的权限规则。如果目标文件夹是用户私人文件夹，文档可能仅用户自己可访问。

需要明确分享时，由用户在飞书侧手动设置，或通过 `lark-drive` 技能的权限相关命令处理。本技能默认不主动修改文档权限。

---

## 五、失败诊断

写入失败时，在 pending 文件中记录：

```json
{
  "topic": "选题名称",
  "attempted_at": "ISO时间",
  "failure_stage": "markdown_create/overwrite",
  "fallback_action": "pending",
  "content_length": 24237
}
```

详细重试历史（retry_history、error_code 等）由 lark-markdown skill / lark-cli 自动生成，不在 yt-ziliao 层规定。
