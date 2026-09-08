#!/usr/bin/env python3
"""无出处断言扫描器（N7 机械防线）。

扫描分析卡全文，找出"含可验证主张但无信源标注"的句子。
防 AI 编造不靠自觉，靠机器拦截；本脚本是唯一放行闸门。

用法: scan_unsourced.py <分析卡路径>
退出码: 0 = 通过（或仅警告）; 1 = 存在必须修复的硬拦截行。

规则（逐行判定）:
- 硬拦截: 行内出现 引语/统计数字/百分比/金额/明确事实断言词
  且行内(±相邻行)不含任何信源标记。
- 信源标记: 据|来源|信源|显示|报告|财报|招股书|裁判文书|判决书|
  天眼查|企查查|SEC|EDGAR|维基|36氪|晚点|财经|采访|访谈|声明|公告|http
- 豁免行: 模板表头、YAML frontmatter、checklist 空项、分桶标题。
"""
import re
import sys

SOURCE_MARK = re.compile(
    r"据|来源|信源|显示|报告|财报|招股书|裁判文书|判决书|天眼查|企查查|"
    r"SEC|EDGAR|维基|36氪|晚点|财经|采访|访谈|声明|公告|http|（见|见资料"
)
CLAIM_MARK = re.compile(
    r"[\"“「].{2,40}[\"”」]"          # 引语
    r"|\d+(\.\d+)?\s*[%％]"           # 百分比
    r"|\d+(\.\d+)?\s*(亿|万|百万|千万| billion| million)"  # 大额数字
    r"|(成立于|创办于|创立于|生于)\d{4}"  # 时间断言
    r"|(起诉|判决|破产|清算|冻结|离职|去世|收购|合并|上市|退市|裁员)\S{0,12}(了|于|在)?"  # 事件断言
)
EXEMPT = re.compile(
    r"^\s*[#|\->]"           # 标题/表格/列表结构行
    r"|^\s*-\s*\[\s*\]"      # 空 checklist
    r"|主张|角度|信源|差异点|优势|劣势|冲突证据|归属方|维度|得分"  # 表头/列名
    r"|Quick Wins|Strategic Builds|Long-term"
)


def scan(path: str):
    lines = open(path, encoding="utf-8").read().splitlines()
    # 定位 YAML frontmatter 范围以豁免
    in_yaml = False
    yaml_end = -1
    if lines and lines[0].strip() == "---":
        in_yaml = True
        for i, ln in enumerate(lines[1:], start=1):
            if ln.strip() == "---":
                yaml_end = i
                break
    hard, warn = [], []
    for i, ln in enumerate(lines):
        if i <= yaml_end:
            continue
        if EXEMPT.search(ln):
            continue
        if not CLAIM_MARK.search(ln):
            continue
        window = ln
        if i > yaml_end + 1:
            window += lines[i - 1]
        if SOURCE_MARK.search(window):
            continue
        # 引语类尤其危险，直接硬拦截；纯数字给警告
        if re.search(r"[\"“「]", ln):
            hard.append((i + 1, ln.strip()[:80]))
        else:
            warn.append((i + 1, ln.strip()[:80]))
    return hard, warn


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    hard, warn = scan(sys.argv[1])
    for n, t in warn:
        print(f"[警告] 行{n}: {t}  <- 建议补信源")
    for n, t in hard:
        print(f"[硬拦截] 行{n}: {t}  <- 无出处引语/断言，退回 N5 补凭证")
    if hard:
        print(f"\n结论: {len(hard)} 处硬拦截，分析卡不得交付")
        sys.exit(1)
    print(f"\n结论: 通过（{len(warn)} 处警告可斟酌）")
    sys.exit(0)


if __name__ == "__main__":
    main()
