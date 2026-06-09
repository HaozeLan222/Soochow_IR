import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.parse_handoff_html_to_jsonl import build_documents, raw_filename


class HandoffImportTests(unittest.TestCase):
    def test_build_documents_uses_seed_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "handoff"
            college = "数学科学学院"
            html_dir = root / college
            seed_dir = root / "colleges" / college
            html_dir.mkdir(parents=True)
            seed_dir.mkdir(parents=True)

            url = "https://web.suda.edu.cn/test_teacher/"
            html_name = raw_filename(url)
            html = """
            <html><body>
            <h1>个人概况</h1>
            <h2>教师个人主页</h2>
            <p>姓名：张三</p>
            <p>职称：教授</p>
            <h3>研究领域</h3>
            <p>代数与几何</p>
            </body></html>
            """
            (html_dir / html_name).write_text(html, encoding="utf-8")

            with (seed_dir / "teacher_seeds.csv").open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["college", "name", "url"])
                writer.writeheader()
                writer.writerow({"college": college, "name": "张三", "url": url})

            docs, report = build_documents(root)

            self.assertEqual(len(docs), 1)
            self.assertEqual(len(report), 1)
            doc = docs[0]
            self.assertEqual(doc.name, "张三")
            self.assertEqual(doc.college, college)
            self.assertEqual(doc.url, url)
            self.assertIn("代数与几何", doc.research)
            self.assertEqual(doc.extra["raw_path"], str(html_dir / html_name))
            self.assertEqual(doc.extra["source"], "handoff_html")

    def test_raw_filename_matches_sha1_prefix(self) -> None:
        url = "https://web.suda.edu.cn/chenhangyan/"
        expected = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".html"
        self.assertEqual(raw_filename(url), expected)

    def test_build_documents_accepts_separate_seed_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_root = root / "raw"
            seed_root = root / "seeds" / "colleges"
            college = "物理科学与技术学院"
            html_dir = raw_root / college
            seed_dir = seed_root / college
            html_dir.mkdir(parents=True)
            seed_dir.mkdir(parents=True)

            url = "https://web.suda.edu.cn/physics_test/"
            html_name = raw_filename(url)
            html = """
            <html><body>
            <h2>教师个人主页</h2>
            <p>姓名：李四</p>
            <p>职称：教授</p>
            <h3>研究领域</h3>
            <p>量子材料</p>
            </body></html>
            """
            (html_dir / html_name).write_text(html, encoding="utf-8")

            with (seed_dir / "teacher_seeds.csv").open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["college", "name", "url"])
                writer.writeheader()
                writer.writerow({"college": college, "name": "李四", "url": url})

            docs, report = build_documents(raw_root, seed_root=seed_root)

            self.assertEqual(len(docs), 1)
            self.assertEqual(len(report), 1)
            self.assertEqual(docs[0].name, "李四")
            self.assertEqual(docs[0].college, college)
            self.assertEqual(docs[0].url, url)


if __name__ == "__main__":
    unittest.main()
