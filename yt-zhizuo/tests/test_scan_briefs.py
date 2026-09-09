#!/usr/bin/env python3
"""scan_briefs.py 测试——yt-zhizuo 四件套机械扫描闸（TDD：先红后绿）

闸管四件事：
1. 四件齐全（Part1~Part5 节头在文档内）
2. 逐镜头有源（Part2 每行：形态合法 / 画面非空 / 来源非空；零静默丢弃靠销号表）
3. 时间码连续（Part2/3/4 行内可解析、段间单调不重叠；Part2 总时长 vs Part1 成片时长 ±10%）
4. 混合形态专项：形态=AI 必须带完整生成提示词；形态=露脸必须标机位/景别
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import scan_briefs as sb  # noqa: E402


def make_doc(part2_rows, part1_minutes=4, part3_rows=None, part4_rows=None):
    p3 = part3_rows or ["| S01 | 00:00-01:30 | 硬切 | 黑体 | M1 | — |"] * 1
    p4 = part4_rows or ["| M1 悬疑 | 00:00-04:00 | Tension | dark synth | 待填 | -12dB |"] * 1
    return "\n".join([
        "# 制作四件套：T-2026-009 测试",
        "## Part 1 配音 Brief",
        f"> 录制方式：自录｜【成片时长：约 {part1_minutes} 分钟】",
        "| 段号 | 时间码 | 脚本原文（标注后） | WHY 提示 |",
        "|---|---|---|---|",
        "| S01 | 00:00-04:00 | [情绪:严肃] 正文 // **重音** | 动机 |",
        "## Part 2 分镜与 B-Roll 清单（段级）",
        "> 形态：露脸/B-Roll/AI｜来源销号制",
        "| 段号 | 时间码 | 时长 | 形态 | 画面内容 | 素材来源 | AI 生成提示词 | 连续性约束 |",
        "|---|---|---|---|---|---|---|---|",
        *part2_rows,
        "## Part 3 剪辑 Brief",
        "| 段号 | 时间码 | 剪辑动作 | 字幕样式 | 转场 | BGM 段 | 备注 |",
        "|---|---|---|---|---|---|---|",
        *p3,
        "## Part 4 配乐提示",
        "| 阶段 | 覆盖时间码 | 情绪标签 | 检索关键词 | 候选曲目 | 音量/闪避 | 转场音效 |",
        "|---|---|---|---|---|---|---|",
        *p4,
        "## Part 5 销号与扫描报告",
        "| 检查项 | 结果 |",
    ])


GOOD_P2 = [
    "| S01 | 00:00-01:30 | 90s | 露脸 | 中景，固定机位，创作者直视镜头 | 自行拍摄：iPhone+DJI Mic | — | 深色衬衫全片统一 |",
    "| S02 | 01:30-03:00 | 90s | B-Roll | 发布会现场空镜，灯光扫过观众席 | ziliao §3.2 素材 #7 | — | — |",
    "| S03 | 03:00-04:00 | 60s | AI | 空荡办公室，黄昏百叶窗光影 | 自行获取或 AI | 可灵：空旷办公室，黄昏，写实，慢推镜头 | — |",
]

BAD_NO_PROMPT = [
    "| S01 | 00:00-02:00 | 120s | AI | 空荡办公室黄昏 | ziliao 无→自行获取 | — | — |",
    "| S02 | 02:00-04:00 | 120s | B-Roll | 街景 | ziliao §2.1 素材 #3 | — | — |",
]

BAD_NO_CAMERA = [
    "| S01 | 00:00-02:00 | 120s | 露脸 | 创作者讲述公司历史 | 自行拍摄 | — | — |",
    "| S02 | 02:00-04:00 | 120s | B-Roll | 街景 | ziliao §2.1 素材 #3 | — | — |",
]

BAD_NON_MONOTONIC = [
    "| S01 | 00:00-02:00 | 120s | B-Roll | 街景A | ziliao #1 | — | — |",
    "| S02 | 01:30-04:00 | 150s | B-Roll | 街景B（起点早于上一段终点） | ziliao #2 | — | — |",
]


def write_doc(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


class TestTimecode(unittest.TestCase):
    def test_parse_mmss_range(self):
        self.assertEqual(sb.parse_timecode("00:00-01:30"), (0, 90))
        self.assertEqual(sb.parse_timecode("3:00-5:30"), (180, 330))

    def test_parse_chinese_colon(self):
        self.assertEqual(sb.parse_timecode("00：00-01：30"), (0, 90))


class TestParsePart2(unittest.TestCase):
    def test_good_rows(self):
        doc = make_doc(GOOD_P2)
        rows = sb.parse_segments_table(doc, "Part 2")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["form"], "露脸")
        self.assertEqual(rows[2]["form"], "AI")
        self.assertTrue(rows[2]["prompt"].startswith("可灵"))

    def test_separator_and_header_skipped(self):
        doc = make_doc(["|---|---|---|---|---|---|---|---|", *GOOD_P2])
        self.assertEqual(len(sb.parse_segments_table(doc, "Part 2")), 3)


class TestAudit(unittest.TestCase):
    def test_good_doc_passes(self):
        path = write_doc(make_doc(GOOD_P2))
        try:
            r = sb.audit(path)
            self.assertTrue(r["passed"], r["errors"])
            self.assertEqual(r["stats"]["segments"], 3)
            self.assertEqual(r["stats"]["form_counts"]["AI"], 1)
        finally:
            os.unlink(path)

    def test_ai_missing_prompt_caught(self):
        path = write_doc(make_doc(BAD_NO_PROMPT))
        try:
            r = sb.audit(path)
            self.assertFalse(r["passed"])
            self.assertTrue(any("AI" in e and "提示词" in e for e in r["errors"]))
        finally:
            os.unlink(path)

    def test_lian_missing_camera_caught(self):
        path = write_doc(make_doc(BAD_NO_CAMERA))
        try:
            r = sb.audit(path)
            self.assertFalse(r["passed"])
            self.assertTrue(any("露脸" in e and "机位" in e for e in r["errors"]))
        finally:
            os.unlink(path)

    def test_non_monotonic_caught(self):
        path = write_doc(make_doc(BAD_NON_MONOTONIC))
        try:
            r = sb.audit(path)
            self.assertFalse(r["passed"])
            self.assertTrue(any("时间" in e for e in r["errors"]))
        finally:
            os.unlink(path)

    def test_missing_part_fails(self):
        path = write_doc(make_doc(GOOD_P2).replace("## Part 4 配乐提示", "## Part X"))
        try:
            r = sb.audit(path)
            self.assertFalse(r["passed"])
            self.assertTrue(any("Part 4" in e for e in r["errors"]))
        finally:
            os.unlink(path)

    def test_duration_ratio_caught(self):
        # 分镜 4 分钟 vs 声明成片 24 分钟 → 16%，超出 ±10%
        path = write_doc(make_doc(GOOD_P2, part1_minutes=24))
        try:
            r = sb.audit(path)
            self.assertFalse(r["passed"])
            self.assertTrue(any("时长" in e for e in r["errors"]))
        finally:
            os.unlink(path)


class TestMainCLI(unittest.TestCase):
    def test_exit_codes(self):
        good = write_doc(make_doc(GOOD_P2))
        bad = write_doc(make_doc(BAD_NO_PROMPT))
        try:
            self.assertEqual(sb.main_argv(["scan_briefs.py", good]), 0)
            self.assertEqual(sb.main_argv(["scan_briefs.py", bad]), 1)
            self.assertEqual(sb.main_argv(["scan_briefs.py"]), 2)
        finally:
            os.unlink(good)
            os.unlink(bad)


if __name__ == "__main__":
    unittest.main()
