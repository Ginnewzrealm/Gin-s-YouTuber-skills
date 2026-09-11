#!/usr/bin/env python3
"""close_obligations.py — 义务队列销号闸门（防契约静默丢弃）

第一性原理：义务=内容+归属者+终态，缺一则义务不存在。散文里的"建议下游补 X"
没有归属者也没有终态，必然蒸发（2026-09-10 实战：V-01/V-02 补 BV 号被三处文档
传递、零处执行）。本脚本把义务变成 manifest 内结构化数据，用退出码强制销号。

两种模式：

  # 1. init：从 manifest materials 生成 pending_obligations 并写回 manifest
  python3 scripts/close_obligations.py --init <manifest.json>

  # 2. gate（默认）：检查 --stage 名下义务的销号状态
  python3 scripts/close_obligations.py <manifest.json> --stage yt-jiaoben \
      [--resolutions workspace/<编号>/obligations.json] [--doc <交付物.md>]

销号三终态（resolutions 文件格式）：
  {"OBL-01": {"status": "resolved",   "evidence": "BV号已落 B-Roll 表 BR-14"},   # 完成
   "OBL-02": {"status": "escalated",  "evidence": "B站搜索API不可用，请人审补"}  # 移交人审
   "OBL-03": {"status": "waived",     "evidence": "人审批准放弃（必填理由）"}}
第四种状态（消失）不允许：未登记即未销号。

闸门规则：
  - blocking 义务未销号（resolved/escalated 均可，waived 仅限 blocking=false）→ exit 1
  - escalated 义务必须给出 evidence，且 --doc 提供时其 ID 必须出现在交付物内（防口头移交）
  - 非本 stage 的义务不检查
"""
import argparse
import json
import os
import sys

TERMINAL = {"resolved", "escalated", "waived"}


def gen_obligations(manifest: dict) -> list:
    """视频线索无直链 → jiaoben 阻塞；其余 no_url → fenxi 非阻塞。"""
    obligations, n = [], 0
    for m in manifest.get("materials", []):
        mid = m.get("id", "")
        mtype = m.get("type", "")
        is_video = mid.startswith("V-") or any(k in mtype for k in ("电视", "纪录片", "视频"))
        if is_video and not m.get("url"):
            n += 1
            obligations.append({
                "id": f"OBL-{n:02d}",
                "task": f"补 {mid}《{m.get('title', '')}》播放页直链（B站BV号/官网URL），落入 B-Roll 表",
                "owner_stage": "yt-jiaoben",
                "blocking": True,
                "source": f"video_clue_no_url:{mid}",
            })
        elif not m.get("url"):
            n += 1
            obligations.append({
                "id": f"OBL-{n:02d}",
                "task": f"补 {mid} 的可追溯 URL，或在分析卡注明多源印证依据",
                "owner_stage": "yt-fenxi",
                "blocking": False,
                "source": f"no_url_material:{mid}",
            })
    return obligations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--init", action="store_true", help="生成义务队列并写回 manifest")
    ap.add_argument("--stage", default=os.path.basename(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), help="当前技能名（默认从脚本位置推断）")
    ap.add_argument("--resolutions", help="销号登记文件（obligations.json）")
    ap.add_argument("--doc", help="交付物路径（escalated 义务须出现在其中）")
    a = ap.parse_args()

    manifest = json.load(open(a.manifest, encoding="utf-8"))

    if a.init:
        manifest["pending_obligations"] = gen_obligations(manifest)
        with open(a.manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"义务队列已生成：{len(manifest['pending_obligations'])} 条 → 写回 {a.manifest}")
        for o in manifest["pending_obligations"]:
            print(f"  {o['id']} [{'阻塞' if o['blocking'] else '非阻塞'}] → {o['owner_stage']}: {o['task']}")
        return 0

    owned = [o for o in manifest.get("pending_obligations", [])
             if o.get("owner_stage") == a.stage]
    if not owned:
        print(f"✅ {a.stage} 名下无义务队列")
        return 0

    resolutions = {}
    if a.resolutions and os.path.exists(a.resolutions):
        resolutions = json.load(open(a.resolutions, encoding="utf-8"))

    doc_text = ""
    if a.doc and os.path.exists(a.doc):
        doc_text = open(a.doc, encoding="utf-8").read()

    hard, done = [], []
    for o in owned:
        r = resolutions.get(o["id"])
        if not r or r.get("status") not in TERMINAL:
            hard.append((o, "未登记销号（消失=第四种状态，不允许）"))
            continue
        if not r.get("evidence"):
            hard.append((o, f"status={r['status']} 但无 evidence——终态必须留痕"))
            continue
        if o["blocking"] and r["status"] == "waived":
            hard.append((o, "阻塞义务不允许 waived——只能 resolved 或 escalated"))
            continue
        if r["status"] == "escalated" and a.doc and o["id"] not in doc_text:
            hard.append((o, "escalated 但义务 ID 未出现在交付物内——口头移交=未移交"))
            continue
        done.append((o, r["status"]))

    for o, st in done:
        print(f"  ✅ {o['id']} ({st}): {o['task']}")
    for o, why in hard:
        print(f"  ❌ {o['id']} [{'阻塞' if o['blocking'] else '非阻塞'}] {why}: {o['task']}")

    if hard:
        print(f"\n结论: {len(hard)}/{len(owned)} 条义务未销号——登记到 {a.resolutions or 'obligations.json'} 后重跑")
        return 1
    print(f"\n结论: {len(owned)} 条义务全部销号")
    return 0


if __name__ == "__main__":
    sys.exit(main())
