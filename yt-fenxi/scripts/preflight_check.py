#!/usr/bin/env python3
"""yt-fenxi 环境自检（N0）。

每次技能触发时静默执行；全部通过只输出一行"环境就绪"。
发现问题输出结构化报告（阻断 / 降级 / 提示），由主技能决定处置。

用法: preflight_check.py [--verbose] [--config <路径>]
退出码: 0 = 全通过 | 1 = 有阻断项（须先走初始化问答） | 2 = 仅降级/提示项

输出 JSON 到 stdout:
{
  "verdict": "ok" | "blocked" | "degraded",
  "checks": [
    {"name": "config", "level": "block", "ok": false, "detail": "config.yaml 缺失", "fix": "走初始化问答生成配置"},
    {"name": "lark-base", "level": "degrade", "ok": true, ...},
    ...
  ]
}
"""
import json
import os
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(SKILL_DIR, "config.yaml")

CHECKS = []


def check(name, level, ok, detail, fix=""):
    CHECKS.append({"name": name, "level": level, "ok": bool(ok), "detail": detail, "fix": fix})


def file_check():
    if not os.path.exists(CONFIG_PATH):
        check("config", "block", False, "config.yaml 缺失", "走初始化问答生成配置（主技能负责问答后重新自检）")
        return None
    cfg = {}
    try:
        text = open(CONFIG_PATH, encoding="utf-8").read()
    except OSError as e:
        check("config", "block", False, f"config.yaml 读取失败: {e}", "检查文件权限或重建配置")
        return None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            cfg[k.strip()] = v.strip().strip('"').strip("'")
        elif ":" in line and line.startswith("  "):
            k, _, v = line.partition(":")
            parent = raw[: len(raw) - len(raw.lstrip())]  # noqa: F841 —— 简化解析，嵌套仅一层
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    pool_token = cfg.get("base_token") or cfg.get("pool_base_token", "")
    pool_table = cfg.get("table_id") or cfg.get("pool_table_id", "")
    missing = []
    if not pool_token:
        missing.append("base_token")
    if not pool_table:
        missing.append("table_id")
    if missing:
        check("config", "block", False, f"config.yaml 缺少必填项: {', '.join(missing)}", "补齐后重新自检")
    else:
        check("config", "block", True, "base_token + table_id 已配置")
    return cfg


def cli_check(name, cmd_probe, level, degrade_detail, degrade_fix):
    """通用 CLI 依赖探测：只看能否调用 --help，不深测业务。"""
    try:
        r = subprocess.run(cmd_probe, capture_output=True, timeout=15)
        check(name, level, r.returncode == 0, f"{name} CLI 可用" if r.returncode == 0 else degrade_detail, "" if r.returncode == 0 else degrade_fix)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        check(name, level, False, f"{name} 不可用: {e}", degrade_fix)


def api_key_check():
    """YouTube Data API key 可用性：只查是否配置了 key，不做网络探测。"""
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if key:
        check("youtube-api-key", "degrade", True, "YOUTUBE_API_KEY 已配置（重档可用）")
    else:
        check("youtube-api-key", "degrade", False, "未配置 YOUTUBE_API_KEY", "自动降级轻档（WebSearch 定性档），或配置后享受重档精算")


def output_dir_check(cfg):
    # 2026-09-10 存储重构：分析卡=技能内 workspace/<编号>/，不再用 config.yaml output_dir。
    # 此检查保留为 always-ok 的桩（兼容未来再次启用时）
    check("output-dir", "block", True, "分析卡=技能内 workspace/<编号>/（v2.8.0 重构后无独立配置）")


def main():
    verbose = "--verbose" in sys.argv
    cfg = file_check()
    if cfg is None or not any(c["name"] == "config" and c["ok"] for c in CHECKS):
        verdict = "blocked"
    else:
        cli_check("lark-cli", ["lark-cli", "--help"], "degrade",
                  "lark-cli 不可用，飞书池读写失效", "降级备用通道：用户粘贴选题行；迁移输出待迁移清单")
        cli_check("yt-ziliao", ["lark-cli", "base", "--help"], "degrade",
                  "yt-ziliao 不可用，资料补采失效", "资料缺失时本次分析终止，提示先安装/补采")
        api_key_check()
        output_dir_check(cfg)
        blocked = any(c["level"] == "block" and not c["ok"] for c in CHECKS)
        degraded = any(c["level"] == "degrade" and not c["ok"] for c in CHECKS)
        verdict = "blocked" if blocked else ("degraded" if degraded else "ok")

    result = {"verdict": verdict, "checks": CHECKS}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if verbose or verdict != "ok":
        for c in CHECKS:
            mark = "✓" if c["ok"] else ("⛔" if c["level"] == "block" else "⚠️")
            print(f"{mark} {c['name']}: {c['detail']}" + (f" → {c['fix']}" if c["fix"] else ""), file=sys.stderr)
    sys.exit(1 if verdict == "blocked" else 0)


if __name__ == "__main__":
    main()
