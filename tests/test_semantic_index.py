import unittest

from suda_ir.data.storage import load_jsonl
from suda_ir.ir.semantic_index import SemanticIndex


class SemanticIndexTests(unittest.TestCase):
    def test_hashing_backend_search_smoke(self) -> None:
        docs = load_jsonl("data/sample/teachers.jsonl")
        index = SemanticIndex(docs, backend="hashing")
        results = index.search("自然语言处理", top_k=3)
        self.assertTrue(results)
        self.assertLessEqual(len(results), 3)
        self.assertTrue(all(result.doc.doc_id for result in results))


if __name__ == "__main__":
    unittest.main()
