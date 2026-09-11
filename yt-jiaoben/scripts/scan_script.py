#!/usr/bin/env python3
"""脚本硬指标扫描器（机械防线）。

按 references/good-script-definition.md 的 A1-A6 前置指标 + v0.4 故事层规则做机械计数。
防"脚本看着行但指标不过"不靠自觉，靠机器拦截；本脚本是交付闸门。

用法: scan_script.py <交付物.md> [--duration 25] [--keywords "词1,词2,词3"]
  --duration: 预估时长（分钟），缺省时从元数据头解析，都没有则跳过 WPM/开场闸检查
退出码: 0 = 通过（可有警告）; 1 = 存在硬拦截，脚本不得交付。

规则:
- 硬拦截: 离场词 / 伪现场感 / 主观语言 / 未公开信息 / 全场零凭证 / 超长句 >35 字
  / 开场3分钟财报术语（A稿区）/ B稿区全片零 [观点] 标记
- 警告: 超字句 21-35 字 / WPM 越界 / 拍点密度不足 / 字每切越界 / 抽象形容词 / SEO 词缺失
  / A稿零黑体金句 / B稿 [内容层] 覆盖率不足 / 单源事实无限定词 / 英文人名未标注中文译名
- A/B 分区: 按 Part 3a/A稿/纯口播 与 Part 3b/B稿/三轨 标题切分；无标题时按是否含 【听觉】 判为 B 或 A
- 三轨格式识别（2026-09-09 实战修复）:
  * 三轨正文常整体包在 ``` 围栏里——围栏**内容照常扫描**，只跳围栏标记行本身
  * 听觉块 = 【听觉】行 + 后续以引号开头的续行（一段台词跨多行），到下一个 【 轨标记为止
  * 口播字数只统计引号内内容（【听觉】[台词]："..."），不算轨道标记和停顿符号
  * 视觉切换数按 【视觉】行内 画面描述 的 →、+、、 拆分估算
- 豁免: 元数据头（--- 包裹）、# 标题行、| 表格行（自检报告元信息，防"引用违禁词做说明"误杀）
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
QUOTE = re.compile(r'["“『「](.*?)["”』」]', re.S)
CUT_SEP = re.compile(r"[→+、]")
# v0.4 故事层：开场 3 分钟禁财报术语（HR/指南 Part 四-1）
STORY_FINANCE = re.compile(
    r"\d{6}\s*\.?\s*(SH|SZ|sh|sz)|商誉|股权占比|营收占比|持股比例|净利润|财报|估值|市占率")
# 英文人名（两名连写，首字母大写）；URL 先剥掉防误报
LATIN_NAME = re.compile(r"(?<![A-Za-z])([A-Z][a-z]{1,15} [A-Z][a-z]{1,15})(?![A-Za-z])")
URL_STRIP = re.compile(r"https?://\S+")

def load_script(path):
    """读取脚本，返回 (扫描行列表, 全文本)。围栏内容保留，只跳过标记行。
    YAML 只认文首 frontmatter——文件内的 --- 是分隔横线（2026-09-10 实战：
    三轨格式的 --- 横线被当成 YAML 切换，整段内容被静默跳过）。"""
    lines = open(path, encoding="utf-8").read().splitlines()
    yaml_end = -1
    if lines and lines[0].strip() == "---":
        for j, ln in enumerate(lines[1:], start=1):
            if ln.strip() == "---":
                yaml_end = j
                break
    scan, body_lines = [], []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if i <= yaml_end:
            continue
        if s.startswith("```"):
            continue  # 围栏标记行跳过；围栏内的三轨正文必须参与扫描
        if not s or s.startswith("|"):
            continue
        scan.append(ln)            # 标题保留——split_ab 靠它切 A/B 区（2026-09-10 修复：
        if not s.startswith("#"):  # 原实现在这里丢了标题，A/B 切分退化成"全篇当 B 区"，
            body_lines.append(ln)  # A 区字数/WPM 检查静默失效，事故文件从未被真正验过字数）
    return scan, "\n".join(body_lines)

def split_ab(lines):
    """按标题切 A 稿/B 稿区。返回 (a_lines, b_lines)；都无则按是否含【听觉】整体判 B 或 A。"""
    a_idx = b_idx = None
    for i, ln in enumerate(lines):
        if not re.match(r"^#{1,3}\s", ln):
            continue
        if a_idx is None and re.search(r"Part\s*3a|A\s*稿|纯口播", ln):
            a_idx = i
        if b_idx is None and re.search(r"Part\s*3b|B\s*稿|三轨", ln):
            b_idx = i
    if a_idx is None and b_idx is None:
        return ([], lines) if any("【听觉】" in ln for ln in lines) else (lines, [])
    a = lines[a_idx:(b_idx if b_idx is not None and b_idx > a_idx else len(lines))] if a_idx is not None else []
    b = lines[b_idx:(a_idx if a_idx is not None and a_idx > b_idx else len(lines))] if b_idx is not None else []
    return a, b

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

def extract_spoken_blocks(lines):
    """听觉块 = 【听觉】/[听觉] 行 + 引号开头续行，到下一个 【 轨标记为止。
    兼容全角【听觉】与半角 [听觉]/**[听觉]** 两种三轨写法（2026-09-10 实战：
    A 稿用半角格式，原实现只认全角，A 区口播被静默漏扫）。"""
    AUD = re.compile(r"[【\[]\s*听觉\s*[】\]]")
    blocks, cur = [], None
    for ln in lines:
        s = ln.strip()
        if AUD.search(s):
            if cur:
                blocks.append(cur)
            cur = ln
        elif cur is not None:
            if s.startswith(("【", "[", "##")):
                blocks.append(cur)
                cur = None
            elif s.startswith(('"', "“", "『", "「")):
                cur += "\n" + ln
            # [关键词]/[音效]/[BGM] 等听觉行内的修饰标记：留在块里无害（引号提取会跳过）
    if cur:
        blocks.append(cur)
    return blocks

def spoken_text(block):
    """从听觉块提取全部引号内台词；无引号则取第一个全角/半角冒号后的内容。"""
    qs = QUOTE.findall(block)
    if qs:
        return "".join(qs)
    tail = re.split(r"[：:]", block, 1)[-1]
    return tail if tail != block else ""

def count_chars(text):
    return len(re.findall(r"[一-鿿A-Za-z0-9]", text))

def split_sentences(text):
    """朗读句切分：句末标点 + 逗号顿号 + 脚本停顿符 / 都切。
    A4 单句≤20字针对朗读负担，停顿标记（,=0.5s /=1s）就是呼吸点，
    逗号连接的短分句不算长难句。"""
    return [s for s in re.split(r"[。！？!?；;，、/]", text) if s.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--keywords", default=None)
    a = ap.parse_args()

    raw_lines = open(a.script, encoding="utf-8").read().splitlines()
    lines, body = load_script(a.script)
    dur, meta_kws = parse_meta(raw_lines)
    if a.duration:
        dur = a.duration
    kws = [k.strip() for k in a.keywords.split(",")] if a.keywords else meta_kws

    hard, warn = [], []
    def h(msg): hard.append(msg)
    def w(msg): warn.append(msg)

    # ---- 结构闸：同名章节重复（2026-09-10 实战：单文件出现两个「Part 4 自检报告」，
    #      一带后缀一不带，精确匹配抓不到——归一化括号后缀后比较）----
    heads = [re.sub(r"[（(].*$", "", ln.strip()).rstrip()
             for ln in raw_lines if re.match(r"^## ", ln.strip())]
    dup = sorted({x for x in heads if heads.count(x) > 1})
    if dup:
        h(f"同名章节重复: {'; '.join(dup)}——单一权威版本原则，合并或删除重复节")

    # ---- 硬拦截黑名单（含围栏内正文）----
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
    n_visual = len(re.findall(r"【视觉】", body))
    if n_cred == 0:
        h("全场零凭证标记（HR-5：每个画面必须有 [凭证 N]）")
    elif n_visual > 0 and n_cred < n_visual / 2:
        w(f"凭证偏少: 视觉段 {n_visual} 处 vs 凭证 {n_cred} 处（HR-5）")

    # ---- 听觉块解析：单句长度 + 口播字数 ----
    blocks = extract_spoken_blocks(lines)
    spoken = 0
    over20, over35 = 0, 0
    for b in blocks:
        text = spoken_text(b)
        spoken += count_chars(text)
        for s in split_sentences(text):
            n = count_chars(s)
            if n > 35:
                over35 += 1
            elif n > 20:
                over20 += 1
    if over35:
        h(f"超长句 {over35} 处（单句 >35 字，A4 严禁长难句）")
    if over20:
        w(f"超字句 {over20} 处（单句 21-35 字，A4 上限 20 字）")

    # ---- 视觉切换估算（【视觉】行及其后续 [画面描述] 行，按 →、+、、 拆分）----
    cuts, in_visual = 0, False
    for ln in lines:
        s = ln.strip()
        if "【视觉】" in ln:
            in_visual = True
            m = re.search(r"画面描述[】\]]\s*[：:]\s*(.+)$", ln)
            if m:
                parts = [p for p in CUT_SEP.split(m.group(1)) if p.strip()]
                cuts += max(1, len(parts))
                in_visual = False  # 行内已取到画面描述
        elif in_visual and s.startswith("[画面描述]"):
            m = re.match(r"\[画面描述\]\s*[：:]\s*(.+)$", s)
            if m:
                parts = [p for p in CUT_SEP.split(m.group(1)) if p.strip()]
                cuts += max(1, len(parts))
            in_visual = False
        elif s.startswith("【") or s.startswith("##"):
            in_visual = False

    # ---- 拍点密度（只数【控制】块内的 [拍点]/Sub-hook/Mob Drop，防自检报告虚增）----
    beats, in_control = 0, False
    for ln in lines:
        s = ln.strip()
        if "【控制】" in ln:
            in_control = True
        elif s.startswith("【") or s.startswith("##"):
            in_control = False
        if in_control:
            beats += len(re.findall(r"【拍点】|\[拍点\]|Sub-hook|Mob Drop", ln))

    # ---- WPM / 拍点 / 字每切 ----
    if dur:
        wpm = spoken / dur
        if not 260 <= wpm <= 320:
            w(f"WPM {wpm:.0f} 越界（合格 260-320，锚定 280；口播 {spoken} 字 / {dur:.0f} 分钟，"
              f"实际可支撑 {spoken/280:.1f} 分钟）")
        if beats / dur < 2:
            w(f"拍点密度 {beats/dur:.1f}/分钟（A3 合格 ≥2/分钟；共 {beats} 个拍点）")
        if cuts:
            per_cut = spoken / cuts
            if not 20 <= per_cut <= 30:
                w(f"字每切 {per_cut:.0f} 越界（A2 每 20-30 字 1 次视觉切换；口播 {spoken} 字 / 估算 {cuts} 切）")

    # ---- SEO 关键词 ----
    for k in kws:
        c = body.count(k)
        need = int(dur / 1.0) if dur else 0  # 每 50 秒 ≥1 次 ≈ 每分钟 ≥1 次
        if c < max(1, need // 2):
            w(f"SEO 词「{k}」出现 {c} 次（目标约 {need} 次/全片）")

    # ---- v0.4 故事层检查 ----
    a_lines, b_lines = split_ab(lines)
    if a_lines:
        a_text = "\n".join(a_lines)
        if dur:
            front = a_text[:int(dur * 35)]  # 开场 3 分钟 ≈ 12.5% × 280 字/分
            hits = sorted(set(STORY_FINANCE.findall(front)))
            if hits:
                h(f"开场 3 分钟财报术语: 命中 {hits}（主线铁律：起幕立现场，数据只作转幕道具）")
        if not re.search(r"\*\*[^*\n]{4,}\*\*", a_text):
            w("A 稿零黑体金句（四幕每幕尾需 1 句锚定观点，**黑体**标注）")
    if b_lines:
        b_text = "\n".join(b_lines)
        n_opinion = len(re.findall(r"\[观点\]", b_text))
        if n_opinion == 0:
            h("B 稿全片零 [观点] 标记（HR-8：没有自己观点的视频不得交付）")
        n_control = len(re.findall(r"【控制】", b_text))
        n_labeled = len(re.findall(r"\[内容层\]", b_text))
        if n_control >= 3 and n_labeled < n_control * 0.7:
            w(f"[内容层] 覆盖率不足: {n_labeled}/{n_control} 段（HR-8 四层标注：事实/争议/转述/观点）")
        for i, ln in enumerate(b_lines):
            if "事实-单源" in ln and not re.search(r"据|疑似|反映", "\n".join(b_lines[max(0, i-8):i+1])):
                w(f"单源事实未限定: {ln.strip()[:40]}（应带'据X反映/疑似'）")
    # 双语人名：首个出现处前 30 字内无中文 = 未标注
    no_url = URL_STRIP.sub("", body)
    seen, unannotated = set(), []
    for m in LATIN_NAME.finditer(no_url):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        ctx = no_url[max(0, m.start() - 30):m.start()]
        if not re.search(r"[一-鿿]", ctx):
            unannotated.append(name)
    if unannotated:
        w(f"英文人名未标注中文译名: {unannotated}（规范：首次出现'中文译名（English Name）'）")

    print(f"指标基线: 口播 {spoken} 字 | 听觉块 {len(blocks)} | 视觉段 {n_visual} | "
          f"估算切换 {cuts} | 拍点 {beats}" + (f" | 时长 {dur:.0f} 分钟" if dur else ""))
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
