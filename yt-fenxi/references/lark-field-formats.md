# 飞书字段格式速查（lark-cli 实测踩坑固化）

> 2026-09-09 siwen 实战踩坑预编译：URL 字段结构错一次、缩写 token 错一次。
> 本文件是写池时的格式真源；与 `lark-base-bridge.md` 的读池纪律配套使用。

## 一、铁规（先于一切格式细节）

1. **token/ID 原样全文复制**——从 `config.yaml` 读出的 base_token / table_id 必须一字不差传给命令，
   **禁止任何形式的缩写**（`DvQtb4…dnhc`、`tblqEC…` 这种省略写法在写操作时必出 400）。
   读日志、抄对话时看到的缩写形式一律视为不可用的残片。
2. 来源唯一：token/ID 只从 `config.yaml` 取，不从聊天记录、历史命令里考古。

## 二、字段类型 → 写入格式对照

| 池字段类型 | 写入格式 | 实例 |
|---|---|---|
| text | 纯字符串 | `"核心钩子": "一句钩子"` |
| number | 数字 | `"资料完整度": 80` |
| checkbox | true / false | `"有法律风险": true` |
| select（单选） | 选项名字符串 | `"选题状态": "已淘汰"` |
| select（多选） | 字符串数组 | `"标签": ["🔥热点","系列"]` |
| **URL / 链接类** | **对象，text 键在前 link 键在后** | `"资料采集": {"text": "报告 v3.0", "link": "https://feishu.cn/docx/xxx"}` |

### URL 字段反例（都踩过）

```json
{"资料采集": {"link": "https://..."}}              // ✗ 缺 text，转换失败
{"资料采集": "https://..."}                        // △ 纯字符串有时能过，但丢显示文本，优先用对象
{"资料采集": {"link": "https://...", "text": "…"}} // ✗ 键序虽不影响 JSON，但文档约定 text 在前，照写防呆
```

## 三、状态字段合法值

选题状态只写 config.yaml `state_options` 里的四个值（researching / confirmed / eliminated 及入口态），
其余选项（如"阶段四：内容制作"）只读。选项名以 config 为准，池里改过选项先改 config。

## 四、异常速查

| 症状 | 大概率原因 | 处置 |
|---|---|---|
| 写记录 400 InvalidRequest | URL 字段缺 text 键 / token 缩写 | 按 §二 改对象结构；按 §一 换全文 token |
| 写记录 400 且字段名报错 | 字段名与池不一致（用户改过） | `record-get` 读一条真数据看字段名，或对照 `pool-field-map.md` |
| select 写入后显示空 | 传的选项名不在池选项列表里 | 先 `field-get` 确认选项名逐字一致（含全半角冒号） |
