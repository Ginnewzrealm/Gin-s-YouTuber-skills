#!/usr/bin/env python3
"""
score_materials.py — ziliaocaiji 资料评分与精选脚本

输入：整理后的素材 JSON（见下方 schema）
输出：完整度评分、可信度分布、精选建议。当总素材 <10 条且未通过严格约束时，
`selection.conditional_pass` 标记放宽约束后的状态，由调用方决定是否继续。

用法：
    python3 scripts/score_materials.py <materials.json>

输入 schema（materials.json）：
{
  "topic": "选题名称",
  "items": [
    {
      "title": "...",
      "url": "https://...",
      "platform": "weibo",
      "language": "zh",
      "publish_date": "2024-07-15",
      "type": "新闻报道",
      "authority": "高",
      "verification": "多方证实",
      "stance": "中立"
    }
  ]
}
"""

import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# 权威性分值
AUTHORITY_SCORE = {"高": 100, "中": 70, "低": 40}
# 核实状态分值
VERIFICATION_SCORE = {"多方证实": 100, "单一来源": 60, "存疑待核实": 30, "存疑": 30}
# 立场集合
STANCES = {"支持方", "质疑方", "中立"}
# 平台类型映射（用于 D1 平台覆盖）
PLATFORM_CATEGORIES = {
    "微博": "social",
    "知乎": "qa",
    "百度": "search",
    "36氪": "news",
    "贴吧": "forum",
    "豆瓣": "forum",
    "BBC": "news",
    "NYT": "news",
    "Reddit": "forum",
    "Hacker News": "forum",
    "Medium": "blog",
    "arXiv": "academic",
    "Google Scholar": "academic",
    "政府公告": "official",
    "公司官网": "official",
    "B站": "video",
    "YouTube": "video",
    "公众号": "social",
    "抖音": "video",
    "行业报告": "report",
}


def load_materials(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def credibility_score(item: dict) -> float:
    """单条素材可信度分 = 权威性×40% + 核实状态×40% + 新鲜度×20%"""
    authority = AUTHORITY_SCORE.get(item.get("authority", "中"), 70)
    verification = VERIFICATION_SCORE.get(item.get("verification", "单一来源"), 60)

    pub_date_str = item.get("publish_date")
    if pub_date_str:
        try:
            pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days = (now - pub_date).days
        except Exception:
            days = 999
    else:
        days = 999

    if days <= 7:
        freshness = 100
    elif days <= 30:
        freshness = 80
    elif days <= 90:
        freshness = 60
    else:
        freshness = 40

    return authority * 0.4 + verification * 0.4 + freshness * 0.2


def compute_d1_platform_coverage(items: list[dict]) -> float:
    """D1 平台覆盖 = 有素材的平台类型数 ÷ 5 × 100"""
    categories = set()
    for item in items:
        platform = item.get("platform", "")
        cat = PLATFORM_CATEGORIES.get(platform, "other")
        categories.add(cat)
    return min(len(categories) / 5 * 100, 100)


def compute_d2_language_coverage(items: list[dict]) -> float:
    """D2 语言覆盖 = min(zh%, en%) - |zh%-en%|×0.3"""
    if not items:
        return 0.0
    total = len(items)
    zh = sum(1 for i in items if i.get("language", "") == "zh") / total
    en = sum(1 for i in items if i.get("language", "") == "en") / total
    return max(0, min(zh, en) - abs(zh - en) * 0.3) * 100


def compute_d3_source_type(items: list[dict]) -> float:
    """D3 来源类型 = 不同类型数 ÷ 3 × 100"""
    types = {i.get("type", "其他") for i in items}
    return min(len(types) / 3 * 100, 100)


def compute_d4_stance_coverage(items: list[dict]) -> float:
    """D4 立场覆盖 = min(支持, 质疑, 中立) ÷ 5 × 100"""
    stance_counts = Counter(i.get("stance", "中立") for i in items if i.get("stance") in STANCES)
    if len(stance_counts) < 3:
        return 0.0
    return min(stance_counts.values()) / 5 * 100


def compute_d5_time_distribution(items: list[dict]) -> float:
    """D5 时间分布 = 熵/最大熵 × 100（分布越均匀得分越高）"""
    months = []
    for item in items:
        pub_date_str = item.get("publish_date")
        if not pub_date_str:
            continue
        try:
            dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            months.append(dt.strftime("%Y-%m"))
        except Exception:
            continue
    if not months:
        return 0.0
    counts = Counter(months)
    total = len(months)
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    max_entropy = math.log2(max(len(counts), 2))
    return max(0, (entropy / max_entropy) * 100)


def compute_d6_url_coverage(items: list[dict]) -> float:
    """D6 URL 覆盖率 = 有URL的信源数 ÷ 总数 × 100"""
    if not items:
        return 0.0
    has_url = sum(1 for i in items if i.get("url"))
    return has_url / len(items) * 100


# D7 历史脉络标记：命中任一即视为"含历史沿革信息"
HISTORY_MARKERS = re.compile(
    r"成立|创办|创立|诞生于|起源于|前身|收购|合并|注资|融资|上市|退市|更名|"
    r"升级|升格|改制|破产|清算|重启|复出|回归|冠名|签约|首[届场]|"
    r"发展史|编年史|十[周年]|周年|[35]0年|历任|创始人|元老|股权|注册资本"
)


def compute_d7_history_coverage(items: list[dict]) -> float:
    """D7 历史脉络覆盖度 = 标题/摘要命中历史节点词的素材数 ÷ 总数 × 100。

    历史节点词覆盖：成立/收购/升级/合作/事故/融资/人事变动/冠名等。
    非历史类选题（如纯产品测评）天然偏低，由阈值兜底，不强制满分。
    """
    if not items:
        return 0.0
    hits = 0
    for i in items:
        text = (i.get("title") or "") + " " + (i.get("summary") or i.get("excerpt") or "")
        if HISTORY_MARKERS.search(text):
            hits += 1
    return hits / len(items) * 100


def completeness_score(items: list[dict]) -> dict[str, Any]:
    d1 = compute_d1_platform_coverage(items)
    d2 = compute_d2_language_coverage(items)
    d3 = compute_d3_source_type(items)
    d4 = compute_d4_stance_coverage(items)
    d5 = compute_d5_time_distribution(items)
    d6 = compute_d6_url_coverage(items)
    d7 = compute_d7_history_coverage(items)
    overall = (d1 + d2 + d3 + d4 + d5 + d6 + d7) / 7
    return {
        "D1_平台覆盖": round(d1, 1),
        "D2_语言覆盖": round(d2, 1),
        "D3_来源类型": round(d3, 1),
        "D4_立场覆盖": round(d4, 1),
        "D5_时间分布": round(d5, 1),
        "D6_URL覆盖率": round(d6, 1),
        "D7_历史脉络": round(d7, 1),
        "overall": round(overall, 1),
        "passed": overall >= 80 and d6 >= 95,
    }


def select_items(items: list[dict]) -> dict[str, Any]:
    """
    精选 30-80 条，满足分布约束：
    - 高权威+多方证实 ≥30%
    - 中权威+单一来源 ≤40%
    - 低权威+单一来源 ≤15%
    - 低权威+存疑 ≤5%
    - 平均可信度分 ≥70
    """
    scored = [(item, credibility_score(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)

    selected = []
    counts = defaultdict(int)

    for item, score in scored:
        authority = item.get("authority", "中")
        verification = item.get("verification", "单一来源")
        category = f"{authority}_{verification}"

        # 分布约束实时检查
        total = len(selected) + 1
        high_multi = counts["高_多方证实"] + (1 if category == "高_多方证实" else 0)
        medium_single = counts["中_单一来源"] + (1 if category == "中_单一来源" else 0)
        low_single = counts["低_单一来源"] + (1 if category == "低_单一来源" else 0)
        low_doubt = counts["低_存疑待核实"] + counts["低_存疑"] + (1 if category in ("低_存疑待核实", "低_存疑") else 0)

        # 约束条件（前 30 条优先放宽，保证至少有内容）
        if len(selected) >= 30:
            if high_multi / total < 0.30:
                if category != "高_多方证实":
                    continue
            if medium_single / total > 0.40:
                if category == "中_单一来源":
                    continue
            if low_single / total > 0.15:
                if category == "低_单一来源":
                    continue
            if low_doubt / total > 0.05:
                if category in ("低_存疑待核实", "低_存疑"):
                    continue

        selected.append((item, score))
        counts[category] += 1

        if len(selected) >= 80:
            break

    # 兜底：如果不足 30 条，全部纳入
    if len(selected) < 30 and len(items) > len(selected):
        existing_urls = {i.get("url") for i, _ in selected}
        for item, score in scored:
            if item.get("url") not in existing_urls:
                selected.append((item, score))
            if len(selected) >= 30:
                break

    avg_score = sum(s for _, s in selected) / len(selected) if selected else 0

    distribution = {
        "高权威_多方证实": counts["高_多方证实"] / len(selected) if selected else 0,
        "中权威_单一来源": counts["中_单一来源"] / len(selected) if selected else 0,
        "低权威_单一来源": counts["低_单一来源"] / len(selected) if selected else 0,
        "低权威_存疑": (counts["低_存疑待核实"] + counts["低_存疑"]) / len(selected) if selected else 0,
    }

    passed = (
        30 <= len(selected) <= 80
        and avg_score >= 70
        and distribution["高权威_多方证实"] >= 0.30
        and distribution["中权威_单一来源"] <= 0.40
        and distribution["低权威_单一来源"] <= 0.15
        and distribution["低权威_存疑"] <= 0.05
    )

    # 冷门领域兜底：素材极少时给出 conditional_pass，由调用方决定是否继续
    conditional_pass = False
    if not passed:
        if len(items) < 10:
            conditional_pass = (
                avg_score >= 60
                and distribution["高权威_多方证实"] >= 0.20
                and distribution["中权威_单一来源"] <= 0.50
                and distribution["低权威_单一来源"] <= 0.25
                and distribution["低权威_存疑"] <= 0.10
            )
        if len(items) < 5:
            conditional_pass = (
                avg_score >= 50
                and distribution["高权威_多方证实"] >= 0.10
                and distribution["中权威_单一来源"] <= 0.60
                and distribution["低权威_单一来源"] <= 0.40
                and distribution["低权威_存疑"] <= 0.20
            )

    return {
        "selected_count": len(selected),
        "avg_credibility": round(avg_score, 1),
        "distribution": {k: round(v, 2) for k, v in distribution.items()},
        "passed": passed,
        "conditional_pass": conditional_pass,
        "selected": [
            {
                "title": i.get("title", ""),
                "url": i.get("url", ""),
                "credibility": round(s, 1),
            }
            for i, s in selected
        ],
    }


def generate_suggestions(completeness: dict, selection: dict) -> list[str]:
    suggestions = []
    if not completeness["passed"]:
        if completeness["D6_URL覆盖率"] < 95:
            suggestions.append("D6 URL 覆盖率不足 95%，直接降级 pending，不补搜")
        if completeness["D1_平台覆盖"] < 60:
            suggestions.append("D1 平台覆盖不足，补搜缺失平台类型")
        if completeness["D2_语言覆盖"] < 60:
            suggestions.append("D2 语言覆盖不足，补搜中英文薄弱侧")
        if completeness["D3_来源类型"] < 60:
            suggestions.append("D3 来源类型不足，补搜官方/学术/视频来源")
        if completeness["D4_立场覆盖"] < 60:
            suggestions.append("D4 立场覆盖不足，补搜支持方/质疑方/中立观点")
        if completeness["D5_时间分布"] < 60:
            suggestions.append("D5 时间分布不均，补搜早期/近期/中间时段素材")
        if completeness["D7_历史脉络"] < 40:
            suggestions.append("D7 历史脉络覆盖不足，补搜主体沿革词（成立/收购/升格/冠名/创始人等），见 search-strategy.md §二")
    if not selection["passed"]:
        if selection["avg_credibility"] < 70:
            suggestions.append(f"精选素材平均可信度 {selection['avg_credibility']}，低于 70，建议提高信源质量")
        if selection["distribution"].get("高权威_多方证实", 0) < 0.30:
            suggestions.append("高权威+多方证实素材占比不足 30%，建议补充")
    return suggestions


def main():
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <materials.json>", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    data = load_materials(input_path)
    items = data.get("items", [])

    if not items:
        print(json.dumps({"error": "无素材"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    completeness = completeness_score(items)
    selection = select_items(items)
    suggestions = generate_suggestions(completeness, selection)

    result = {
        "topic": data.get("topic", ""),
        "input_count": len(items),
        "completeness": completeness,
        "selection": selection,
        "suggestions": suggestions,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
