# OpenCLI 平台命令映射

> 本文件供 `scripts/opencli_adapter.py` 参考，不直接写入 SKILL.md。
> yt-ziliao 中大部分平台没有 OpenCLI 适配器，优先使用 WebSearch/WebFetch；本文件只列出可能通过 OpenCLI 增强的平台。

---

## 平台映射

| 技能内名称 | OpenCLI 适配器 | 策略 | 常用命令 | 备注 |
|---|---|---|---|---|
| 知乎 | `zhihu` | cookie | `zhihu search <keyword>` | 需登录 |
| 微博 | `weibo` | cookie | `weibo search <keyword>` / `weibo feed` | 需登录 |
| B站 / 哔哩哔哩 | `bilibili` | cookie | `bilibili search <keyword>` | 可直接使用 |
| YouTube | `youtube` | cookie | `youtube search <keyword>` | 需登录 |
| Reddit | `reddit` | cookie | `reddit search <keyword>` | 需登录 |

---

## 无 OpenCLI 适配器的平台

以下平台在 yt-ziliao 的搜索分工中出现，但当前没有可靠 OpenCLI 适配器，直接走 WebSearch/WebFetch：

- 百度、36氪、贴吧、豆瓣
- BBC、NYT、Medium
- 政府公告、行业报告
- arXiv、Google Scholar

未来如果 OpenCLI 新增对应适配器，只需在本表添加映射，并在 `scripts/opencli_adapter.py` 的 `PLATFORM_ALIASES` 和 `SEARCH_COMMANDS` 中补充即可。

---

## 命令发现

不要硬编码适配器列表。运行时通过 `opencli list -f json` 动态发现当前可用的适配器和命令。

---

## 登录状态检测

cookie 策略平台可通过 `opencli <site> whoami` 检测登录状态：

- 成功：用户已登录
- 失败：用户未登录，该平台的 OpenCLI 采集将失败，自动降级 WebSearch/WebFetch

---

## 返回字段差异

不同平台返回的字段不同，统一抽取以下字段：

- `title` / `name` / `question` / `topic` / `text` → 标题
- `url` / `link` / `href` / `share_url` → 链接
- `summary` / `description` / `content` / `excerpt` / `snippet` → 摘要
- `published_at` / `publish_time` / `created_at` / `time` / `date` → 发布时间

无法识别时保留原始 `raw` 字段。

---

## 浏览器兜底

当站点适配器不存在或失败时，使用通用浏览器命令（均通过 `scripts/opencli_adapter.py` 封装）：

```bash
opencli browser yt-ziliao open <url> --window background
opencli browser yt-ziliao extract
opencli browser yt-ziliao tab close <page_targetId>
```

> `browser open` 返回 JSON 包含 `page`（targetId），提取后必须调用 `browser tab close <page>` 关闭该标签。`--keep-tab false` 仅适用于站点适配器命令，不适用于 `browser` 子命令。

---

## 输出字段对齐

`scripts/opencli_adapter.py` 会将 OpenCLI 返回数据标准化为 `scripts/score_materials.py` 可消费的字段：

| 字段 | 来源/默认值 | 说明 |
|------|------------|------|
| `title` | OpenCLI 返回的 title/name/question/topic/text | 必填 |
| `url` | OpenCLI 返回的 url/link/href/share_url | 可能为空 |
| `platform` | 调用方传入的平台名 | 必填 |
| `language` | OpenCLI 返回的 language 或根据 platform 推断 | 中文平台默认 zh，英文平台默认 en |
| `publish_date` | OpenCLI 返回的 published_at/publish_time/created_at/time/date | 可能为空 |
| `type` | OpenCLI 返回的 type 或根据 platform 推断 | 知乎/微博/视频/论坛等 |
| `authority` | OpenCLI 返回的 authority 或默认 "中" | 主流程可覆盖 |
| `verification` | OpenCLI 返回的 verification 或默认 "单一来源" | 主流程可覆盖 |
| `stance` | OpenCLI 返回的 stance 或默认 "中立" | 主流程可覆盖 |
| `source` | 固定 "opencli" | 用于追溯 |
| `raw` | OpenCLI 原始返回项 | 保留原始数据 |

---

## 更新说明

OpenCLI 的适配器和命令会不断演进。新增平台时，只需：

1. 在本文件中添加映射
2. 在 `scripts/opencli_adapter.py` 的 `PLATFORM_ALIASES` 中添加别名
3. 在 `scripts/opencli_adapter.py` 的 `SEARCH_COMMANDS` 中添加候选命令

无需修改 SKILL.md。
