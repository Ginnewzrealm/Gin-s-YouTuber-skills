#!/usr/bin/env python3
"""scan_briefs.py — yt-zhizuo 四件套机械扫描闸（防偷工/防断链/防格式漂移）

用法：
    python3 scripts/scan_briefs.py <四件套文档.md>

闸管四件事（缺哪件 exit 1 并打印清单）：
1. 四件齐全：Part 1~Part 5 节头存在
2. 逐镜头有源：Part 2 每行形态合法（露脸/B-Roll/AI）、画面非空、来源非空
3. 时间码连续：Part 2/3/4 行内时间码可解析、段间单调不重叠；
   Part 2 各段时长合计 vs Part 1 声明成片时长 ±10% 容差
4. 混合形态专项：形态=AI 必须带完整生成提示词（可灵/即梦）；
   形态=露脸的画面描述必须含机位/景别标注

机械原则：只认表格与节头，不凭印象；[法审] 标雷计数进 stats 供人审。
"""

import re
import sys
from typing import List, Optional, Tuple

PART_HEADINGS = ["Part 1", "Part 2", "Part 3", "Part 4", "Part 5"]
FORMS = ("露脸", "B-Roll", "AI")
AI_TOOLS = ("可灵", "即梦", "Runway", "Pika")
CAMERA_WORDS = ("机位", "景别", "特写", "近景", "中景", "全景", "远景",
                "固定", "手持", "推镜", "拉镜", "摇镜", "移镜", "无人机")

# MM:SS（容忍全角冒号与 H:MM:SS），匹配段或区间
TC_RE = re.compile(
    r"(\d{1,3})\s*[:：]\s*(\d{2})\s*(?:[-–~～]\s*(\d{1,3})\s*[:：]\s*(\d{2}))?"
)
DURATION_MIN_RE = re.compile(r"成片时长[：:]\s*约?\s*(\d+(?:\.\d+)?)\s*分钟")


def parse_timecode(cell: str) -> Optional[Tuple[int, int]]:
    """从表格单元格解析 (起点秒, 终点秒)；纯时长格（如 90s）返回 None。"""
    m = TC_RE.search(cell.strip())
    if not m:
        return None
    h1, m1, h2, m2 = m.groups()
    start = int(h1) * 60 + int(m1)
    if h2 is None:
        return None  # 只有单点（如纯时间点引用），交给区间行处理
    return (start, int(h2) * 60 + int(m2))


def _split_doc(text: str) -> dict:
    """按 Part 节头切分文档 {part_key: 节内文本}。"""
    parts = {}
    current = None
    for line in text.splitlines():
        head = next((p for p in PART_HEADINGS if line.strip().startswith("## " + p)), None)
        if head:
            current = head
            parts[current] = []
        elif current:
            parts[current].append(line)
    return {k: "\n".join(v) for k, v in parts.items()}


def _is_separator(cells: List[str]) -> bool:
    return all(set(c.strip()) <= set("-: ") and c.strip() for c in cells)


def _looks_like_header(cells: List[str]) -> bool:
    first = cells[0].strip()
    return first in ("段号", "阶段", "#", "序号", "镜头")


def _rows(section_text: str) -> List[List[str]]:
    """抽取节内表格数据行（跳表头与分隔行）。"""
    out = []
    for line in section_text.splitlines():
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if _is_separator(cells) or _looks_like_header(cells):
            continue
        out.append(cells)
    return out


def parse_segments_table(text: str, part: str = "Part 2") -> List[dict]:
    """Part 2 段级分镜表 → [{seg, time, dur, form, visual, source, prompt, continuity}]。"""
    parts = _split_doc(text)
    rows = []
    for cells in _rows(parts.get(part, "")):
        if len(cells) < 6:
            continue
        rows.append({
            "seg": cells[0],
            "time": cells[1],
            "dur": cells[2] if len(cells) > 6 else "",
            "form": cells[3] if len(cells) > 6 else cells[2],
            "visual": cells[4] if len(cells) > 6 else cells[3],
            "source": cells[5] if len(cells) > 6 else cells[4],
            "prompt": cells[6] if len(cells) > 7 else "",
            "continuity": cells[7] if len(cells) > 7 else "",
        })
    return rows


def audit(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = _split_doc(text)
    errors: List[str] = []
    warnings: List[str] = []
    stats = {"segments": 0, "total_seconds": 0, "form_counts": {}, "fash_count": 0,
             "script_minutes": None}

    # 闸1：四件齐全
    for p in PART_HEADINGS:
        if p not in parts:
            errors.append(f"缺少节头 ## {p}（四件套结构不完整）")

    # Part 1 成片时长
    m = DURATION_MIN_RE.search(parts.get("Part 1", ""))
    if m:
        stats["script_minutes"] = float(m.group(1))
    else:
        warnings.append("Part 1 未声明成片时长（时长对账闸跳过）")

    # 闸2+4：Part 2 逐镜头校验
    prev_end = -1
    seg_rows = parse_segments_table(text, "Part 2")
    stats["segments"] = len(seg_rows)
    if not seg_rows and "Part 2" in parts:
        errors.append("Part 2 表格无数据行")

    for r in seg_rows:
        seg = r["seg"]
        form = r["form"].replace(" ", "")
        stats["form_counts"][form] = stats["form_counts"].get(form, 0) + 1

        if not any(f in form for f in FORMS):
            errors.append(f"{seg}：形态「{r['form']}」非法（只认 露脸/B-Roll/AI）")
        if not r["visual"]:
            errors.append(f"{seg}：画面内容为空（逐镜头有源闸）")
        if not r["source"]:
            errors.append(f"{seg}：素材来源为空（逐镜头有源闸）")

        if "AI" in form and not any(t in r["prompt"] for t in AI_TOOLS):
            errors.append(f"{seg}：形态=AI 但生成提示词缺失或不完整（须含工具名+画面描述）")
        if "露脸" in form and not any(w in r["visual"] for w in CAMERA_WORDS):
            errors.append(f"{seg}：形态=露脸但画面描述无机位/景别标注（如 中景/固定机位/特写）")

        tc = parse_timecode(r["time"])
        if tc is None:
            errors.append(f"{seg}：时间码「{r['time']}」不可解析（须 MM:SS-MM:SS）")
        else:
            start, end = tc
            if end <= start:
                errors.append(f"{seg}：时间码终点≤起点「{r['time']}」")
            if start < prev_end:
                errors.append(f"{seg}：段间时间码重叠/回退（起点 {start}s < 上一段终点 {prev_end}s）")
            prev_end = max(prev_end, end)
            stats["total_seconds"] += end - start

        if "[法审]" in (r["visual"] + r["source"]):
            stats["fash_count"] += 1

    # 闸3：Part 3/4 时间码可解析
    for part in ("Part 3", "Part 4"):
        for cells in _rows(parts.get(part, "")):
            tc = parse_timecode(cells[1]) if len(cells) > 1 else None
            if tc is None:
                errors.append(f"{part} 行「{cells[0] if cells else '?'}」：时间码不可解析")

    # 闸3b：总时长对账（±10%）
    if stats["script_minutes"] and stats["total_seconds"]:
        declared = stats["script_minutes"] * 60
        actual = stats["total_seconds"]
        if not (0.9 <= actual / declared <= 1.1):
            errors.append(
                f"时长对账未过：分镜合计 {actual}s vs 成片声明 {int(declared)}s"
                f"（{actual / declared:.0%}，容差 ±10%）")

    return {"passed": not errors, "errors": errors, "warnings": warnings, "stats": stats}


def main_argv(argv: list) -> int:
    if len(argv) < 2:
        print(f"用法: python3 {argv[0]} <四件套文档.md>", file=sys.stderr)
        return 2
    result = audit(argv[1])
    print(f"段数 {result['stats']['segments']}｜合计 {result['stats']['total_seconds']}s｜"
          f"形态分布 {result['stats']['form_counts']}｜法审标雷 {result['stats']['fash_count']} 处")
    for w in result["warnings"]:
        print(f"⚠ {w}")
    if result["passed"]:
        print("✅ 四件套扫描通过：结构齐/有源/时间码连续/形态专项达标")
        return 0
    for e in result["errors"]:
        print(f"❌ {e}")
    print(f"共 {len(result['errors'])} 项未过——修正后重跑")
    return 1


def main() -> None:
    sys.exit(main_argv(sys.argv))


if __name__ == "__main__":
    main()
