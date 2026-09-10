#!/usr/bin/env python3
"""
generate_toc.py — 给 Markdown 交付物自动生成目录（TOC）

飞书云盘导入的 .md 不会自动生成大纲（云文档才有），本脚本在推送飞书前
扫描 H2/H3 标题，生成目录区块。

用法：
    python3 scripts/generate_toc.py <file.md>           # 就地更新（默认）
    python3 scripts/generate_toc.py <file.md> --stdout  # 只打印结果

规则：
- 目录区块用 <!-- TOC --> / <!-- /TOC --> 标记包裹；已存在则原位替换，不存在则
  插在第一个 H1 标题行之后
- 只收录 ## 与 ### 两级；目录项为纯文本列表（H2 顶格、H3 缩进两空格），
  不生成锚点链接（飞书 .md 预览不保证锚点可用）
"""
import sys
from pathlib import Path

MARK_BEGIN = "<!-- TOC -->"
MARK_END = "<!-- /TOC -->"


def build_toc(lines: list[str]) -> list[str]:
    toc = [MARK_BEGIN, "", "## 目录", ""]
    for ln in lines:
        if ln.startswith("## ") and not ln.startswith("### "):
            title = ln[3:].strip()
            if title == "目录":
                continue
            toc.append(f"- {title}")
        elif ln.startswith("### "):
            title = ln[4:].strip()
            toc.append(f"  - {title}")
    toc += ["", MARK_END]
    return toc


def process(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    # 去掉旧目录区块
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip() == MARK_BEGIN:
            while i < len(lines) and lines[i].strip() != MARK_END:
                i += 1
            i += 1  # 跳过 MARK_END
            continue
        out.append(lines[i])
        i += 1
    toc = build_toc(out)
    # 找插入点：第一个 H1 之后；无 H1 则文件开头
    insert_at = 0
    for idx, ln in enumerate(out):
        if ln.startswith("# "):
            insert_at = idx + 1
            break
    final = out[:insert_at] + [""] + toc + [""] + out[insert_at:]
    return "\n".join(final).rstrip("\n") + "\n"


def main() -> None:
    if len(sys.argv) < 2:
        print(f"用法: python3 {sys.argv[0]} <file.md> [--stdout]", file=sys.stderr)
        sys.exit(1)
    path = Path(sys.argv[1])
    result = process(path)
    if "--stdout" in sys.argv:
        print(result, end="")
    else:
        path.write_text(result, encoding="utf-8")
        print(f"TOC 已更新: {path}")


if __name__ == "__main__":
    main()
