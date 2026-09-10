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
