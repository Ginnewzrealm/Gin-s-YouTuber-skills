#!/usr/bin/env python3
"""
score_materials.py — yt-ziliao 资料评分与精选脚本

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
  ],
  "rejected": [                        # 可选：搜索/合并阶段拒收来源（审计链，不许静默丢弃）
    {"title": "...", "url": "https://...", "reason": "拒收原因必填（内容农场/与#N重复/无关/源头不明）"}
  ],
  "skipped": [                         # 可选：搜索维度显式跳过记录
    {"dimension": "抖音", "query": "尝试的查询词", "reason": "跳过原因必填"}
  ]
}

输出在 v2.5.0 起含 audit 块：
{
  "audit": {
    "rejected_count": N,               # 透传输入 rejected（reason 缺失进 invalid）
    "skipped_count": M,                # 透传输入 skipped（reason 缺失进 invalid）
    "invalid": [{"index", "kind", ...}],
    "unselected": [{"title", "url", "reason"}]   # 精选阶段落选条目，逐条带理由，零静默丢弃
  }
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
# 立场别名归一：materials 里常见"质疑方(财经作家反思视角)"这类带括注的值，
# 前缀匹配即可归类（v2.9.1 修复 D4=0 的真正根因：带括注值被 STANCES 精确匹配丢弃）
def normalize_stance(value: str) -> str:
    v = (value or "").strip()
    for s in STANCES:
        if v.startswith(s):
            return s
    return "中立"

# 语言别名归一（v2.9.1）："中文/汉语/Chinese"→zh，"英文/英语/English"→en
LANGUAGE_ALIASES = {
    "zh": "zh", "中文": "zh", "汉语": "zh", "chinese": "zh", "zh-cn": "zh", "zh-tw": "zh", "繁体": "zh",
    "en": "en", "英文": "en", "英语": "en", "english": "en",
}
def normalize_language(value: str) -> str:
    return LANGUAGE_ALIASES.get((value or "").strip().lower(), (value or "").strip().lower())

# 平台类型映射（用于 D1 平台覆盖）
PLATFORM_CATEGORIES = {
    "微博": "social", "weibo": "social",
    "知乎": "qa", "zhihu": "qa",
    "百度": "search", "baidu": "search",
    "36氪": "news", "36kr": "news",
    "贴吧": "forum", "豆瓣": "forum",
    "BBC": "news", "NYT": "news", "Reddit": "forum", "Hacker News": "forum",
    "Medium": "blog", "arXiv": "academic", "Google Scholar": "academic",
    "政府公告": "official", "公司官网": "official",
    "B站": "video", "bilibili": "video", "哔哩哔哩": "video",
    "YouTube": "video", "youtube": "video",
    "公众号": "social", "抖音": "video", "douyin": "video",
    "行业报告": "report",
}
# 平台兜底：URL 域名启发（v2.9.1）：platform 字段不在表内时按 URL 归类
PLATFORM_DOMAIN_HINTS = [
    ("bilibili.com", "video"), ("youtube.com", "video"), ("youtu.be", "video"),
    ("weibo.com", "social"), ("zhihu.com", "qa"), ("twitter.com", "social"),
    ("x.com", "social"), ("reddit.com", "forum"), ("medium.com", "blog"),
    ("arxiv.org", "academic"), ("scholar.google", "academic"),
    ("gov.cn", "official"), ("gov.", "official"),
    ("people.com.cn", "news"), ("news.cn", "news"), ("xinhuanet.com", "news"),
    ("caixin.com", "news"), ("eeo.com.cn", "news"), ("gmw.cn", "news"),
    ("sina.com.cn", "news"), ("sohu.com", "news"), ("qq.com", "news"),
    ("163.com", "news"), ("ifeng.com", "news"), ("ce.cn", "news"),
]
def platform_category(item: dict) -> str:
    platform = (item.get("platform") or "").strip()
    if platform in PLATFORM_CATEGORIES:
        return PLATFORM_CATEGORIES[platform]
    url = (item.get("url") or "").lower()
    for domain, cat in PLATFORM_DOMAIN_HINTS:
        if domain in url:
            return cat
    return "other"


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
    """D1 平台覆盖 = 有素材的平台类型数 ÷ 5 × 100（含 platform 别名与 URL 域名兜底）"""
    categories = set()
    for item in items:
        categories.add(platform_category(item))
    return min(len(categories) / 5 * 100, 100)


def compute_d2_language_coverage(items: list[dict]) -> float:
    """D2 语言覆盖（v2.9.1 修正）：先归一语言别名，再按"主语言基础分 + 次语言加成"计。

    旧公式 min(zh,en)-|zh-en|*0.3 对中文母语选题（天然 zh 占绝对多数）恒判 0 分，
    与"语言覆盖"的语义不符。新公式：主语言占比≥60% 得 60 基础分（保证单语选题不冤死），
    次语言占比×100 为加成，封顶 100——鼓励双语但仍给纯中文选题合理分。
    """
    if not items:
        return 0.0
    total = len(items)
    counts = Counter(normalize_language(i.get("language", "")) for i in items)
    counts.pop("", None)
    if not counts:
        return 0.0
    top, second = counts.most_common(2)[0][1] / total, (counts.most_common(2)[1][1] / total if len(counts) > 1 else 0)
    base = 60 if top >= 0.6 else top * 100
    return min(base + second * 100, 100)


def compute_d3_source_type(items: list[dict]) -> float:
    """D3 来源类型 = 不同类型数 ÷ 3 × 100"""
    types = {i.get("type", "其他") for i in items}
    return min(len(types) / 3 * 100, 100)


def compute_d4_stance_coverage(items: list[dict]) -> float:
    """D4 立场覆盖 = min(支持, 质疑, 中立) ÷ 5 × 100（stance 经前缀归一，带括注值不再被丢弃）"""
    stance_counts = Counter(normalize_stance(i.get("stance", "中立")) for i in items)
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


def audit_summary(data: dict[str, Any]) -> dict[str, Any]:
    """审计链校验：rejected/skipped 透传并校验 reason 必填（缺失进 invalid）。

    v2.5.0 铁规：收录要记录，拒绝也要记录——判断可追溯，不许静默丢弃。
    """
    rejected = data.get("rejected", []) or []
    skipped = data.get("skipped", []) or []
    invalid = []
    for i, r in enumerate(rejected):
        if not r.get("reason"):
            invalid.append({"index": i, "kind": "rejected", "title": r.get("title", "")})
    for i, s in enumerate(skipped):
        if not s.get("reason"):
            label = s.get("dimension") or s.get("platform") or ""
            invalid.append({"index": i, "kind": "skipped", "dimension": label})
    return {
        "rejected_count": len(rejected),
        "skipped_count": len(skipped),
        "invalid": invalid,
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
    skip_records: dict[str, str] = {}  # url -> 落选理由（审计链）

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
                    skip_records[item.get("url", "")] = (
                        "分布约束：高权威+多方证实占比不足 30%，本条暂缓（补搜同类后可入选）"
                    )
                    continue
            if medium_single / total > 0.40:
                if category == "中_单一来源":
                    skip_records[item.get("url", "")] = "分布约束：中权威+单一来源占比超 40%，本条暂缓"
                    continue
            if low_single / total > 0.15:
                if category == "低_单一来源":
                    skip_records[item.get("url", "")] = "分布约束：低权威+单一来源占比超 15%，本条暂缓"
                    continue
            if low_doubt / total > 0.05:
                if category in ("低_存疑待核实", "低_存疑"):
                    skip_records[item.get("url", "")] = "分布约束：低权威+存疑占比超 5%，本条暂缓"
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
                skip_records.pop(item.get("url", ""), None)  # 兜底纳入，撤销落选记录
            if len(selected) >= 30:
                break

    # 审计链：落选的每条必有理由（约束暂缓 / 80 条上限截断），零静默丢弃
    selected_urls = {i.get("url") for i, _ in selected}
    unselected = [
        {
            "title": i.get("title", ""),
            "url": i.get("url", ""),
            "reason": skip_records.get(
                i.get("url", ""),
                "精选上限 80 条截断（按可信度分排序，本条排在入选线之后）",
            ),
        }
        for i in items
        if i.get("url") not in selected_urls
    ]

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
        "unselected": unselected,
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


def main_argv(argv: list[str]) -> None:
    if len(argv) < 2:
        print(f"用法: python3 {argv[0]} <materials.json>", file=sys.stderr)
        sys.exit(1)

    input_path = argv[1]
    data = load_materials(input_path)
    items = data.get("items", [])

    if not items:
        print(json.dumps({"error": "无素材"}, ensure_ascii=False, indent=2))
        sys.exit(1)

    completeness = completeness_score(items)
    selection = select_items(items)
    suggestions = generate_suggestions(completeness, selection)
    audit = audit_summary(data)
    audit["unselected"] = selection.get("unselected", [])

    result = {
        "topic": data.get("topic", ""),
        "input_count": len(items),
        "completeness": completeness,
        "selection": selection,
        "audit": audit,
        "suggestions": suggestions,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    main_argv(sys.argv)


if __name__ == "__main__":
    main()
