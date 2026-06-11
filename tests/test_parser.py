import unittest

from suda_ir.crawler.parser import is_probable_teacher_page, parse_teacher_page


class ParserTests(unittest.TestCase):
    def test_parse_template_teacher_page(self) -> None:
        html = """
        <html><body>
        <h1>曹敏 副教授</h1>
        <p>计算机科学与技术学院（软件学院）</p>
        <h3>个人资料</h3>
        <p>直属机构：计算机科学与技术学院（软件学院）</p>
        <p>电子邮箱：mcao@suda.edu.cn</p>
        <h3>个人简介</h3>
        <p>曹敏，苏州大学副教授，研究方向为视觉-语言多模态学习。</p>
        <h3>研究领域</h3>
        <p>视觉-语言跨模态学习、具身智能</p>
        </body></html>
        """
        doc = parse_teacher_page(html, url="https://web.suda.edu.cn/caomin/")
        self.assertEqual(doc.name, "曹敏")
        self.assertIn("计算机科学与技术学院", doc.college)
        self.assertIn("副教授", doc.title)
        self.assertIn("跨模态", doc.research)
        self.assertIn("个人资料", doc.extra["sections"])
        self.assertIn("研究领域", doc.extra["sections"])
        self.assertIn("mcao@suda.edu.cn", doc.content)

    def test_parse_free_form_teacher_page(self) -> None:
        html = """
        <html><body>
        <h2>周国栋的个人主页</h2>
        <p>苏州大学特聘教授，博士生导师</p>
        <p>计算机科学与技术学院</p>
        <p>电话: 0512-65214851</p>
        <p>电邮: gdzhou [at] suda.edu.cn</p>
        <p>研究方向：自然语言处理、信息抽取、统计机器翻译、机器学习等。</p>
        <p>学术论文：近5年来发表国际著名期刊和会议论文80余篇。</p>
        </body></html>
        """
        doc = parse_teacher_page(html, url="https://web.suda.edu.cn/gdzhou/")
        self.assertEqual(doc.name, "周国栋")
        self.assertIn("特聘教授", doc.title)
        self.assertIn("自然语言处理", doc.research)
        self.assertIn("论文80余篇", doc.papers)
        self.assertIn("0512-65214851", doc.content)
        self.assertIn("gdzhou@suda.edu.cn", doc.content)

    def test_teacher_page_filter(self) -> None:
        self.assertTrue(is_probable_teacher_page("教师个人主页\n个人资料\n个人简介\n研究领域\n很多正文"))
        self.assertTrue(
            is_probable_teacher_page(
                "Ning Chen's homepage\nBiography\nResearch Interest\nPublications\nSchool of Computer Science"
            )
        )
        self.assertTrue(
            is_probable_teacher_page(
                "HomePage of LI Junhui\n李军辉\n教授\n苏州大学/计算机科学与技术学院/自然语言处理实验室\n研究兴趣\n机器翻译\n论文发表"
            )
        )
        self.assertTrue(
            is_probable_teacher_page(
                "Huanfei Ma's Homepage\n马欢飞\n数学科学学院\n江苏省应用数学（苏州大学）中心\n履历\n教学\n研究兴趣\n论文与著作"
            )
        )
        self.assertTrue(
            is_probable_teacher_page(
                "Research Homepage\n张三\n物理科学与技术学院\nSoochow University\n研究兴趣\n论文与著作"
            )
        )
        self.assertTrue(
            is_probable_teacher_page(
                "Research Homepage\n李四\n未来科学与工程学院\nSoochow University\n研究兴趣\n论文与著作"
            )
        )
        self.assertFalse(is_probable_teacher_page("学院列表\n学院 部门\n访问数据：1000"))
        self.assertFalse(is_probable_teacher_page("error\n正在同步中，请稍后再试……"))


if __name__ == "__main__":
    unittest.main()
