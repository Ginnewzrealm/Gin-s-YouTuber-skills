#!/usr/bin/env python3
"""youtube-skills 总路由核心脚本测试（v0.1.0）"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import yt_core as yc  # noqa: E402


class TestRouteAdvice(unittest.TestCase):
    """状态机 → 路由建议映射：每个池状态必须给出唯一明确的下一步归属。"""

    def test_idea_stage_goes_to_human_gate(self):
        adv = yc.route_advice("阶段一：想法记录", has_materials=False, completeness=0)
        self.assertEqual(adv["skill"], "人（硬闸门①立项）")

    def test_legacy_idea_state_name(self):
        adv = yc.route_advice("想法记录", has_materials=False, completeness=0)
        self.assertEqual(adv["skill"], "人（硬闸门①立项）")

    def test_researching_without_materials(self):
        adv = yc.route_advice("阶段二：资料研究", has_materials=False, completeness=0)
        self.assertEqual(adv["skill"], "yt-ziliao")

    def test_researching_ready_goes_to_fenxi(self):
        adv = yc.route_advice("阶段二：资料研究", has_materials=True, completeness=85)
        self.assertEqual(adv["skill"], "yt-fenxi")

    def test_researching_low_completeness_stays_ziliao(self):
        adv = yc.route_advice("阶段二：资料研究", has_materials=True, completeness=45)
        self.assertEqual(adv["skill"], "yt-ziliao")

    def test_confirmed_goes_to_jiaoben(self):
        adv = yc.route_advice("阶段三：确认选题", has_materials=True, completeness=85)
        self.assertEqual(adv["skill"], "yt-jiaoben")

    def test_production_goes_to_human(self):
        adv = yc.route_advice("阶段四：内容制作", has_materials=True, completeness=85)
        self.assertEqual(adv["skill"], "人（硬闸门③定稿终审）")

    def test_making_state_goes_to_zhizuo(self):
        adv = yc.route_advice("制作中", has_materials=True, completeness=85)
        self.assertEqual(adv["skill"], "yt-zhizuo")

    def test_pending_publish_goes_to_agrici(self):
        adv = yc.route_advice("待发布", has_materials=True, completeness=85)
        self.assertIn("agrici", adv["skill"])

    def test_tuijianqi_goes_to_guanjianci(self):
        adv = yc.route_advice("推荐期", has_materials=True, completeness=85)
        self.assertEqual(adv["skill"], "yt-guanjianci")

    def test_published_placeholder(self):
        adv = yc.route_advice("已发布", has_materials=True, completeness=85)
        self.assertIn("fupan", adv["skill"])
        self.assertIn("待开工", adv["skill"])

    def test_eliminated_is_terminal(self):
        adv = yc.route_advice("已淘汰", has_materials=False, completeness=0)
        self.assertEqual(adv["skill"], "终态（仅档案）")

    def test_every_phase_skill_field_nonempty(self):
        for state in ["阶段一：想法记录", "阶段二：资料研究", "阶段三：确认选题",
                      "阶段四：内容制作", "制作中", "待发布", "已发布", "推荐期", "已淘汰"]:
            adv = yc.route_advice(state, has_materials=True, completeness=85)
            self.assertTrue(adv["skill"], f"{state} 路由为空")
            self.assertTrue(adv["next_action"], f"{state} next_action 为空")


class TestRenderMacro(unittest.TestCase):
    """宏观仪表盘渲染：六阶段齐全、硬闸门标注、当前高亮、淘汰态展示。"""

    def test_seven_phases_and_gates(self):
        out = yc.render_macro("阶段二：资料研究")
        for kw in ["阶段 1/8", "阶段 2/8", "阶段 3/8", "阶段 4/8", "阶段 5/8", "阶段 6/8", "阶段 7/8", "阶段 8/8",
                   "硬闸门", "当前"]:
            self.assertIn(kw, out)

    def test_phase_names_cover_chain(self):
        out = yc.render_macro("阶段一：想法记录")
        for kw in ["选题立项", "资料采集", "选题分析", "脚本制作", "内容制作", "发布包装", "数据复盘", "推荐期优化"]:
            self.assertIn(kw, out)

    def test_eliminated_shown_as_terminal(self):
        self.assertIn("已淘汰", yc.render_macro("已淘汰"))

    def test_done_before_current(self):
        out = yc.render_macro("阶段三：确认选题")
        # 当前阶段之前标 ✓，之后标 待开始；fupan 阶段名自带 [待开工] 占位
        self.assertIn("[✓]", out)
        self.assertIn("[待开始]", out)
        self.assertIn("待开工", out)


class TestWorkspaceConfig(unittest.TestCase):
    """工作区配置：默认值、路径展开、读写回环。"""

    def test_default_config(self):
        cfg = yc.default_config("~/Documents/YouTuber工作流")
        self.assertEqual(cfg["version"], 1)
        self.assertEqual(cfg["dirs"]["reports"], "资料报告")
        self.assertEqual(cfg["dirs"]["cards"], "选题分析卡")
        self.assertEqual(cfg["dirs"]["briefs"], "制作四件套")
        self.assertEqual(cfg["dirs"]["keywords"], "关键词库")
        self.assertTrue(cfg["workspace_root"].startswith("/"))  # ~ 已展开

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "config.json")
            yc.save_config(p, yc.default_config("~/Documents/YouTuber工作流"))
            cfg = yc.load_config(p)
            self.assertEqual(cfg["version"], 1)
            self.assertIn("workspace_root", cfg)

    def test_resolve_dir(self):
        cfg = yc.default_config("~/Documents/YouTuber工作流")
        self.assertEqual(yc.resolve_dir(cfg, "cards"), os.path.expanduser("~/Documents/YouTuber工作流/选题分析卡"))


if __name__ == "__main__":
    unittest.main()
