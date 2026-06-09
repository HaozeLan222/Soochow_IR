import unittest

from suda_ir.data.storage import load_jsonl
from suda_ir.ir.searcher import TutorSearcher


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        docs = load_jsonl("data/sample/teachers.jsonl")
        self.searcher = TutorSearcher(docs)

    def test_exact_name_search(self) -> None:
        results = self.searcher.search("周国栋", field="name")
        self.assertTrue(results)
        self.assertEqual(results[0].doc.name, "周国栋")

    def test_research_search(self) -> None:
        results = self.searcher.search("自然语言处理")
        self.assertTrue(results)
        self.assertEqual(results[0].doc.name, "周国栋")

    def test_college_filter(self) -> None:
        results = self.searcher.search("计算机", field="college")
        self.assertGreaterEqual(len(results), 2)

    def test_optimized_query_expansion(self) -> None:
        searcher = TutorSearcher(load_jsonl("data/sample/teachers.jsonl"), mode="optimized")
        results = searcher.search("NLP")
        self.assertTrue(results)
        self.assertEqual(results[0].doc.name, "周国栋")

    def test_optimized_fuzzy_name_search(self) -> None:
        searcher = TutorSearcher(load_jsonl("data/sample/teachers.jsonl"), mode="optimized")
        results = searcher.search("周国东", field="name")
        self.assertTrue(results)
        self.assertEqual(results[0].doc.name, "周国栋")


if __name__ == "__main__":
    unittest.main()

