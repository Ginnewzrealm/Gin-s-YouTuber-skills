#!/usr/bin/env python3
"""脚本硬指标扫描器（机械防线）。

按 references/good-script-definition.md 的 A1-A6 前置指标做机械计数。
防"脚本看着行但指标不过"不靠自觉，靠机器拦截；本脚本是交付闸门。

用法: scan_script.py <脚本.md> [--duration 25] [--keywords "词1,词2,词3"]
  --duration: 预估时长（分钟），缺省时从元数据头解析，都没有则跳过 WPM 检查
退出码: 0 = 通过（可有警告）; 1 = 存在硬拦截，脚本不得交付。

规则:
- 硬拦截: 离场词 / 伪现场感 / 主观语言 / 未公开信息 / 全场零凭证
- 警告: 单句超字 / WPM 越界 / 拍点密度不足 / 视听比越界 / 抽象形容词 / SEO 词缺失
- 豁免: 元数据头（--- 包裹）、``` 围栏代码块、以 # 开头的行
"""
import argparse
import re
import sys

LEAVING = re.compile(r"以上就是|感谢收看|感谢观看|喜欢请点赞|点赞关注|我们下期再见|下期再会|欢迎在评论区")
FAKE_SCENE = re.compile(r"某个(会议室|雨夜|深夜|清晨|午后)|雨夜|心里默默|独自走在|霓虹灯映|空气(仿佛|突然)凝固")
SUBJECTIVE = re.compile(r"我认为|我觉得|在我看来|依我看|大家都知道|所有人都认为|没人能否认|毫无疑问")
ABSOLUTE = re.compile(r"永远|绝对|必然|所有人|每个人|从未")
UNPUBLIC = re.compile(r"内部人士|知情人士|私下透露|非公开|会议纪要流出|据未经证实")
ABSTRACT_ADJ = re.compile(r"非常(愤怒|激动|紧张|开心|高兴)|气氛(很|突然|十分)|一脸茫然|十分(诡异|震惊)")
CREDENTIAL = re.compile(r"\[凭证|凭证\s*\d|来源[:：]")

def is_exempt(ln):
    s = ln.strip()
    return s.startswith("#") or s.startswith("```") or not s

def load_script(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    out, in_fence, in_yaml = [], False, False
    for ln in lines:
        if ln.strip() == "---":
            in_yaml = not in_yaml
            continue
        if in_yaml:
            continue
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or is_exempt(ln):
            continue
        out.append(ln)
    return out

def parse_meta(lines):
    dur, kws = None, []
    for ln in lines[:20]:
        m = re.search(r"(\d+)\s*[-~至到]\s*(\d+)\s*分钟", ln)
        if m and dur is None:
            dur = (int(m.group(1)) + int(m.group(2))) / 2
        m = re.search(r"核心关键词[^：:]*[：:]\s*(.+)", ln)
        if m:
            kws = [k.strip() for k in re.split(r"[,，、/]", m.group(1)) if k.strip()]
    return dur, kws

def split_sentences(text):
    return [s for s in re.split(r"[。！？!?；;]", text) if s.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--keywords", default=None)
    a = ap.parse_args()

    lines = load_script(a.script)
    body = "\n".join(lines)
    dur, meta_kws = parse_meta(lines)
    if a.duration:
        dur = a.duration
    kws = [k.strip() for k in a.keywords.split(",")] if a.keywords else meta_kws

    hard, warn = [], []
    def h(msg): hard.append(msg)
    def w(msg): warn.append(msg)

    # ---- 硬拦截黑名单 ----
    for name, pat in [("离场词", LEAVING), ("伪现场感", FAKE_SCENE),
                      ("主观语言", SUBJECTIVE), ("未公开信息", UNPUBLIC)]:
        hits = sorted(set(pat.findall(body)))
        if hits:
            h(f"{name}: 命中 {hits}")

    # ---- 绝对化（警告，语境误判率高）----
    hits = sorted(set(ABSOLUTE.findall(body)))
    if hits:
        w(f"绝对化表述: {hits}（HR-3，建议加时空限定）")

    # ---- 抽象形容词 ----
    hits = sorted(set(ABSTRACT_ADJ.findall(body)))
    if hits:
        w(f"抽象形容词: {hits}（A5，改为客观动作描述）")

    # ---- 凭证 ----
    n_cred = len(CREDENTIAL.findall(body))
    n_visual = len(re.findall(r"【视觉】|\*\*画面", body))
    if n_cred == 0:
        h("全场零凭证标记（HR-5：每个画面必须有 [凭证 N]）")
    elif n_visual > 0 and n_cred < n_visual / 2:
        w(f"凭证偏少: 视觉段 {n_visual} 处 vs 凭证 {n_cred} 处（HR-5）")

    # ---- 单句长度（口播行）----
    over20, over35 = 0, 0
    for ln in lines:
        if "【台词】" in ln or "[台词]" in ln or "口播" in ln:
            text = re.sub(r"[\"'「『\"」』]", "", ln.split("：", 1)[-1])
            for s in split_sentences(text):
                n = len(re.sub(r"\s", "", s))
                if n > 35: over35 += 1
                elif n > 20: over20 += 1
    if over35:
        h(f"超长句 {over35} 处（单句 >35 字，A4 严禁长难句）")
    if over20:
        w(f"超字句 {over20} 处（单句 21-35 字，A4 上限 20 字）")

    # ---- WPM / 拍点密度 / 视听比 ----
    spoken = 0
    for ln in lines:
        if "【听觉】" in ln or "[台词]" in ln or "口播" in ln:
            spoken += len(re.sub(r"\s", "", ln))
    if dur:
        wpm = spoken / dur
        if not 260 <= wpm <= 320:
            w(f"WPM {wpm:.0f} 越界（合格 260-320，锚定 280；口播 {spoken} 字 / {dur} 分钟）")
        pi = len(re.findall(r"【拍点】|拍点打断|rehook|Rehook|REHOOK", body))
        if pi / dur < 2:
            w(f"拍点密度 {pi/dur:.1f}/分钟（A3 合格 ≥2/分钟）")
    visuals = len(re.findall(r"【视觉】", body))
    if visuals and spoken:
        ratio = spoken / visuals
        if not 9 <= ratio <= 14:
            w(f"视听比 1:{ratio:.0f}（A2 合格 1:9 至 1:14；台词 {spoken} 字 / 视觉段 {visuals} 处）")

    # ---- SEO 关键词 ----
    for k in kws:
        c = body.count(k)
        need = int(dur / 1.0) if dur else 0  # 每 50 秒 ≥1 次 ≈ 每分钟 ≥1 次
        if c < max(1, need // 2):
            w(f"SEO 词「{k}」出现 {c} 次（目标约 {need} 次/全片）")

    for t in warn:
        print(f"[警告] {t}  <- 建议修复")
    for t in hard:
        print(f"[硬拦截] {t}  <- 退回重写")
    if hard:
        print(f"\n结论: {len(hard)} 处硬拦截，脚本不得交付")
        sys.exit(1)
    print(f"\n结论: 通过（{len(warn)} 处警告可斟酌）")
    sys.exit(0)

if __name__ == "__main__":
    main()
