#!/usr/bin/env python3
"""keyword_brief.py — yt-guanjianci 关键词+标题库机械闸

用法：
    python3 scripts/keyword_brief.py <关键词包.json>

闸管三件事：
1. 输入校验：词根非空；schema 字段齐（主关键词须含 词/分级）
2. 标题矩阵机械规范：每条 8-35 字 / 禁逗号句号叹号 / 无占位符（[XX]、XX、待填）
3. 数据源档位标注：A=DataForSEO 精确值 / B=Google Trends 相对指数 / C=手工定性档

机械原则：只认 JSON 字段，不凭印象；档位决定月搜索量字段是否允许为空。
"""

import json
import re
import sys
from typing import List

GRADES = ("A", "B", "C")
GRADE_NOTES = {
    "A": "DataForSEO/付费 API 精确月搜索量",
    "B": "Google Trends(gprop:youtube) 0-100 相对指数，需对标基准词换算量级",
    "C": "手工竞品扫描+定性标注（无绝对量；分级靠经验判断，须人复核）",
}

TITLE_LEN = (8, 35)
BANNED_PUNCT = (",", "，", "。", "!", "！", ";", "；")
PLACEHOLDER_RE = re.compile(r"(\[.*?\])|(XX+)|(待填)|(TODO)", re.IGNORECASE)

# ---- 封面词规范（来源：商业故事封面词提炼 SOP，2026-09 归档）----
COVER_MAX_HANZI = 6          # 封面字 ≤6 汉字（数字/字母不占额）
CJK_RE = re.compile(r"[一-鿿]")
COVER_BANNED = (             # 三不选：过程/背景 + 中性专业术语
    "经过", "长期", "调查", "背景", "历程", "发展",
    "供应链", "资产负债", "毛利率", "营收", "整合", "同比", "环比",
)
COVER_PREDICATES = ("了", "的", "是", "在", "和", "与")  # 谓语连接词=句子嫌疑


def cover_word_ok(word: str) -> bool:
    """封面词机械规范：≤6 汉字 / 三不选（过程词·中性术语·完整句）。"""
    t = (word or "").strip()
    if not t:
        return False
    hanzi = len(CJK_RE.findall(t))
    if hanzi == 0 or hanzi > COVER_MAX_HANZI:
        return False
    if any(b in t for b in COVER_BANNED):
        return False
    if hanzi >= 5 and any(p in t for p in COVER_PREDICATES):
        return False  # 长且带谓语=完整句子
    return True


def title_ok(title: str) -> bool:
    """单条标题机械规范：长度 8-35 字 / 禁标点 / 无占位符。问号冒号放行（经验值研究支持）。"""
    t = title.strip()
    n = len(t)
    if not (TITLE_LEN[0] <= n <= TITLE_LEN[1]):
        return False
    if any(p in t for p in BANNED_PUNCT):
        return False
    if PLACEHOLDER_RE.search(t):
        return False
    return True


def validate_pack(pack: dict) -> dict:
    errors: List[str] = []
    warnings: List[str] = []
    stats = {"titles": 0, "grade": pack.get("数据源档位", ""), "cover_words": 0}

    # 闸1：词根非空
    if not pack.get("词根"):
        errors.append("词根为空（须给定实体/选题词根）")

    # 闸2：档位合法 + 搜索量字段按档位校验
    grade = pack.get("数据源档位", "")
    if grade not in GRADES:
        errors.append(f"数据源档位「{grade}」非法（只认 A/B/C：{'; '.join(GRADES)}）")
    else:
        main = pack.get("主关键词") or {}
        if not main.get("词"):
            errors.append("主关键词.词 为空")
        if not main.get("分级"):
            errors.append("主关键词.分级 为空（须按四级标准：大词/中词/小词/微长尾）")
        if grade == "A" and main.get("月搜索量") in (None, ""):
            errors.append("档位=A 必须提供精确月搜索量")
        if grade in ("B", "C") and main.get("月搜索量") in (None, ""):
            warnings.append(f"档位={grade} 无绝对搜索量（{GRADE_NOTES[grade]}）")

    for field in ("次级关键词", "长尾词"):
        if field not in pack:
            errors.append(f"缺字段 {field}")

    # 闸3：标题矩阵
    matrix = pack.get("标题矩阵", [])
    stats["titles"] = len(matrix)
    if not matrix:
        warnings.append("标题矩阵为空（仅出关键词包，未产标题）")
    for i, t in enumerate(matrix, 1):
        cand = t.get("候选", "")
        label = cand or f"第{i}条(无候选字段)"
        if not cand:
            errors.append(f"标题矩阵第{i}条缺「候选」字段")
            continue
        if not title_ok(cand):
            errors.append(
                f"标题「{cand[:20]}…」未过机械规范（8-35字/禁逗句号叹号/无占位符）")
        if t.get("适用阶段") not in ("冷启动", "推荐期", "通用"):
            warnings.append(f"标题「{cand[:12]}…」适用阶段未标注（建议 冷启动/推荐期/通用）")

    # 闸4：封面词（单独可输出的封面字）
    covers = pack.get("封面词", [])
    stats["cover_words"] = len(covers)
    if not covers:
        warnings.append("封面词为空（封面字无产出，缩略图叠字无原料）")
    for w in covers:
        if not cover_word_ok(w):
            errors.append(f"封面词「{w}」未过规范（≤{COVER_MAX_HANZI}汉字/三不选：过程词·中性术语·完整句）")

    return {"passed": not errors, "errors": errors, "warnings": warnings, "stats": stats}


def main_argv(argv: list) -> int:
    if len(argv) < 2:
        print(f"用法: python3 {argv[0]} <关键词包.json>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        pack = json.load(f)
    r = validate_pack(pack)
    print(f"词根 {pack.get('词根','?')}｜档位 {r['stats']['grade']}｜标题 {r['stats']['titles']} 条｜封面词 {r['stats']['cover_words']} 个")
    for w in r["warnings"]:
        print(f"⚠ {w}")
    if r["passed"]:
        print("✅ 关键词包扫描通过：schema 齐/标题规范/档位标注")
        return 0
    for e in r["errors"]:
        print(f"❌ {e}")
    print(f"共 {len(r['errors'])} 项未过——修正后重跑")
    return 1


def main() -> None:
    sys.exit(main_argv(sys.argv))


if __name__ == "__main__":
    main()
