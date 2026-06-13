# 检索优化实验记录

> 历史过程记录：本文保留早期实验设计与中间指标，当前权威 IR 实现、消融结果和运行命令以 `../ir_model_handoff.md` 为准。

## 查询集合

| 编号 | 查询 | 查询意图 | 期望结果 |
|---|---|---|---|
| Q1 | 自然语言处理 | 研究方向检索 | NLP、文本挖掘、机器翻译相关导师 |
| Q2 | 周国栋 | 姓名精确检索 | 返回指定导师 |
| Q3 | 知识图谱 | 研究方向检索 | 知识表示、图数据、智能问答相关导师 |
| Q4 | NLP | 英文缩写/同义表达 | 自然语言处理相关导师 |
| Q5 | 周国东 | 姓名错别字 | 模糊召回周国栋 |
| Q6 | 问答系统 | 相关概念查询 | 智能问答、知识图谱相关导师 |

当前样例查询集保存在：

```text
data/sample/eval_queries.jsonl
```

真实数据评测集已建立在：

```text
data/processed/handoff/eval_queries.real.jsonl
```

该文件包含 10 个查询，并使用真实教师 `doc_id` 标注相关文档。

## 基础系统 vs 优化系统

| 查询 | 基础系统 Top-5 | 优化系统 Top-5 | 现象分析 |
|---|---|---|---|
| 自然语言处理 | 贡正仙、龚晨、王中卿、陈文亮、钱忠 | 龚晨、周国栋、王红玲、贡正仙、李培峰 | 两套系统都能召回 NLP 导师；优化系统通过字段级 BM25 和扩展词更突出“中文信息处理、机器翻译、信息抽取”等相关导师。 |
| NLP | 梁小波、陈文亮、周国栋、李正华、王红玲 | 周国栋、王红玲、龚晨、贡正仙、陈文亮 | 基础系统主要依赖英文 token 偶然匹配；优化系统将 NLP 扩展到自然语言处理、机器翻译、信息抽取等，Top-5 更集中。 |
| 周国东 | 无结果 | 周国栋 | 基础姓名检索只支持精确/包含匹配；优化系统使用模糊姓名检索，可以纠正常见错别字。 |
| 问答系统 | 李明翰、张得天、彭涛、陈文亮、吴颖文 | 吴颖文、陈文亮、周夏冰、李培峰、吴庭芳 | 优化系统把“问答系统”和智能问答、知识图谱、自然语言处理关联，能召回更多语义相关导师。 |

## 指标

| 系统 | Precision@5 | MRR | 平均查询时间 |
|---|---:|---:|---:|
| 基础 BM25 | 0.5400 | 0.8500 | 1.65 ms |
| 优化系统 | 0.6400 | 1.0000 | 39.67 ms |

上述结果基于真实 5 学院清洗数据：

```text
data/processed/handoff/handoff_teachers.clean.jsonl
```

评测查询集为：

```text
data/processed/handoff/eval_queries.real.jsonl
```

该查询集包含 10 个查询，覆盖自然语言处理、NLP 缩写、姓名错别字、知识图谱、智能问答、医学图像、组合优化、太阳能电池、光伏材料等场景。

运行方式：

```bash
python scripts/evaluate_search.py --data data/sample/teachers.jsonl --queries data/sample/eval_queries.jsonl --top-k 5
```

真实数据评测时：

```bash
python scripts/evaluate_search.py --data data/processed/handoff/handoff_teachers.clean.jsonl --queries data/processed/handoff/eval_queries.real.jsonl --top-k 5
```

## 当前优化点

1. 字段级 BM25：分别计算姓名、研究方向、论文、简介、学院等字段的 BM25 分数，再按字段权重融合，避免用重复 token 模拟字段权重。
2. 查询扩展：对常见导师检索领域词做同义词扩展，例如 `NLP -> 自然语言处理、机器翻译、信息抽取、文本挖掘`。
3. 模糊姓名检索：使用 `rapidfuzz`，未安装时回退到 Python 标准库相似度，支持姓名错别字召回。
