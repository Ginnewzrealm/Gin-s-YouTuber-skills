# 飞书字段格式速查（lark-cli 实测踩坑固化）

> 2026-09-09 siwen 实战踩坑预编译：URL 字段连撞两次坑——裸字符串报 URLFieldConvFail、
> `{link, text}` 顺序错乱报 400。本文件是 yt-ziliao 回填「资料采集」字段时的格式真源。
> 2026-09-09 第二次实战补编：yt-jiaoben 回填「选题脚本链接」报 800010701——
> **字段名带"链接"≠URL 类型**，实测该字段是 text。规则升级为：回填前必须先查字段类型。

## 一、铁规（先于一切格式细节）

1. **token/ID 原样全文复制**——从 `runtime/config.json` 读出的 base_token / table_id 必须一字不差传给命令，
   **禁止任何形式的缩写**（`DvQtb4…dnhc`、`tblqEC…` 这种省略写法在写操作时必出 400）。
   读日志、抄对话时看到的缩写形式一律视为不可用的残片。
2. 来源唯一：token/ID 只从 `runtime/config.json` 取，不从聊天记录、历史命令里考古。
3. **回填任何字段前必须先 `+field-list` 确认真实字段类型**——字段名里带"链接""URL"字样不代表是 URL 类型
   （实测「选题脚本链接」「YouTube URL」在选题池里都是 text）。按字段名猜格式必踩坑。

## 二、字段类型 → 写入格式对照

| 池字段类型 | 写入格式 | 实例 |
|---|---|---|
| text | 纯字符串 | `"选题标题": "萝卜快跑在武汉运营"` |
| text（存 URL） | **仍是纯字符串**，直接写 URL | `"选题脚本链接": "https://feishu.cn/docx/xxx"` |
| **text 字段存 URL**（本池主流） | **纯 URL 字符串**（飞书会自动渲染为 `[title](url)` markdown 链接） | `"资料采集": "https://feishu.cn/docx/xxx"` |
| URL / 链接类（本池暂无） | **对象，text 键在前 link 键在后** | `{"text": "报告 v3.0", "link": "https://feishu.cn/docx/xxx"}` |

### URL 字段反例（本次实战踩过）

```json
// ——— 以下是 URL 字段的常见反例（本池暂无 URL 字段，记录防呆用）———
{"资料采集": {"link": "https://..."}}              // ✗ 缺 text，URLFieldConvFail
{"资料采集": {"link": "https://...", "text": "…"}} // ✗ 约定 text 在前 link 在后，照写防呆
// ——— 以下是 text 字段存 URL 时的反例（"资料采集""选题脚本链接""YouTube URL""竞品参考"都属此类）———
{"选题脚本链接": {"text": "脚本", "link": "https://..."}}  // ✗ text 字段收对象→800010701
{"资料采集": [{"text":"x","link":"y"}]}            // ✗ text 字段收数组→800010701；数组用于 link/user/group 字段（需要 [{id}]）
```

## 三、异常速查

| 症状 | 大概率原因 | 处置 |
|---|---|---|
| 写记录 400 InvalidRequest / URLFieldConvFail | URL 字段缺 text 键或写成裸字符串 | 按 §二 改对象结构，text 在前 |
| 写记录 800010701（field value convert fail） | **给 text 类型字段塞了对象**（如 `{"text","link"}`） | `+field-list` 查真实类型；text 类型写纯字符串 |
| 写记录 400 InvalidRequest | token 缩写（`…`省略写法） | 按 §一 从 runtime/config.json 换全文 token |
| 建文档 400 且标题含特殊字符 | 长破折号（——）/emoji 触发安全校验 | 按 write-strategy.md「文档标题白名单」先清洗 |
