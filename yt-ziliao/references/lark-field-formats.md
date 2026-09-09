# 飞书字段格式速查（lark-cli 实测踩坑固化）

> 2026-09-09 siwen 实战踩坑预编译：URL 字段连撞两次坑——裸字符串报 URLFieldConvFail、
> `{link, text}` 顺序错乱报 400。本文件是 yt-ziliao 回填「资料采集」字段时的格式真源。

## 一、铁规（先于一切格式细节）

1. **token/ID 原样全文复制**——从 `runtime/config.json` 读出的 base_token / table_id 必须一字不差传给命令，
   **禁止任何形式的缩写**（`DvQtb4…dnhc`、`tblqEC…` 这种省略写法在写操作时必出 400）。
   读日志、抄对话时看到的缩写形式一律视为不可用的残片。
2. 来源唯一：token/ID 只从 `runtime/config.json` 取，不从聊天记录、历史命令里考古。

## 二、字段类型 → 写入格式对照

| 池字段类型 | 写入格式 | 实例 |
|---|---|---|
| text | 纯字符串 | `"选题标题": "萝卜快跑在武汉运营"` |
| URL / 链接类 | **对象，text 键在前 link 键在后** | `"资料采集": {"text": "报告 v3.0", "link": "https://feishu.cn/docx/xxx"}` |

### URL 字段反例（本次实战踩过）

```json
{"资料采集": {"link": "https://..."}}              // ✗ 缺 text，URLFieldConvFail
{"资料采集": "https://..."}                        // ✗ 裸字符串，转换失败
{"资料采集": {"link": "https://...", "text": "…"}} // ✗ 约定 text 在前 link 在后，照写防呆
```

## 三、异常速查

| 症状 | 大概率原因 | 处置 |
|---|---|---|
| 写记录 400 InvalidRequest / URLFieldConvFail | URL 字段缺 text 键或写成裸字符串 | 按 §二 改对象结构，text 在前 |
| 写记录 400 InvalidRequest | token 缩写（`…`省略写法） | 按 §一 从 runtime/config.json 换全文 token |
| 建文档 400 且标题含特殊字符 | 长破折号（——）/emoji 触发安全校验 | 按 write-strategy.md「文档标题白名单」先清洗 |
