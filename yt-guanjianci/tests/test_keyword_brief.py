#!/usr/bin/env python3
"""test_keyword_brief.py 测试——yt-guanjianci 关键词+标题库机械闸（TDD：先红后绿）

闸管三件事：
1. 输入校验：词根非空；关键词包 JSON schema 合法（四级分级字段齐）
2. 标题矩阵机械规范：每条 8-35 字 / 不含禁用标点（,。！!）/ 无占位符
3. 依赖标注：数据源档位（A=DataForSEO 精确 / B= Trends 相对 / C= 手工定性）
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import keyword_brief as kb  # noqa: E402


def make_pack(source_grade="C"):
    return {
        "词根": "星宇裁员",
        "查询时间": "2026-09-10",
        "数据源档位": source_grade,
        "主关键词": {"词": "星宇科技裁员", "分级": "小词", "月搜索量": None, "竞争度": "中（定性）"},
        "次级关键词": [{"词": "星宇 道歉信", "分级": "微长尾"}],
        "长尾词": ["星宇裁员 真相", "星宇为什么裁员"],
        "竞品标题用词": {"高频词": ["裁员", "道歉"], "高CTR句式": ["数字+反转", "身份+爆料"]},
        "标题矩阵": [
            {"候选": "裁掉600人后星宇连夜删掉了道歉信", "公式": "数字+反转",
             "适用阶段": "推荐期", "钩子词": "连夜删掉", "句式": "数字+反转", "实体词": "星宇"},
            {"候选": "为什么星宇一边扩招一边裁员？幕后真相", "公式": "悬念设问",
             "适用阶段": "冷启动", "钩子词": "为什么", "句式": "悬念设问", "实体词": "星宇"},
        ],
        "封面词": ["裁员", "600人 清算"],
        "验证记录": [],
    }


class TestTitleRules(unittest.TestCase):
    def test_length_bounds(self):
        self.assertTrue(kb.title_ok("裁掉600人后星宇连夜删掉了道歉信"))
        self.assertFalse(kb.title_ok("短"))
        self.assertFalse(kb.title_ok("太" * 36))

    def test_banned_punctuation(self):
        self.assertFalse(kb.title_ok("标题,带逗号"))
        self.assertFalse(kb.title_ok("标题。带句号"))
        self.assertFalse(kb.title_ok("标题!带叹号"))
        self.assertTrue(kb.title_ok("标题：带冒号测试"))
        self.assertTrue(kb.title_ok("标题？带问号测试"))

    def test_placeholder(self):
        self.assertFalse(kb.title_ok("标题[待填]内容"))
        self.assertFalse(kb.title_ok("标题 XX 内容"))


class TestValidatePack(unittest.TestCase):
    def test_good_pack_passes(self):
        r = kb.validate_pack(make_pack())
        self.assertTrue(r["passed"], r["errors"])

    def test_missing_grade(self):
        p = make_pack()
        p["数据源档位"] = "X"
        r = kb.validate_pack(p)
        self.assertFalse(r["passed"])
        self.assertTrue(any("数据源档位" in e for e in r["errors"]))

    def test_bad_title_caught(self):
        p = make_pack()
        p["标题矩阵"][0]["候选"] = "bad,title"
        r = kb.validate_pack(p)
        self.assertFalse(r["passed"])
        self.assertTrue(any("标题" in e for e in r["errors"]))

    def test_bad_cover_word_caught(self):
        p = make_pack()
        p["封面词"] = ["经过长期调查发现"]
        r = kb.validate_pack(p)
        self.assertFalse(r["passed"])
        self.assertTrue(any("封面词" in e for e in r["errors"]))

    def test_schema_guard(self):
        p = make_pack()
        p["主关键词"] = {"词": "x"}  # 缺分级
        r = kb.validate_pack(p)
        self.assertFalse(r["passed"])
        self.assertTrue(any("主关键词" in e for e in r["errors"]))


class TestGradeMap(unittest.TestCase):
    def test_grade_notes(self):
        self.assertIn("DataForSEO", kb.GRADE_NOTES["A"])
        self.assertIn("手工", kb.GRADE_NOTES["C"])


class TestCoverWords(unittest.TestCase):
    def test_valid_cover_word(self):
        self.assertTrue(kb.cover_word_ok("蒸发"))
        self.assertTrue(kb.cover_word_ok("3万亿 蒸发"))
        self.assertTrue(kb.cover_word_ok("清算"))

    def test_too_long_caught(self):
        self.assertFalse(kb.cover_word_ok("蒸发了三万亿"))
        self.assertFalse(kb.cover_word_ok("一夜之间全部蒸发"))

    def test_process_and_neutral_caught(self):
        """三不选：过程/背景词与中性词硬拦。"""
        self.assertFalse(kb.cover_word_ok("经过长期调查发现"))
        self.assertFalse(kb.cover_word_ok("供应链整合"))

    def test_full_sentence_caught(self):
        """三不选：完整句子硬拦（含谓语连接）。"""
        self.assertFalse(kb.cover_word_ok("这家公司亏掉了1000亿"))

    def test_empty(self):
        self.assertFalse(kb.cover_word_ok(""))
        self.assertFalse(kb.cover_word_ok("  "))


class TestMainCLI(unittest.TestCase):
    def test_exit_codes(self):
        good = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(make_pack(), good, ensure_ascii=False)
        good.close()
        bad = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        p = make_pack()
        p["数据源档位"] = "Z"
        json.dump(p, bad, ensure_ascii=False)
        bad.close()
        try:
            self.assertEqual(kb.main_argv(["keyword_brief.py", good.name]), 0)
            self.assertEqual(kb.main_argv(["keyword_brief.py", bad.name]), 1)
            self.assertEqual(kb.main_argv(["keyword_brief.py"]), 2)
        finally:
            os.unlink(good.name)
            os.unlink(bad.name)


if __name__ == "__main__":
    unittest.main()
