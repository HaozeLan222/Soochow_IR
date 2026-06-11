import unittest

from suda_ir.ir.query_intent import analyze_query
from suda_ir.ir.semantic_gate import should_use_semantic


class SemanticGateTests(unittest.TestCase):
    def test_does_not_trigger_for_short_research_keyword(self) -> None:
        intent = analyze_query("自然语言处理")
        self.assertFalse(should_use_semantic("自然语言处理", intent))

    def test_does_not_trigger_for_paper_query(self) -> None:
        query = "ACL 机器翻译论文"
        intent = analyze_query(query)
        self.assertFalse(should_use_semantic(query, intent))

    def test_does_not_trigger_for_paper_soft_preference(self) -> None:
        query = "纳米学院 论文比较多的柔性传感器老师"
        intent = analyze_query(query)
        self.assertFalse(should_use_semantic(query, intent))

    def test_triggers_for_semantic_rewrite(self) -> None:
        query = "研究人类语言理解和文本分析的老师"
        intent = analyze_query(query)
        self.assertTrue(should_use_semantic(query, intent))

    def test_does_not_trigger_for_direct_domain_research_query(self) -> None:
        query = "研究智能问答和知识表示的老师"
        intent = analyze_query(query)
        self.assertFalse(should_use_semantic(query, intent))

    def test_does_not_trigger_for_direct_domain_colloquial_query(self) -> None:
        query = "有没有老师研究机器翻译和跨语言处理"
        intent = analyze_query(query)
        self.assertFalse(should_use_semantic(query, intent))


if __name__ == "__main__":
    unittest.main()
