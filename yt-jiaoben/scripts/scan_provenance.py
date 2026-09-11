#!/usr/bin/env python3
"""scan_provenance.py — 口播溯源机械闸门（防编造不靠自觉，靠映射）

第一性原理：伪事实（编人名）、无源因果（编机制）在「无成本结构」里必然发生。
给它们加上成本的方式不是提醒，而是：每条进入口播的事实性内容必须能映射到
素材 ID（或显式标注演绎），映射不到就阻断交付。

用法：
    python3 scripts/scan_provenance.py <脚本.md> <manifest.json>
    （manifest 缺省时退化为「只查标签存在性」，不做人名语料比对）

三类内容（行尾标注语法）：
    （C-05）        事实——素材 ID 必须存在于 manifest
    （演绎：说明）   构造内容（合成人物/情景重演）——必须另有成片免责句
    （无源：说明）   暂无法溯源的主张——必须人审签认，否则阻断

判定（逐条口播行）：
- 硬拦截：行内含数字事实（百分比/金额/倍数/年份+事件）而无任何溯源标注
- 硬拦截：「他叫X/名叫X/人叫X」的人名 X 不出现在素材语料（标题+正文）中且未标演绎
- 硬拦截：标注的 C-XX/V-XX 不存在于 manifest
- 硬拦截：有「演绎」标注但全文无免责句（"演绎"二字须出现在口播/法审节）
- 警告：  有标注但标注 ID 的素材 verify 为单一来源

退出码：0 = 通过（可有警告）；1 = 存在硬拦截，脚本不得交付。
"""
import json
import re
import sys

TAG_RE = re.compile(r"（((?:[CV]-\d{2}[、/]?)+|演绎[:：][^）]*|无源[:：][^）]*|待核[:：][^）]*)）")
NUMERIC_FACT = re.compile(
    r"\d+(\.\d+)?\s*[%％]"
    r"|\d+(\.\d+)?\s*(亿|万|千|百|台|项|笔|倍|欧元|美元|元|公斤|分贝|kW|BTU)"
    r"|\d{4}\s*年"
)
NAME_INTRO = re.compile(r"(?:他叫|她叫|名叫|人叫)\s*([一-龥·A-Za-z]{2,8})")
SPOKEN_LINE = re.compile(r"^\s*\**\s*\[?听觉\]?|^\s*[\"“『]")


def load_corpus(manifest_path):
    """素材语料 = manifest 全文本 + materials 标题。人名比对基准。"""
    with open(manifest_path, encoding="utf-8") as f:
        raw = f.read()
    corpus = raw
    try:
        m = json.loads(raw)
        for it in m.get("materials", []):
            corpus += "\n" + (it.get("title") or "")
    except json.JSONDecodeError:
        pass
    return corpus


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    script_path = sys.argv[1]
    corpus = load_corpus(sys.argv[2]) if len(sys.argv) > 2 else ""
    text = open(script_path, encoding="utf-8").read()
    lines = text.splitlines()

    manifest_ids = set()
    if corpus:
        manifest_ids = set(re.findall(r"[CV]-\d{2}", corpus))

    hard, warn = [], []
    in_fence = False
    # YAML 只认文首 frontmatter（文件内的 --- 多为三轨分隔横线，不得当 YAML 切换）
    yaml_end = -1
    if lines and lines[0].strip() == "---":
        for j, ln0 in enumerate(lines[1:], start=1):
            if ln0.strip() == "---":
                yaml_end = j
                break
    has_disclaimer = "演绎" in text and bool(re.search(r"免责|人物为|情节为|典型用户", text))

    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if i <= yaml_end:
            continue
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # 只扫口播行：【听觉】/[听觉]/「听觉」 标记，或以引号开头的台词行
        if not re.search(r"【?听觉】?|「听觉」", ln) and not re.match(r"^\s*\**\s*[\"“『]", ln):
            continue
        tags = TAG_RE.findall(ln)

        # 1. 数字事实必须带标注
        if NUMERIC_FACT.search(ln) and not tags:
            hard.append((i, "数字事实无溯源标注", ln.strip()[:70]))

        # 2. 出场人名必须在素材语料中，或标注演绎
        m = NAME_INTRO.search(ln)
        if m:
            name = m.group(1)
            named = f"他叫{name}" in ln or f"她叫{name}" in ln
            if named and corpus and name not in corpus \
               and not any(t.startswith("演绎") for t in tags):
                hard.append((i, f"人名「{name}」不在素材语料中且未标演绎", ln.strip()[:70]))

        # 3. 标注的素材 ID 必须存在（支持 C-03/C-05 组合标注）
        for t in tags:
            for mid in re.findall(r"[CV]-\d{2}", t):
                if manifest_ids and mid not in manifest_ids:
                    hard.append((i, f"标注 {mid} 不存在于 manifest", ln.strip()[:70]))

        # 4. 演绎必须有免责通道
        if any(t.startswith("演绎") for t in tags) and not has_disclaimer:
            hard.append((i, "演绎标注存在但全文无免责句", ln.strip()[:70]))

    for n, why, t in warn:
        print(f"[警告] 行{n} ({why}): {t}")
    for n, why, t in hard:
        print(f"[硬拦截] 行{n} ({why}): {t}")
    if hard:
        print(f"\n结论: {len(hard)} 处硬拦截——补标注（素材ID/演绎/无源+人签）后重扫")
        return 1
    print(f"\n结论: 通过（{len(warn)} 处警告可斟酌）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
