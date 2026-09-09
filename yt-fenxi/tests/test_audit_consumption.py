#!/usr/bin/env python3
"""audit_consumption.py 测试——消费对账机械闸门（防偷懒/防遗漏）"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import audit_consumption as ac  # noqa: E402

MANIFEST = {
    "topic_id": "T-2026-009",
    "report_url": "https://feishu.cn/docx/X",
    "materials": [
        {"id": "#1", "url": "https://a.com/1", "title": "致歉信"},
        {"id": "#2", "url": "https://b.com/2?utm_source=x", "title": "人社局通报"},
        {"id": "#3", "url": "https://c.com/3", "title": "律师观点"},
    ],
    "disputes": [{"id": "D1"}, {"id": "D2"}],
    "angles": [{"id": "A1"}, {"id": "A2"}],
}


def write_tmp(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name

CARD_FULL = """# 选题分析卡

## 五、核心争议点提炼（N5.5）
| # | 争议点 | 站边 | 依据 |
| 1 | D1 是否构成裁员 | 乙方 | N5#1 |

未选争议点去向：
| 争议点 | 去向 | 原因 |
| D2 | 悬置 | 已裁决无对立 |

## 六、切入点穷举（N6）
对照 ziliao §5.1：A1 → 已纳入穷举 #1；A2 → 未纳入（与 #1 同质）

## 十一、消费对账
| 素材 | 去向 | 原因 |
|------|------|------|
| #1 https://a.com/1 | N5 已证实 #1 | — |
| #2 https://b.com/2 | 不采用 | 与 #1 同源重复 |
| #3 https://c.com/3 | N5.5 依据 | — |
"""

CARD_LAZY = """# 选题分析卡

## 五、核心争议点提炼（N5.5）
| # | 争议点 | 站边 | 依据 |
| 1 | D1 是否构成裁员 | 乙方 | N5#1 |

## 六、切入点穷举（N6）
| # | 角度 | 综合分 |
| 1 | 我的新角度 | 88 |
"""


class TestUrlNormalize(unittest.TestCase):
    def test_strip_utm_fragment_slash(self):
        self.assertEqual(ac.normalize_url("https://B.com/2/?utm_source=x#frag"),
                         "https://b.com/2")


class TestAudit(unittest.TestCase):
    def test_full_card_passes(self):
        card = write_tmp(CARD_FULL)
        try:
            result = ac.audit(MANIFEST, card)
            self.assertEqual(result["unconsumed_materials"], [])
            self.assertEqual(result["unconsumed_disputes"], [])
            self.assertEqual(result["unconsumed_angles"], [])
            self.assertTrue(result["passed"])
        finally:
            os.unlink(card)

    def test_lazy_card_caught(self):
        card = write_tmp(CARD_LAZY)
        try:
            result = ac.audit(MANIFEST, card)
            self.assertFalse(result["passed"])
            # #2（带 utm 也被规范化命中：正文无 b.com 且无对账表）
            norm_urls = [ac.normalize_url(m["url"]) for m in result["unconsumed_materials"]]
            self.assertIn("https://b.com/2", norm_urls)
            self.assertIn("D2", result["unconsumed_disputes"])
            self.assertIn("A1", result["unconsumed_angles"])
            self.assertIn("A2", result["unconsumed_angles"])
        finally:
            os.unlink(card)

    def test_reconciliation_section_saves_unconsumed(self):
        """素材没进正文，但进了消费对账表（带 URL）→ 算对账齐。"""
        card = write_tmp(CARD_LAZY + "\n## 十一、消费对账\n| 素材 | 去向 | 原因 |\n|---|---|---|\n"
                                      "| #2 | 不采用 | 单一来源 |\n| #3 https://c.com/3 | N5 引用 | — |\n")
        try:
            result = ac.audit(MANIFEST, card)
            urls = [m["url"] for m in result["unconsumed_materials"]]
            self.assertNotIn("https://b.com/2", urls)   # 对账表内出现即销号
            self.assertNotIn("https://c.com/3", urls)
        finally:
            os.unlink(card)

    def test_dispute_in_reconciliation_section(self):
        card = write_tmp(CARD_LAZY + "\n## 十一、消费对账\n未选争议点去向：D2 悬置（人社局已裁决）\n")
        try:
            result = ac.audit(MANIFEST, card)
            self.assertNotIn("D2", result["unconsumed_disputes"])
        finally:
            os.unlink(card)


class TestMainCLI(unittest.TestCase):
    def test_exit_codes(self):
        m = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(MANIFEST, m, ensure_ascii=False)
        m.close()
        c = write_tmp(CARD_LAZY)
        try:
            self.assertEqual(ac.main_argv(["audit_consumption.py", m.name, c]), 1)
            c2 = write_tmp(CARD_FULL)
            try:
                self.assertEqual(ac.main_argv(["audit_consumption.py", m.name, c2]), 0)
            finally:
                os.unlink(c2)
        finally:
            os.unlink(m.name)
            os.unlink(c)


if __name__ == "__main__":
    unittest.main()
