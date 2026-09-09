#!/usr/bin/env python3
"""yt_core.py — youtube-skills 总路由核心脚本（薄路由，无业务逻辑）

子命令：
    init      初始化问答：工作区路径（+选题池链接可跳过）→ 落盘共享配置
    route     路由建议：传池状态 → 输出该调用的子技能（纯映射，不读池）
    progress  渲染宏观七阶段仪表盘
    skills    检测 yt-* 子技能安装状态

设计红线（违反即返工）：
- 本脚本不读选题池（读池归 lark-base 桥接，由 Agent 执行后把状态喂进来）
- 本脚本不含任何业务逻辑/凭证；base_token 等定位符只在用户级配置里

状态机语义（路由正确性的根基，改前必读）：
- 「阶段三：确认选题」= 已过 N8 人审、已立项 → 该调 yt-jiaoben（不是 fenxi！fenxi 的活干完才会迁到这个状态）
- 「阶段四：内容制作」= 脚本已交付 → 等人定稿终审（硬闸门③）
- 「制作中」= 已过终审，四件套已交付 → 人做片（此阶段为手动状态，技能不动）
- 「待发布」= 全片完成 → agrici metadata 出上传包（硬闸门④人挑标题）
- 「阶段二：资料研究」= 双义态：资料未就绪 → yt-ziliao；就绪（有链接且完整度≥60）→ yt-fenxi
"""

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Optional

CONFIG_PATH = os.path.expanduser("~/.config/youtube-skills/config.json")

# ---------- 宏观七阶段（硬闸门=状态迁移点上的人审；阶段3无独立池状态，寄生于阶段二就绪态） ----------

PHASES = [
    {"num": 1, "name": "选题立项", "skill": "人（硬闸门①立项）", "gate": "硬闸门①：人立项",
     "states": ["阶段一：想法记录", "想法记录"]},
    {"num": 2, "name": "资料采集", "skill": "yt-ziliao", "gate": None,
     "states": ["阶段二：资料研究"]},
    {"num": 3, "name": "选题分析", "skill": "yt-fenxi", "gate": "硬闸门②：N8 人审拍板",
     "states": [],  # 池内表现为「阶段二：资料研究」就绪态（有链接+完整度≥60）
     "note": "资料就绪后 fenxi 在本阶段工作，N9 过闸才把状态迁到阶段三"},
    {"num": 4, "name": "脚本制作", "skill": "yt-jiaoben", "gate": "硬闸门③：定稿终审",
     "states": ["阶段三：确认选题", "阶段四：内容制作"]},
    {"num": 5, "name": "内容制作", "skill": "yt-zhizuo", "gate": None,
     "states": ["制作中"],
     "note": "人定稿终审过闸后迁「制作中」；yt-zhizuo 出四件套 → 人做片（拍摄/剪辑）"},
    {"num": 6, "name": "发布包装", "skill": "agrici /youtube metadata", "gate": "硬闸门④：人挑标题",
     "states": ["待发布"],
     "note": "人做完全片迁「待发布」；agrici 出上传包（标题变体/描述/标签/章节/缩略图 brief）→ 人上传"},
    {"num": 7, "name": "数据复盘", "skill": "fupan [待开工]（唯一逆流：写回选题池）", "gate": None,
     "states": ["已发布"]},
]

TERMINAL_ELIMINATED = "已淘汰"


def _phase_num_of(state: str) -> int:
    """池状态 → 宏观阶段号（渲染用；阶段三/四都属阶段4，阶段二恒显阶段2）。"""
    if state in ("阶段一：想法记录", "想法记录"):
        return 1
    if state == "阶段二：资料研究":
        return 2
    if state in ("阶段三：确认选题", "阶段四：内容制作"):
        return 4
    if state == "制作中":
        return 5
    if state == "待发布":
        return 6
    if state == "已发布":
        return 7
    return 0


def route_advice(state: str, has_materials: bool, completeness: int) -> dict:
    """池状态 → 路由建议（纯映射函数，可单测）。

    阶段二有分叉：就绪（有链接且完整度≥60）→ yt-fenxi；否则 → yt-ziliao 补采。
    """
    if state == TERMINAL_ELIMINATED:
        return {"state": state, "skill": "终态（仅档案）",
                "next_action": "无下一步；如需重开，人改回阶段一后重新走链"}
    if state == "已发布":
        return {"state": state, "skill": "fupan [待开工]",
                "next_action": "等 fupan 技能建成后接数据复盘；当前人工看 Studio 数据"}
    if state in ("阶段一：想法记录", "想法记录"):
        return {"state": state, "skill": "人（硬闸门①立项）",
                "next_action": "等人立项拍板；立项后状态迁阶段二并调 yt-ziliao"}
    if state == "阶段二：资料研究":
        ready = has_materials and completeness >= 60
        if ready:
            return {"state": state, "skill": "yt-fenxi",
                    "next_action": "资料就绪，调 yt-fenxi 跑 N2→N9（N8 人审=硬闸门②）"}
        return {"state": state, "skill": "yt-ziliao",
                "next_action": "资料未就绪（缺链接或完整度<60），调 yt-ziliao 采集/补采"}
    if state == "阶段三：确认选题":
        return {"state": state, "skill": "yt-jiaoben",
                "next_action": "已过人审（状态即证据），调 yt-jiaoben 输入契约校验→脚本"}
    if state == "阶段四：内容制作":
        return {"state": state, "skill": "人（硬闸门③定稿终审）",
                "next_action": "脚本已交付，等人定稿终审；过闸后迁「制作中」→ yt-zhizuo 出四件套"}
    if state == "制作中":
        return {"state": state, "skill": "yt-zhizuo",
                "next_action": "四件套（配音/分镜/剪辑/配乐 brief）已交付，人做片：拍摄/AI 生成/剪辑/混音；全片完成后迁「待发布」"}
    if state == "待发布":
        return {"state": state, "skill": "agrici /youtube metadata",
                "next_action": "调 agrici metadata 出上传包装包；人挑标题（硬闸门④）后人工上传，传完迁「已发布」"}
    return {"state": state, "skill": "未知（状态未登记）",
            "next_action": "先对照池「选题状态」选项名核对（含制作中/待发布选项），勿硬跑"}


def render_macro(state: str) -> str:
    """宏观七阶段仪表盘（指南 §10.2 格式；core 每轮渲染，子技能不重复宏观）。"""
    if state == TERMINAL_ELIMINATED:
        return "🎬 YouTuber 工作流进度\n\n该选题已淘汰（终态，仅档案）。如需重开：人改回阶段一 → 重新走链。"

    current_num = _phase_num_of(state)
    current_ph = next((p for p in PHASES if p["num"] == current_num), None)
    lines = ["🎬 YouTuber 工作流进度", ""]
    for ph in PHASES:
        if ph["num"] < current_num:
            lines.append(f"阶段 {ph['num']}/7：{ph['name']} [✓]")
        elif ph["num"] == current_num:
            gate = f"　← {ph['gate']}" if ph["gate"] else ""
            lines.append(f"阶段 {ph['num']}/7：{ph['name']}　【当前：池状态={state}】{gate}")
            if ph.get("note"):
                lines.append(f"　ℹ {ph['note']}")
            lines.append(f"　→ 该调：{ph['skill']}")
        else:
            pending = "[待开工]" if ("[待开工]" in ph["skill"] or not ph["states"]) else "[待开始]"
            lines.append(f"阶段 {ph['num']}/7：{ph['name']} {pending}")
    if state == "阶段二：资料研究":
        lines.append("")
        lines.append("ℹ 阶段二为双义态：资料就绪（有链接+完整度≥60）→ 进入阶段3 yt-fenxi；未就绪 → yt-ziliao 补采")
    lines.append("")
    lines.append("硬闸门四处：①立项（阶段一→二）②N8 人审（分析→阶段三）③定稿终审（阶段四→制作中）④挑标题（发布前）——机器不得替人过闸")
    return "\n".join(lines)


# ---------- 工作区共享配置（全系统唯一事实源；子技能只读不写） ----------

def default_config(workspace_root: str = "~/Documents/YouTuber工作流") -> dict:
    root = os.path.expanduser(workspace_root)
    return {
        "version": 1,
        "workspace_root": root,
        "dirs": {
            "reports": "资料报告",     # ziliao 本地报告 + manifest.json 落这里
            "cards": "选题分析卡",      # fenxi 分析卡落这里
            "scripts_out": "脚本",      # jiaoben 脚本工作区
            "briefs": "制作四件套",     # yt-zhizuo 本地存档落这里
        },
        "pool": {"base_token": "", "table_id": "",
                 "note": "选题池定位符；空则路由时现场问用户或读 yt-fenxi config.yaml"},
        "initialized_at": datetime.now(timezone.utc).isoformat(),
    }


def save_config(path: str, cfg: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_config(path: str = CONFIG_PATH) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_dir(cfg: dict, key: str) -> str:
    return os.path.join(cfg["workspace_root"], cfg["dirs"][key])


# ---------- 子技能安装检测 ----------

SKILL_SEARCH_DIRS = ["~/.agents/skills", "~/.claude/skills"]
SUB_SKILLS = ["yt-ziliao", "yt-fenxi", "yt-jiaoben", "yt-zhizuo"]


def detect_skills() -> dict:
    """检测 yt-* 子技能是否已安装（只查 SKILL.md 存在性，不读内容）。"""
    found = {}
    for name in SUB_SKILLS:
        hit = None
        for d in SKILL_SEARCH_DIRS:
            p = os.path.join(os.path.expanduser(d), name, "SKILL.md")
            if os.path.exists(p):
                hit = p
                break
        found[name] = bool(hit)
    return found


# ---------- CLI ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="youtube-skills 总路由核心脚本")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="落盘默认工作区配置（问答由 Agent 完成，脚本只写盘）")
    p_init.add_argument("--workspace", default="~/Documents/YouTuber工作流")
    p_init.add_argument("--base-token", default="")
    p_init.add_argument("--table-id", default="")

    p_route = sub.add_parser("route", help="状态→路由建议（纯映射）")
    p_route.add_argument("--state", required=True)
    p_route.add_argument("--has-materials", action="store_true")
    p_route.add_argument("--completeness", type=int, default=0)

    p_prog = sub.add_parser("progress", help="渲染宏观仪表盘")
    p_prog.add_argument("--state", required=True)

    sub.add_parser("skills", help="子技能安装检测")

    args = ap.parse_args()

    if args.cmd == "init":
        cfg = default_config(args.workspace)
        cfg["pool"]["base_token"] = args.base_token
        cfg["pool"]["table_id"] = args.table_id
        save_config(CONFIG_PATH, cfg)
        print(json.dumps({"config_path": CONFIG_PATH, "config": cfg}, ensure_ascii=False, indent=2))
    elif args.cmd == "route":
        print(json.dumps(route_advice(args.state, args.has_materials, args.completeness),
                         ensure_ascii=False, indent=2))
    elif args.cmd == "progress":
        print(render_macro(args.state))
    elif args.cmd == "skills":
        print(json.dumps(detect_skills(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
