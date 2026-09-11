#!/usr/bin/env python3
"""audit_consumption.py — yt-fenxi 消费对账机械闸门（防偷懒/防遗漏）

用法：
    python3 scripts/audit_consumption.py <manifest.json> <分析卡.md>

对账对象（全部来自 yt-ziliao manifest.json，v2.6 交接物）：
- materials[]：每条素材 URL 必须出现在分析卡任意处（引用）或「## 十一、消费对账」节内（销号+原因）
- disputes[]：每个争议点 ID（D1..Dn）必须出现（N5.5 选用/未选去向行均可）
- angles[]：每个角度 ID（A1..An）必须出现（N6 穷举/对照块/对账节均可）

判定：三个集合的"未消费差集"全空 → exit 0；否则 exit 1 并打印差集清单。
机械原则：URL 规范化（去 utm/fragment/尾斜杠、host 小写）后子串匹配；禁止凭印象对账。
"""

import json
import re
import sys
from urllib.parse import urlparse, urlunparse

RECON_SECTION_HEADING = "## 十一、消费对账"
URL_RE = re.compile(r"https?://[^\s)\]\"'<>，。；]+")


def normalize_url(url: str) -> str:
    """去 utm 参数、fragment、尾部斜杠；host 小写——防分享链接差异造成假差集。"""
    try:
        p = urlparse(url.strip())
        query = "&".join(q for q in p.query.split("&") if not q.startswith("utm_"))
        path = p.path.rstrip("/") or "/"
        return urlunparse((p.scheme, p.netloc.lower(), path, "", query, ""))
    except Exception:
        return url.strip().lower()


def _split_reconciliation(card_text: str) -> tuple:
    """拆分正文与消费对账节（对账节内的出现也算销号）。"""
    idx = card_text.find(RECON_SECTION_HEADING)
    if idx < 0:
        return card_text, ""
    return card_text[:idx], card_text[idx:]


def _load_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def audit(manifest: dict, card_path: str) -> dict:
    with open(card_path, encoding="utf-8") as f:
        card = f.read()
    body, recon = _split_reconciliation(card)
    haystack = body + "\n" + recon  # id/URL 出现在全文任一处即算被消费

    # 正文 URLs 提取后逐条规范化：卡片里的链接可能带 utm/尾斜杠，两边规范化再比
    card_urls = {normalize_url(u) for u in URL_RE.findall(haystack)}

    unconsumed_materials = []
    for m in manifest.get("materials", []):
        url = m.get("url", "")
        mid = m.get("id", "")
        if url:
            if normalize_url(url) not in card_urls:
                unconsumed_materials.append({"id": mid, "url": url, "title": m.get("title", "")})
        else:
            # no_url 素材无法按 URL 对账，退化为按 ID 对账——ID 未出现在卡内任意处
            # （正文引用或「消费对账」节销号行）即视为静默丢弃（2026-09-10 实战漏洞：
            # C-13/C-14 缺行但脚本报 19/19 通过，根因即此处只查带 URL 素材）
            if mid and mid not in haystack:
                unconsumed_materials.append({"id": mid, "url": None, "title": m.get("title", "")})

    unconsumed_disputes = [d["id"] for d in manifest.get("disputes", [])
                           if d.get("id") and d["id"] not in haystack]
    unconsumed_angles = [a["id"] for a in manifest.get("angles", [])
                         if a.get("id") and a["id"] not in haystack]

    passed = not unconsumed_materials and not unconsumed_disputes and not unconsumed_angles
    return {
        "topic_id": manifest.get("topic_id", ""),
        "passed": passed,
        "unconsumed_materials": unconsumed_materials,
        "unconsumed_disputes": unconsumed_disputes,
        "unconsumed_angles": unconsumed_angles,
        "stats": {
            "materials_total": len(manifest.get("materials", [])),
            "disputes_total": len(manifest.get("disputes", [])),
            "angles_total": len(manifest.get("angles", [])),
        },
    }


def main_argv(argv: list) -> int:
    if len(argv) < 3:
        print(f"用法: python3 {argv[0]} <manifest.json> <分析卡.md>", file=sys.stderr)
        return 2
    manifest = _load_manifest(argv[1])
    result = audit(manifest, argv[2])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["passed"]:
        print("✅ 消费对账齐：素材/争议/角度零遗漏（或均已销号）")
        return 0
    print(f"❌ 消费对账未过：未消费素材 {len(result['unconsumed_materials'])}、"
          f"争议 {result['unconsumed_disputes']}、角度 {result['unconsumed_angles']}"
          f"——逐条补入正文引用或「{RECON_SECTION_HEADING}」节销号后重跑")
    return 1


def main() -> None:
    sys.exit(main_argv(sys.argv))


if __name__ == "__main__":
    main()
