# 检索算法相关工作与本项目映射

## 适合作业落地的研究方向

### 1. 查询扩展

Query2doc 使用大语言模型为短查询生成伪文档，再把伪文档作为扩展内容加入检索。论文报告其方法可提升 BM25 在 MS-MARCO、TREC DL 等数据集上的效果，且不需要微调模型。

本项目当前先实现轻量版本：用领域词典扩展导师检索常见术语，例如 `NLP -> 自然语言处理、机器翻译、信息抽取、文本挖掘`。后续如果接入 DeepSeek/Qwen，可以把词典扩展升级为 LLM 生成伪文档。

参考：

- Query2doc: Query Expansion with Large Language Models, EMNLP 2023. https://arxiv.org/abs/2303.07678
- Query Expansion by Prompting Large Language Models, 2023. https://arxiv.org/abs/2305.03653

### 2. 零样本稠密检索

HyDE 先让语言模型根据查询生成一个假想相关文档，再用向量模型检索真实文档。它适合没有人工相关性标注的场景。

本项目后续可扩展：对“自然语言处理方向”生成一段伪导师研究简介，再用中文 embedding 检索教师主页。由于当前课程作业规模较小，暂未默认引入大模型和向量库。

参考：

- Precise Zero-Shot Dense Retrieval without Relevance Labels, ACL 2023. https://arxiv.org/abs/2212.10496

### 3. 混合检索

BGE-M3 支持 dense、sparse、multi-vector 多种检索能力，并覆盖多语言文本。对于中文导师主页，混合检索可以兼顾关键词、姓名、论文题名和语义相似度。

本项目当前实现了字段级 BM25、查询扩展和模糊匹配；后续可加 `bge-m3` 向量召回，并用 RRF 或加权分数融合 BM25 与向量结果。

参考：

- BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation, 2024. https://arxiv.org/abs/2402.03216
- BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models, 2021. https://arxiv.org/abs/2104.08663

### 4. 神经稀疏检索

SPLADE 把神经模型的词项扩展能力和倒排索引结合起来，效果强且可解释，但训练和部署成本高。

本项目可在报告中作为高级相关工作介绍，不建议作为主实现。

参考：

- SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking, SIGIR 2021. https://arxiv.org/abs/2107.05720
- SPLADE v2, 2021. https://arxiv.org/abs/2109.10086

### 5. LLM 重排序

RankGPT/RankLLM 一类工作使用大语言模型对候选文档列表重新排序。适合二阶段检索：先由 BM25 或 hybrid 检索召回 Top-20，再由 LLM 判断相关性。

本项目后续可选实现：把优化检索 Top-10 的导师姓名、研究方向、论文摘要交给 DeepSeek/Qwen 打分，输出最终排序和解释。

参考：

- Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents, 2023. https://arxiv.org/abs/2304.09542
- RankZephyr: Effective and Robust Zero-Shot Listwise Reranking is a Breeze, 2023. https://arxiv.org/abs/2312.02724
- RankLLM: A Python Package for Reranking with Large Language Models, 2025. https://arxiv.org/abs/2505.19284

## 当前已实现映射

| 论文方向 | 本项目实现 | 位置 |
|---|---|---|
| 字段级排序 | 字段 BM25 分别计分后融合 | `suda_ir/ir/fielded_index.py` |
| 查询扩展 | 导师领域词典扩展 | `suda_ir/ir/query_expansion.py` |
| 模糊检索 | 姓名和字段候选短语相似度 | `suda_ir/ir/fuzzy.py` |
| 对比评测 | Baseline vs Optimized，Precision@K、MRR、耗时 | `scripts/evaluate_search.py` |

## 建议报告表述

本项目的优化系统采用轻量多阶段检索框架：第一阶段使用字段级 BM25 完成可解释关键词召回；第二阶段引入查询扩展缓解用户短查询和领域术语不一致问题；第三阶段使用模糊匹配提升姓名查询容错性。该设计借鉴了 Query2doc/HyDE 的查询增强思想和混合检索系统的多信号融合思想，但为了适配课程项目规模，当前采用可离线运行、无需训练的实现。

