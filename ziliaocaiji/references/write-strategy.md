# 文档写入策略

> `ziliaocaiji` 不直接调用 `lark-cli`。业务层决定写什么、如何分块、失败如何降级，实际的文档创建与写入通过 `Skill(skill="lark-doc")` 完成。`lark-doc` skill 内部可能使用 `lark-cli` 执行飞书 API 调用，但这由 lark-doc skill 自身管理，不在 ziliaocaiji 层配置。

---

## 一、分块策略

| 内容长度 | 策略 | 说明 |
|---------|------|------|
| < 30KB | 整体写入 | 单次调用 lark-doc 完成完整文档写入 |
| 30-50KB | 按章节分块 | 分 6 次调用，每章一次 |
| > 50KB | 二次切分 | 按章节分块，超长章节再按段落切分 |

分块后记录到 `write_stats.chunk_strategy` 和 `write_stats.chunk_count`。

### 超长段落兜底

如果单个段落仍超过阈值，按以下顺序进一步切分：
1. 句子边界；
2. 表格行边界（针对第六章信息来源总表）；
3. 硬性字符截断（最后兜底）。

切分后的每一块用 append 或 write-block 写入，记录实际切分策略。

---

## 二、四级降级

**业务语义**：写入失败时按顺序尝试备用方案，直到成功或进入 pending 状态。

| 优先级 | 降级路径 | 业务含义 |
|--------|---------|---------|
| 🥇 | 整体写入 | 首选：一次性写入完整报告 |
| 🥈 | 按章节追加 | 备用：分章节写入，应对大文档 |
| 🥉 | Markdown 表格兜底 | 备用：章节追加仍失败时，将报告整理为 Markdown 表格形式尝试写入 |
| 🏅 | pending 状态 | 兜底：所有飞书路径失败时，写入 pending 文件，下次触发恢复 |

**pending 文件**：`runtime/.pending/<topic>.json`

```json
{
  "topic": "选题名称",
  "created_at": "ISO时间",
  "target": { "type": "feishu_doc", "folder_token": "..." },
  "payload": { "content": "完整Markdown正文" },
  "status": "pending"
}
```

**pending 恢复**：下次触发同一选题时，检测 pending 文件，询问用户是否恢复写入。

---

## 三、回读校验

写入后校验内容完整性：

| 路径 | 校验方式 |
|------|---------|
| Markdown 文档 | 检查六章 H2 标题齐全：事件概述/已确认事实/观点分析/证据与可信度评估/切入视角分析/信息来源总表 |
| 表格兜底 | 校验行数 ≥6，且章节号连续 1-6 |
| pending 状态 | 跳过校验，交付消息标注「⚠️ 未写入飞书，无法自动校验」 |

缺失章节补写（最多3次），仍失败则标注。

---

## 四、文档权限与分享

`ziliaocaiji` 生成的飞书文档默认继承所在文件夹的权限规则。如果 `doc_folder` 是用户私人文件夹，文档可能仅用户自己可访问。

需要明确分享时，由用户在飞书侧手动设置，或通过 `lark-doc` 技能的权限相关命令处理。本技能默认不主动修改文档权限。

---

## 五、失败诊断

写入失败时，在进度文件中记录：

```json
{
  "topic": "选题名称",
  "attempted_at": "ISO时间",
  "failure_stage": "write/append/table",
  "fallback_action": "pending",
  "content_length": 24237
}
```

详细重试历史（retry_history、error_code 等）由 lark-doc skill / lark-cli 自动生成，不在 ziliaocaiji 层规定。
