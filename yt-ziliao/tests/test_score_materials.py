#!/usr/bin/env python3
"""score_materials.py 回归测试（v2.5.0 审计链）"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import score_materials as sm  # noqa: E402


def make_item(i, authority="高", verification="多方证实", stance="中立", url_shift=0, **kw):
    item = {
        "title": f"素材{i}",
        "url": f"https://example.com/{i + url_shift}",
        "platform": "微博",
        "language": "zh",
        "publish_date": "2026-09-01",
        "type": "新闻报道",
        "authority": authority,
        "verification": verification,
        "stance": stance,
    }
    item.update(kw)
    return item


def make_items(n, **kw):
    return [make_item(i, **kw) for i in range(n)]


class TestUnselectedAudit(unittest.TestCase):
    """每条输入素材必须可追溯：入选 selected 或落选 unselected（带理由），零静默丢弃。"""

    def test_every_item_accounted(self):
        items = make_items(50, authority="中", verification="单一来源")
        result = sm.select_items(items)
        sel_urls = {s["url"] for s in result["selected"]}
        unsel_urls = {u["url"] for u in result["unselected"]}
        input_urls = {i["url"] for i in items}
        self.assertEqual(sel_urls | unsel_urls, input_urls)
        self.assertEqual(len(sel_urls) + len(unsel_urls), len(items))

    def test_unselected_reason_nonempty(self):
        items = make_items(50, authority="中", verification="单一来源")
        result = sm.select_items(items)
        self.assertTrue(result["unselected"])
        for u in result["unselected"]:
            self.assertTrue(u.get("reason"), f"落选条目缺理由: {u}")

    def test_cap_reason_when_full(self):
        items = make_items(90, authority="高", verification="多方证实")
        result = sm.select_items(items)
        self.assertEqual(result["selected_count"], 80)
        for u in result["unselected"]:
            self.assertIn("80", u["reason"])


class TestRejectedSkippedValidation(unittest.TestCase):
    """拒收/跳过清单落盘校验：reason 必填，缺失即报 invalid。"""

    def test_valid_entries_pass(self):
        data = {
            "rejected": [{"title": "t", "url": "https://x.com", "reason": "内容农场"}],
            "skipped": [{"dimension": "抖音", "query": "星宇 裁员", "reason": "平台封闭"}],
        }
        audit = sm.audit_summary(data)
        self.assertEqual(audit["rejected_count"], 1)
        self.assertEqual(audit["skipped_count"], 1)
        self.assertEqual(audit["invalid"], [])

    def test_missing_reason_flagged(self):
        data = {
            "rejected": [{"title": "t", "url": "https://x.com"}, {"title": "ok", "url": "https://y.com", "reason": "重复"}],
            "skipped": [{"dimension": "知乎"}],
        }
        audit = sm.audit_summary(data)
        self.assertEqual(len(audit["invalid"]), 2)
        kinds = {i["kind"] for i in audit["invalid"]}
        self.assertEqual(kinds, {"rejected", "skipped"})

    def test_absent_arrays_default_zero(self):
        audit = sm.audit_summary({})
        self.assertEqual(audit["rejected_count"], 0)
        self.assertEqual(audit["skipped_count"], 0)


class TestMainEndToEnd(unittest.TestCase):
    """main() 输出须含 audit（rejected/skipped 透传 + invalid + unselected）。"""

    def run_main(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
            path = f.name
        try:
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                sm.main_argv(["score_materials.py", path])
            return json.loads(buf.getvalue())
        finally:
            os.unlink(path)

    def test_audit_in_output(self):
        items = make_items(35, authority="中", verification="单一来源")
        data = {
            "topic": "测试",
            "items": items,
            "rejected": [{"title": "r1", "url": "https://r.com", "reason": "营销号"}],
            "skipped": [{"dimension": "公众号", "reason": "未接入"}],
        }
        out = self.run_main(data)
        self.assertIn("audit", out)
        self.assertEqual(out["audit"]["rejected_count"], 1)
        self.assertEqual(out["audit"]["skipped_count"], 1)
        self.assertEqual(len(out["audit"]["invalid"]), 0)
        self.assertTrue(len(out["audit"]["unselected"]) > 0)


class TestDistributionRegression(unittest.TestCase):
    """v2.5.0 不得破坏既有精选分布约束。"""

    def test_high_quality_all_selected(self):
        items = make_items(40, authority="高", verification="多方证实")
        result = sm.select_items(items)
        self.assertTrue(result["passed"])
        self.assertEqual(result["selected_count"], 40)

    def test_low_quality_conditional_pass(self):
        # 8 条：2 高多方 + 4 中单一 + 2 低单一 → 踩线满足 <10 条档 conditional_pass
        items = (
            make_items(2, authority="高", verification="多方证实")
            + make_items(4, authority="中", verification="单一来源", url_shift=10)
            + make_items(2, authority="低", verification="单一来源", url_shift=20)
        )
        result = sm.select_items(items)
        self.assertFalse(result["passed"])
        self.assertTrue(result["conditional_pass"])


if __name__ == "__main__":
    unittest.main()
