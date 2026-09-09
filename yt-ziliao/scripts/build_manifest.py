#!/usr/bin/env python3
"""build_manifest.py — 从已生成的六章报告解析交接清单 manifest.json（v2.6.0）

用法：
    python3 scripts/build_manifest.py <报告.md> --topic-id T-XXXX-XXX \
        --report-url <飞书链接> [--score score_output.json] [--out manifest.json]

解析来源（全部机械解析已交付报告，不靠对话记忆）：
- §6.1 精选资料表        → materials[]（id/url/标题/类型/权威性/核实状态/立场/摘录）
- §3.5 争议点原料清单     → disputes[]（双方主张+来源+可裁决性）
- §5.1 切入角度盘点       → angles[]（标签/类型/代表内容/URL）
- 附录 A.1-A.3           → audit（rejected/skipped/unselected；缺失则警告不阻断，兼容旧版报告）

优先级：附录审计链 > --score 传入的 audit > 空表+warning。
"""

import argparse
import json
import re
from typing import Any, Optional

SKILL_VERSION = "2.6.0"
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
EMPTY_MARKERS = {"无", "—", "-", "", "无记录"}
HEADER_FIRST_CELLS = {"标题", "维度", "角度", "#", "序号"}


# ---------- 通用表格解析 ----------

def _cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(cells: list) -> bool:
    return all(set(c) <= set("-: ") for c in cells)


def _is_empty_row(cells: list) -> bool:
    return all(c in EMPTY_MARKERS for c in cells)


def _rows_under(text: str, heading_marker: str) -> list:
    """抓取标题行之后的连续表格行（停在空行/新标题处）。"""
    lines = text.splitlines()
    out, cap = [], False
    for ln in lines:
        if cap:
            s = ln.strip()
            if s.startswith("|"):
                cells = _cells(s)
                if not _is_sep(cells):
                    out.append(cells)
                continue
            if s == "" or s.startswith(">"):
                continue  # 标题与表格之间的空行/引用行不中断抓取
            cap = False
        if ln.lstrip().startswith("#") and heading_marker in ln:
            cap = True
    return out


def _strip_link(text: str) -> tuple:
    """[显示](url) → (显示, url)；纯文本 → (原文, '')；裸 URL → (URL, URL)。"""
    m = LINK_RE.search(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    t = text.strip()
    if t.startswith("http"):
        return t, t
    return t, ""


def _first_link(cells: list) -> str:
    for c in cells:
        _, url = _strip_link(c)
        if url:
            return url
    return ""


# ---------- 三个原料解析器 ----------

def parse_materials(text: str) -> list:
    """§6.1 精选资料：| # | URL | 标题 | 类型 | 权威性 | 核实状态 | 立场 | 摘录 |"""
    out = []
    for cells in _rows_under(text, "6.1 精选资料"):
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        _, url = _strip_link(cells[1])
        out.append({
            "id": f"#{cells[0]}",
            "url": url,
            "title": cells[2],
            "type": cells[3],
            "authority": cells[4],
            "verification": cells[5],
            "stance": cells[6],
            "excerpt": cells[7] if len(cells) > 7 else "",
        })
    return out


def parse_disputes(text: str) -> list:
    """§3.5 争议点原料：| # | 争议点 | 甲方主张 | 乙方主张 | 甲方来源 | 乙方来源 | 是否可裁决 |"""
    out = []
    for cells in _rows_under(text, "3.5 争议点原料清单"):
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        _, url_a = _strip_link(cells[4])
        _, url_b = _strip_link(cells[5])
        out.append({
            "id": f"D{cells[0]}",
            "topic_of_dispute": cells[1],
            "claim_a": cells[2],
            "claim_b": cells[3],
            "url_a": url_a,
            "url_b": url_b,
            "resolvable": cells[6],
        })
    return out


def parse_angles(text: str) -> list:
    """§5.1 角度盘点：| 角度 | 类型 | 代表内容 | 关注度 |（链接在角度列或代表内容列均可）"""
    out = []
    for cells in _rows_under(text, "5.1 现有切入角度盘点"):
        if len(cells) < 4 or _is_empty_row(cells) or cells[0] in HEADER_FIRST_CELLS:
            continue
        label, url = _strip_link(cells[0])
        if not url:
            url = _first_link(cells[2:])
        out.append({
            "id": f"A{len(out) + 1}",
            "label": label,
            "type": cells[1],
            "representative": cells[2],
            "url": url,
        })
    return out


def parse_audit_appendix(text: str) -> dict:
    """附录 A.1/A.2/A.3 → audit；缺章进 missing_sections（不阻断，兼容旧报告）。"""
    rejected, skipped, unselected = [], [], []
    for cells in _rows_under(text, "A.1 搜索阶段拒收"):
        if len(cells) >= 3 and not _is_empty_row(cells) and cells[0] not in HEADER_FIRST_CELLS:
            rejected.append({"title": cells[0], "url": cells[1], "reason": cells[2]})
    for cells in _rows_under(text, "A.2 搜索维度跳过"):
        if len(cells) >= 3 and not _is_empty_row(cells) and cells[0] not in HEADER_FIRST_CELLS:
            skipped.append({"dimension": cells[0], "query": cells[1], "reason": cells[2]})
    for cells in _rows_under(text, "A.3 精选阶段落选"):
        if len(cells) >= 3 and not _is_empty_row(cells) and cells[0] not in HEADER_FIRST_CELLS:
            unselected.append({"title": cells[0], "url": cells[1], "reason": cells[2]})
    missing = []
    for key, marker in (("A.1", "A.1 搜索阶段拒收"), ("A.2", "A.2 搜索维度跳过"),
                        ("A.3", "A.3 精选阶段落选")):
        if not _rows_under(text, marker):
            missing.append(key)
    return {"rejected": rejected, "skipped": skipped, "unselected": unselected,
            "missing_sections": missing}


# ---------- 组装 ----------

def build_manifest(report_text: str, completeness: Optional[dict], audit: Optional[dict],
                   topic_id: str, report_url: str) -> dict:
    materials = parse_materials(report_text)
    disputes = parse_disputes(report_text)
    angles = parse_angles(report_text)
    appendix = parse_audit_appendix(report_text)

    warnings = []
    if appendix["missing_sections"]:
        warnings.append(f"appendix_missing:{','.join(appendix['missing_sections'])}")
    if appendix["rejected"] or appendix["skipped"] or appendix["unselected"]:
        audit_out = {k: appendix[k] for k in ("rejected", "skipped", "unselected")}
        audit_out["invalid"] = []
    elif audit:
        audit_out = audit
    else:
        audit_out = {"rejected": [], "skipped": [], "unselected": [], "invalid": []}
        warnings.append("missing_audit:报告无附录审计链且未传 score 输出")

    return {
        "topic_id": topic_id,
        "report_url": report_url,
        "generated_from": "delivered_report_parse",
        "skill_version": SKILL_VERSION,
        "materials": materials,
        "disputes": disputes,
        "angles": angles,
        "audit": audit_out,
        "completeness": completeness or {},
        "counts": {"materials": len(materials), "disputes": len(disputes), "angles": len(angles)},
        "warnings": warnings,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="从六章报告构建 manifest.json")
    ap.add_argument("report", help="报告 markdown 路径")
    ap.add_argument("--topic-id", required=True)
    ap.add_argument("--report-url", required=True)
    ap.add_argument("--score", help="score_materials.py 输出 JSON（补 completeness/audit 用）")
    ap.add_argument("--out", help="manifest 输出路径（缺省只打印）")
    args = ap.parse_args()

    with open(args.report, encoding="utf-8") as f:
        report_text = f.read()

    completeness, audit = None, None
    if args.score:
        with open(args.score, encoding="utf-8") as f:
            score = json.load(f)
        comp = score.get("completeness", {})
        completeness = {"overall": comp.get("overall"), "D7_历史脉络": comp.get("D7_历史脉络")}
        audit = score.get("audit")

    manifest = build_manifest(report_text, completeness, audit, args.topic_id, args.report_url)
    out_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text)
        print(f"manifest 已写入: {args.out}")
    print(out_text)


if __name__ == "__main__":
    main()
