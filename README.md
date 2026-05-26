# Soochow IR Tutor Search

苏州大学导师信息垂直检索系统课程项目骨架。

目标是先搭建一个可协作、可扩展、可演示的通用架构：基础版本使用网页爬取、正文解析、隐私脱敏、JSONL 存储、BM25 排序检索；后续可以逐步加入模糊查询、语义向量检索、LLM 重排序和图形界面。

## 项目结构

```text
suda_ir/
  app/                  # 命令行和 Web 界面入口
  crawler/              # 爬虫、跳转处理、HTML 解析
  ir/                   # 分词、索引、排序、搜索
  data/                 # 数据读写工具
data/
  sample/teachers.jsonl # 可直接运行的示例数据
  raw/                  # 原始 HTML，默认不提交
  processed/            # 清洗后的教师数据，默认不提交
tests/                  # 基础单元测试
docs/                   # 报告、分工、实验记录
```

## 快速运行

无需安装额外依赖即可运行示例检索：

```bash
python -m suda_ir.app.cli --data data/sample/teachers.jsonl --query 自然语言处理
python -m suda_ir.app.cli --data data/sample/teachers.jsonl --query 周国栋 --field name
```

运行测试：

```bash
python -m unittest discover -s tests
```

安装推荐依赖后效果更好：

```bash
pip install -r requirements.txt
```

可选 Web 界面：

```bash
streamlit run suda_ir/app/streamlit_app.py
```

## 基础流程

1. 从学院/教师页面爬取 HTML。
2. 保存原始 HTML 和最终 URL，避免跳转或解析失败导致数据丢失。
3. 使用多规则解析抽取姓名、学院、职称、研究方向、论文、简介等字段。
4. 对电话、邮箱等敏感信息脱敏。
5. 将结构化字段和全文正文写入 JSONL。
6. 基于教师文档构建 BM25 索引。
7. 查询时优先处理姓名精确匹配，再进行字段加权全文排序。

## 四人协作建议

| 成员 | 方向 | 主要文件 |
|---|---|---|
| A | 爬虫与数据清洗 | `suda_ir/crawler/`, `suda_ir/data/` |
| B | 基础检索与排序 | `suda_ir/ir/` |
| C | 优化算法与评测 | `docs/experiments.md`, 后续 `suda_ir/ir/semantic.py` |
| D | 界面、报告与展示 | `suda_ir/app/`, `docs/` |

## 后续优化路线

- 模糊查询：`rapidfuzz` 或编辑距离。
- 查询扩展：同义词词表、领域词典。
- 语义向量检索：`sentence-transformers`、`text2vec` 或中文 BGE 模型。
- LLM 重排序：BM25 召回 Top-K 后调用大模型评分。
- 评价指标：Precision@5、MRR、查询耗时。

