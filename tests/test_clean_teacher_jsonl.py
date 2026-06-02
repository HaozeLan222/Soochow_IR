import unittest

from scripts.clean_teacher_jsonl import clean_content, clean_doc, clean_field_text
from suda_ir.models import TeacherDoc


class CleanTeacherJsonlTests(unittest.TestCase):
    def test_clean_content_strips_nav_and_footer(self) -> None:
        text = """
        教师个人主页
        返回首页
        欢迎登录
        张三
        副教授
        研究方向：自然语言处理
        Copyright 苏州大学 2019, All Rights Reserved
        推荐使用IE8.0以上
        """
        cleaned = clean_content(text)
        self.assertNotIn("返回首页", cleaned)
        self.assertNotIn("Copyright", cleaned)
        self.assertIn("张三", cleaned)
        self.assertIn("研究方向：自然语言处理", cleaned)

    def test_clean_doc_infers_title_and_trims_field_noise(self) -> None:
        doc = TeacherDoc(
            doc_id="1",
            name="张三",
            college="计算机科学与技术学院",
            title="",
            research="自然语言处理\n基本信息\n张三\n职称：副教授",
            papers="软件著作\n专利",
            profile="张三，副教授，研究方向为信息检索。\n社会职务\n社会职务：",
            content="张三\n副教授\n研究方向：信息检索\nCopyright 苏州大学 2019, All Rights Reserved",
            url="https://example.com",
            final_url="https://example.com",
            extra={"sections": {}},
        )

        cleaned = clean_doc(doc)
        self.assertEqual(cleaned.title, "副教授")
        self.assertEqual(cleaned.research, "自然语言处理")
        self.assertEqual(cleaned.papers, "")
        self.assertEqual(cleaned.profile, "张三，副教授，研究方向为信息检索。")
        self.assertIn("计算机科学与技术学院\n\n张三\n\n副教授", cleaned.content)
        self.assertIn("个人简介\n张三，副教授，研究方向为信息检索。", cleaned.content)
        self.assertNotIn("Copyright", cleaned.content)
        self.assertEqual(cleaned.extra["clean_quality"], "high")

    def test_clean_field_text_compacts_broken_layout(self) -> None:
        text = (
            "主要研究方向为基于溶液法制程的新型光伏材料与器件：\n"
            "1.\n"
            "有机太阳能电池\n"
            ":\n"
            "新型高分子材料设计、太阳能电池应用及机理研究；\n"
            "2.\n"
            "有机\n"
            "-\n"
            "无机杂化光电器件\n"
        )
        cleaned = clean_field_text(text, "research")
        self.assertIn("1. 有机太阳能电池：新型高分子材料设计", cleaned)
        self.assertIn("2. 有机-无机杂化光电器件", cleaned)

    def test_clean_field_text_compacts_bracketed_numbering(self) -> None:
        text = "（\n1\n）固体功能\n材料的合成与表征"
        cleaned = clean_field_text(text, "research")
        self.assertEqual(cleaned, "（1）固体功能材料的合成与表征")

    def test_clean_field_text_collapses_short_bullet_research_list(self) -> None:
        text = "1.\n柔性能量收集材料及器件\n2.\n微纳传感材料与器件\n3.\n智能传感器件与自驱动系统"
        cleaned = clean_field_text(text, "research")
        self.assertEqual(cleaned, "1. 柔性能量收集材料及器件；2. 微纳传感材料与器件；3. 智能传感器件与自驱动系统")

    def test_clean_field_text_normalizes_profile_dates(self) -> None:
        text = "袁建宇 (Yuan Jianyu)2021年8月-至今,苏州大学2016年9月-2021年7月,苏州大学2011年9月\n-2016年6月,苏州大学Google Scholar：https://x"
        cleaned = clean_field_text(text, "profile")
        self.assertIn("\n2021年8月-至今", cleaned)
        self.assertIn("\n2016年9月-2021年7月", cleaned)
        self.assertIn("\n2011年9月-2016年6月", cleaned)
        self.assertIn("\nGoogle Scholar：https://x", cleaned)

    def test_clean_field_text_normalizes_papers_broken_tokens(self) -> None:
        text = "120余篇，H\n-index： 68，i10-index： 135\n10. 0以上47篇\nhttps://example.com/eScience青年编委\n1\n0、 Paper"
        cleaned = clean_field_text(text, "papers")
        self.assertIn("H-index： 68", cleaned)
        self.assertIn("10.0以上47篇", cleaned)
        self.assertIn("https://example.com/eScience\n青年编委", cleaned)
        self.assertIn("10、 Paper", cleaned)

    def test_clean_content_strips_nav_block_and_normalizes_text(self) -> None:
        text = (
            "数学科学学院\n"
            "杨大伟\n"
            "教授\n"
            "个人资料\n"
            "个人概况\n"
            "研究领域\n"
            "开授课程\n"
            "科研项目\n"
            "论文\n"
            "个人简介：\n"
            "此板块暂作杨大伟承担的科研项目NSFC\n"
            "***\n"
            "的成果展示部分。"
        )
        cleaned = clean_content(text)
        self.assertNotIn("个人概况\n研究领域\n开授课程\n科研项目\n论文", cleaned)
        self.assertIn("个人简介：", cleaned)
        self.assertIn("NSFC\n***\n的成果展示部分。", cleaned)


if __name__ == "__main__":
    unittest.main()
