#!/usr/bin/env python3
"""build_manifest.py 测试（v2.6.0 交接清单生成器）"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import build_manifest as bm  # noqa: E402


REPORT_SAMPLE = """# 星宇车灯 资料汇总分析报告

## 三、观点整理（条目清单）

### 3.5 争议点原料清单（挖掘记录，不判断）

| # | 争议点 | 甲方主张 | 乙方主张 | 甲方来源 | 乙方来源 | 是否可裁决 |
|---|--------|---------|---------|---------|---------|-----------|
| 1 | 是否构成经济性裁员 | 公司：协商解除 | 律师：实质构成 | https://a.com | https://b.com | 可裁决-依据：法定要件 |
| 2 | 离职证明口径 | 公司要求个人原因 | 应届生质疑 | https://c.com | https://d.com | 未决 |

## 五、切入角度盘点（只盘点，不推荐）

### 5.1 现有切入角度盘点

| 角度 | 类型 | 代表内容 | 关注度 |
|------|------|---------|-------|
| [跨境ESG合规](https://e.com) | 政策/合规 | 港交所投诉 | 高 |
| [业绩承压转型](https://f.com) | 数据/产业链 | 净减2894人 | 高 |

## 六、信息来源总表

### 6.1 精选资料

| # | URL | 标题 | 类型 | 权威性 | 核实状态 | 立场 | 摘录要点 |
|---|-----|------|------|--------|---------|------|---------|
| 1 | https://toutiao.com/x1 | 公司致歉信 | 公司公告 | 高 | 多方证实 | 支持 | 440签约 |
| 2 | https://chinanews.com/x2 | 人社局通报 | 政府新闻 | 高 | 多方证实 | 中立 | 简单生硬 |
| 3 | https://inewsweek.cn/x3 | 律师观点 | 权威媒体 | 中 | 单一来源 | 质疑 | 程序违法 |

## 附录：拒收与跳过清单（审计链，v2.5.0 起必填）

### A.1 搜索阶段拒收（rejected）

| 标题 | URL | 拒收原因 |
|------|-----|---------|
| 营销号爆文 | https://farm.com/1 | 内容农场 |

### A.3 精选阶段落选（unselected）

| 标题 | URL | 落选原因 |
|------|-----|---------|
| 旧闻回顾 | https://old.com/9 | 精选上限 80 条截断 |
"""


class TestParseMaterials(unittest.TestCase):
    def test_parse_six_chapters_materials(self):
        m = bm.parse_materials(REPORT_SAMPLE)
        self.assertEqual(len(m), 3)
        self.assertEqual(m[0]["url"], "https://toutiao.com/x1")
        self.assertEqual(m[0]["authority"], "高")
        self.assertEqual(m[0]["stance"], "支持")
        self.assertEqual(m[2]["stance"], "质疑")


class TestParseDisputes(unittest.TestCase):
    def test_parse_disputes(self):
        d = bm.parse_disputes(REPORT_SAMPLE)
        self.assertEqual(len(d), 2)
        self.assertEqual(d[0]["claim_a"], "公司：协商解除")
        self.assertEqual(d[0]["url_b"], "https://b.com")
        self.assertIn("可裁决", d[0]["resolvable"])
        self.assertEqual(d[1]["resolvable"], "未决")


class TestParseAngles(unittest.TestCase):
    def test_parse_angles(self):
        a = bm.parse_angles(REPORT_SAMPLE)
        self.assertEqual(len(a), 2)
        self.assertEqual(a[0]["label"], "跨境ESG合规")
        self.assertEqual(a[0]["type"], "政策/合规")
        self.assertEqual(a[0]["url"], "https://e.com")


class TestParseAuditAppendix(unittest.TestCase):
    def test_parse_appendix(self):
        audit = bm.parse_audit_appendix(REPORT_SAMPLE)
        self.assertEqual(len(audit["rejected"]), 1)
        self.assertEqual(audit["rejected"][0]["reason"], "内容农场")
        self.assertEqual(len(audit["unselected"]), 1)
        # A.2 缺席 → 空列表 + 缺章警告
        self.assertEqual(audit["skipped"], [])
        self.assertIn("A.2", audit["missing_sections"])


class TestBuildManifest(unittest.TestCase):
    def test_full_manifest(self):
        mf = bm.build_manifest(
            REPORT_SAMPLE,
            {"overall": 85.0, "D7_历史脉络": 45.0},
            audit={"rejected": [], "skipped": [], "invalid": [],
                   "unselected": [{"title": "t", "url": "https://old.com/9", "reason": "截断"}]},
            topic_id="T-2026-009",
            report_url="https://la9zp1rfvv9.feishu.cn/docx/X",
        )
        self.assertEqual(mf["topic_id"], "T-2026-009")
        self.assertEqual(mf["report_url"], "https://la9zp1rfvv9.feishu.cn/docx/X")
        self.assertEqual(mf["skill_version"], "2.6.0")
        self.assertEqual(len(mf["materials"]), 3)
        self.assertEqual(len(mf["disputes"]), 2)
        self.assertEqual(len(mf["angles"]), 2)
        self.assertEqual(mf["completeness"]["overall"], 85.0)
        # 附录审计链优先于传入的 score audit（设计优先级）
        self.assertEqual(mf["audit"]["unselected"][0]["reason"], "精选上限 80 条截断")

    def test_missing_appendix_graceful(self):
        report_no_audit = REPORT_SAMPLE.split("## 附录")[0]
        mf = bm.build_manifest(report_no_audit, {"overall": 80.0},
                               audit=None, topic_id="T-1", report_url="u")
        self.assertTrue(any("missing_audit" in w for w in mf["warnings"]))


if __name__ == "__main__":
    unittest.main()
