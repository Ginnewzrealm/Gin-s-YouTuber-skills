# AgentChat 运维手册（网页 AI 粗采层外部依赖）

> 配套：yt-ziliao `references/网页AI粗采层.md`。AgentChat 安装于 `~/.agents/skills/agentchat/`（软链 `~/.claude/skills/agentchat`）。

## 一、日常启动（专用 Chrome）

```bash
cd ~/.agents/skills/agentchat && ./.venv/bin/python scripts/start-chrome-debug.py
```

- 独立 profile `~/.chrome-debug-profile`，CDP 9222，与 OpenCLI 的 Chrome 互不干扰
- 直连模式（千问/DeepSeek/豆包/Kimi 全国内直连，不走代理；系统分流让 Gemini 等走系统代理）
- 窗口别关；关了就跑上面命令恢复（幂等）

## 二、自检

```bash
node ~/.claude/skills/agentchat/skills/AgentChat-OneWeb/index.js --smoke   # 9家可达性
node ~/.claude/skills/agentchat/skills/AgentChat-OneWeb/index.js --doctor  # CDP 体检
```

轮换池要求 DeepSeek/千问/Kimi 三家 REACHABLE + 已登录。

## 三、已知坑（实战记录）

| 坑 | 解法 |
|---|---|
| `start-chrome-debug.py` 需要 Python ≥3.10 + playwright | 用仓库内 `.venv`（python 3.14），别用系统 python3.9 |
| Cookies <50KB 时 daemon 拒绝启动 | 首次登录前把 `Default/Cookies` 挪走（备份），登录后自然超过 |
| `.env` 里 `PROXY_SERVER` 留空才是直连 | 本仓库已 patch：空值=不传 proxy 参数（原版会报 Invalid URL）|
| 豆包 adapter 漂移（登录页驱动失败） | 待修 `skills/lib/providers/adapters/doubao.js`；前三家够用可缓 |
| 输出带思考 trace / 脚注残留 / 末尾 -1-2-3 | 解析时剔除，见粗采层文档「已知输出噪声」 |
| 图片下载产物 `ai-image-*.png` | 测试后删除，已进 .gitignore |

## 四、登录态维护

- 三家（DeepSeek/千问/Kimi）在专用窗口登录，手机号验证码即可；建议小号
- 登录丢失多见于重启 Chrome 时 Cookie 未落盘——重登一次即可
- 豆包若跳飞书版，说明账号被企业路由，放弃或换号

## 五、provider 频率红线（防封）

单家冷却 ≥60s、时上限 20、日上限 80——粗采层轮换调度自动遵守，手动调用别连刷。

## 六、轮换池真实可用度（2026-09-10 美的空调链路实战确认）

| Provider | 状态 | 备注 |
|---|---|---|
| DeepSeek | ✅ 主力 | 24-27 秒返回，质量稳 |
| 千问 | ✅ 主力 | 14-181 秒，思考过程长但事实准 |
| Kimi | ✅ 主力 | 联网搜索强（50+ 结果），但会下载大量图片产物需清理 |
| MiniMax/MiMo | 🟡 备用 | smoke 通过但未深度使用 |
| **豆包** | ❌ **本次会话adapter修复失败** | 见下方 |

### 豆包修复记录（待下个会话专项处理）

**症状**：adapter 的 `responseSelectors` 用 `[class*="message-list"] [class*="max-w"]`，但 `last()` 抓到了**页面背景其他 `class*="container-`/`max-w-`/`s-font-` 元素**（导航、侧栏、对话框底部智能体图片网格），输出全是图片和导航文字，无实际回复文本。

**实测根因**（CDP 实地探测）：
- "能"字真实所在：`div.container-enLQFx`（20 多层嵌套）
- 路径上有 `DIV.message-list-zLoNs1`
- 但页面背景有同样匹配 `class*="container-` 的元素（首页智能体卡片），`last()` 取错了

**尝试过的修复（全部失败）**：
1. v2：加 `:not([class*="header"])` 等排除 → 输出仍为图片
2. v3：纯 `[class*="content-"]` → 输出仍为图片
3. v4：锚定 `[class*="message-list"] [class*="container-"]` → 输出仍为图片

**真实修复路径（待下个会话）**：
- factory.js 的 `last()` 取最新回复——需加"找新出现的、文本含 prompt 的回复"逻辑（改 factory 是 GitHub 第三方代码，需谨慎）
- 或者在 doubao.js 加 `waitForResponse` 事件钩子（CDP 底层，需 opencli-adapter-author 技能）
- 或者彻底改用"豆包只发链接问题"路线（不指望回复文本，只问返回结构化 URL 的问题）

**当前会话决定**：放弃豆包，三家（DeepSeek/千问/Kimi）已能支撑轮换池。下次会话专门开一个 CDP debug 窗口处理。
