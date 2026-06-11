# IR 系统优化方案讨论稿

更新时间：2026-06-09

## 1. 当前项目状态

当前项目已经具备一个可运行的垂直 IR 系统雏形：

- 已爬取并清洗 5 个学院教师主页数据。
- 当前统一检索输入文件为：

```text
data/processed/handoff/handoff_teachers.clean.jsonl
```

- 当前数据规模：

```text
教师文档：283 条
学院数：5
clean_quality=high：199
clean_quality=medium：80
clean_quality=low：4
```

- 当前 baseline 检索方法：
  - 中文分词优先使用 `jieba`。
  - 无 `jieba` 时使用字符 n-gram 兜底。
  - BM25 排序。
  - 字段加权：`name > research > papers > title > profile > college/content`。
  - 支持姓名精确搜索。
  - 支持学院字段过滤。
  - 支持 CLI 和基础 Streamlit 界面。

当前系统已经可以作为“基础 IR 系统”，但还缺少正式评测和优化系统对比。

## 2. 老师 PPT 中的关键要求

老师 PPT 对本项目的核心要求可以归纳为：

### 2.1 基础要求

实现一个面向苏州大学若干学院导师信息的垂直检索系统。

必须支持：

- 查询研究方向，例如“自然语言处理方向”，返回相关导师。
- 查询教师姓名，例如“周国栋”，精确返回该教师。
- 支持其他常用查询，例如论文标题、关键词、研究领域。
- 爬取至少 5 个学院教师信息，至少包含计算机学院。
- 基于爬取数据构建排序式 IR 系统。
- 处理教师隐私信息，例如电话用 `***` 替换。

### 2.2 升级要求

在基础 IR 系统上构建更先进的 IR 系统。

至少完成 2 项优化，并且报告/展示中要体现优化效果：

- 同一个查询在 baseline 和 optimized 系统中的结果对比。
- 用指标证明优化是否有效。
- 报告体现分工和每位同学贡献。
- 需要 PPT 展示。

### 2.3 PPT 给出的可选优化方向

老师明确提到的优化方向包括：

1. 图形化查询界面。
2. 多次迭代查询、模糊查询。
3. 机器学习或深度学习相关度计算，例如 SVMrank、BERT embedding。
4. 大语言模型优化排序，例如 DeepSeek/Qwen。
5. 其他优化：拼写检查、压缩倒排索引、缩短查询时间、垃圾信息过滤等。

## 3. 为什么要做评测 query 和 evaluate_search.py

“写 15-20 个评测 query + 做 `evaluate_search.py`”的目的，就是为了量化对比 baseline 和优化模型。

如果没有评测，只能说“看起来更好”。有评测后，可以写成：

```text
Baseline BM25: Precision@5 = 0.xx, MRR = 0.xx
Optimized Hybrid: Precision@5 = 0.yy, MRR = 0.yy
```

这样报告里就能回答老师 PPT 的要求：

> 优化目标是否真正实现？

建议建立：

```text
data/eval/queries.jsonl
scripts/evaluate_search.py
```

评测指标：

- `Precision@5`：Top-5 中有多少是相关教师。
- `MRR`：第一个相关教师出现得越靠前越好。
- `Recall@K`：可选，适合多相关教师查询。
- 查询耗时：用于说明效率。

推荐查询类型：

```text
姓名精确查询：周国栋、马欢飞、李领治
研究方向查询：自然语言处理、机器学习、图像处理、量子材料、纳米材料
学院 + 方向查询：数学科学学院 动力系统、物理科学与技术学院 凝聚态
论文/成果查询：机器翻译、知识图谱、光伏材料、偏微分方程
模糊/近似查询：自然语言、机器翻译方向、做推荐系统的老师
```

## 4. 对截图方案的评价

截图中同学提出的方案是：

```text
面向导师信息垂直检索的自适应混合检索与查询扩展优化
```

分三层：

1. Baseline：BM25 字段加权。
2. 优化一：自适应 Hybrid Retrieval。
3. 优化二：查询扩展。
4. 可选优化三：Top-K 重排序。

这个方向是可以参考的，而且和老师 PPT 很契合。

优点：

- 有明确 baseline 和优化系统。
- 覆盖 PPT 中的模糊查询、深度学习相关度、大模型优化排序。
- 能做可量化对比：Precision@5、MRR、耗时。
- 对导师检索场景很贴合：姓名、研究方向、论文标题本来就是不同查询意图。

需要注意：

- 不要一次做太大，否则容易变成“全都写了但都不稳定”。
- BGE-M3、BGE reranker、DeepSeek/Qwen 都可能涉及模型下载、API、网络和运行成本。
- 课程项目里最稳的路线是：先做可解释优化，再做可选语义优化。

建议采用这个方案的“分层版本”：

```text
必做：
Baseline BM25
优化一：查询意图识别 + 字段自适应加权 + fuzzy 姓名匹配
优化二：领域词典查询扩展

选做：
Hybrid dense retrieval
Top-K rerank
LLM query expansion / rerank
```

## 5. 推荐最终方案：自适应混合检索框架

建议题目：

```text
面向苏州大学导师信息的垂直检索系统及自适应查询优化研究
```

不要把优化设计成“为了满足至少 2 项优化而临时加两个功能”。更 solid 的做法，是把系统设计成一个完整的分层检索框架，每一层解决导师信息检索中的一个真实问题：

```text
用户查询不规范 -> 查询理解与标准化
字段重要性不同 -> 字段级检索与自适应权重
字面匹配召回不足 -> 查询扩展与模糊匹配
语义相近但词不相同 -> 语义召回或重排序
优化是否有效 -> 统一评测集和指标对比
```

推荐整体结构：

```text
数据层：教师主页 HTML -> JSONL -> cleaned JSONL
Baseline 层：BM25 + 固定字段加权
查询理解层：查询类型识别 + 学院/职称/姓名/研究方向解析
召回优化层：字段级 BM25 + 模糊匹配 + 查询扩展
融合排序层：多路召回结果融合，建议使用 RRF 或加权融合
语义增强层：可选 embedding 召回或 Top-K rerank
评测层：Precision@5、MRR、耗时
展示层：Streamlit 前端
```

报告中的核心问题可以写成：

```text
如何针对导师主页这种半结构化、字段噪声较多、查询意图多样的垂直检索场景，
设计一个比基础 BM25 更稳定的自适应混合检索系统？
```

## 6. 优化点清单

### 6.1 已完成或接近完成

#### 数据清洗优化

状态：已基本完成。

内容：

- 网页解析。
- 电话/邮箱脱敏。
- 空壳页、跨学院页过滤。
- `clean_quality` 标注。
- 统一 JSONL schema。

可在报告中作为数据预处理优化说明。

#### 图形化查询界面

状态：已有基础 Streamlit，前端同学正在继续做。

建议增强：

- 默认加载 `handoff_teachers.clean.jsonl`。
- 学院筛选。
- 职称筛选。
- Top-K 设置。
- `clean_quality` 筛选。
- 结果卡片展示。
- 命中字段高亮。
- 教师主页链接。

### 6.2 推荐作为主线完成的优化

这一部分建议作为正式优化系统的核心，不要只挑两个零散功能。主线可以命名为：

```text
Adaptive Hybrid Retrieval
```

它由五个互相配合的模块组成。

#### 优化一：查询意图识别与自适应字段权重

动机：

不同查询类型应该走不同策略：

- “周国栋”更像姓名查询。
- “自然语言处理”更像研究方向查询。
- “机器翻译论文”更像论文/成果查询。
- “数学科学学院 动力系统”包含学院过滤和研究方向。

实现思路：

```text
1. 判断 query 是否匹配教师姓名。
2. 判断 query 是否包含学院名或学院关键词。
3. 判断 query 是否包含“论文、发表、成果”等词。
4. 判断 query 是否包含“教授、副教授、讲师”等职称。
5. 根据意图调整字段权重。
```

示例：

```text
姓名查询：name 权重最高，启用 exact + fuzzy。
研究方向查询：research/content 权重最高。
论文查询：papers 权重提高。
学院查询：先 filter college，再排序。
```

预期效果：

- 姓名查询更稳定。
- 学院 + 方向组合查询更准。
- 论文相关查询不被 profile/content 噪声淹没。

#### 优化二：字段级 BM25，而不是简单重复 token 加权

当前 baseline 的字段加权方式，是把高权重字段的 token 重复多次。这能工作，但解释性和可控性一般。

更 solid 的做法是为每个字段分别计算分数：

```text
score(doc, query)
  = w_name * BM25_name
  + w_research * BM25_research
  + w_papers * BM25_papers
  + w_profile * BM25_profile
  + w_content * BM25_content
```

再结合查询意图动态调整权重：

```text
姓名查询：提高 name
研究方向查询：提高 research/content
论文查询：提高 papers
学院查询：先过滤 college，再排序
```

优点：

- 比重复 token 更可解释。
- 方便在报告中展示字段权重表。
- 方便做消融实验，例如“去掉 research boost 后效果下降”。

#### 优化三：模糊匹配

动机：

用户可能输入不完整或略有误差：

```text
自然语言 -> 自然语言处理
周国东 -> 周国栋
机器翻译方向 -> 机器翻译
```

实现方式：

- 使用 `rapidfuzz`。
- 对姓名做 fuzzy ratio。
- 对 query 和字段关键词做部分匹配。

建议优先应用于：

- `name`
- `research`
- `title`
- 学院简称

预期效果：

- 提升短查询、错别字查询、简称查询的召回率。

#### 优化四：领域词典查询扩展

动机：

用户输入的词和教师主页里的词不一定完全一样。

示例词典：

```python
{
  "NLP": ["自然语言处理", "机器翻译", "文本挖掘", "信息抽取", "中文信息处理"],
  "机器学习": ["深度学习", "人工智能", "神经网络", "数据挖掘"],
  "CV": ["计算机视觉", "图像处理", "目标检测", "模式识别"],
  "量子": ["量子材料", "量子信息", "凝聚态物理"],
  "纳米": ["纳米材料", "软物质", "光伏材料", "柔性器件"]
}
```

实现方式：

```text
query -> query + expansion terms
```

或：

```text
原 query 权重 1.0
扩展词权重 0.3-0.5
```

预期效果：

- 提升研究方向查询召回。
- 报告中容易解释。
- 不依赖大模型，稳定可控。

#### 优化五：多路召回融合

当系统同时有以下召回来源时：

```text
name exact/fuzzy
field BM25
expanded query BM25
college/title filter
optional embedding retrieval
```

需要一个融合策略，而不是简单拼接结果。

推荐使用 RRF：

```text
RRF_score(doc) = Σ 1 / (k + rank_i)
```

其中 `rank_i` 是文档在第 i 个召回器中的排名，`k` 常用 60。

优点：

- 不要求不同模型分数在同一量纲。
- 实现简单。
- 很适合把 BM25、fuzzy、embedding 结果融合。
- 报告里容易解释。

### 6.3 更 solid 的实验设计：不是做功能，而是证明系统变强

为了让方案看起来更扎实，建议把优化写成一组递进实验，而不是只写“我们做了两个优化点”。核心思路是：

```text
Baseline 不是对手，而是参照物。
每新增一个模块，都要回答它解决了什么问题、带来了多少指标提升、有没有副作用。
```

推荐设计四个可运行版本：

| 版本 | 名称 | 包含模块 | 用途 |
|---|---|---|---|
| V0 | Baseline BM25 | 当前 BM25 + 固定字段加权 | 课程基础要求和参照组 |
| V1 | Field-aware BM25 | 字段级 BM25 + 查询意图识别 + 动态字段权重 | 证明字段结构被有效利用 |
| V2 | Adaptive Hybrid | V1 + fuzzy matching + 领域词典查询扩展 + RRF 融合 | 作为主要优化系统 |
| V3 | Semantic Enhanced | V2 + embedding 召回或 reranker | 作为高阶加分项，时间不够可以不做 |

这样汇报时不是说“我们优化了 A 和 B”，而是说：

```text
我们从基础 BM25 出发，逐步加入字段感知、查询理解、模糊匹配、查询扩展和多路融合，
并通过统一评测集验证每一层对导师检索效果的贡献。
```

建议做消融实验：

| 对比 | 目的 |
|---|---|
| V0 vs V1 | 验证字段级 BM25 和查询意图识别是否有效 |
| V1 vs V2 | 验证 fuzzy、查询扩展和融合是否提升召回 |
| V2 vs V3 | 验证语义模型是否值得加入 |
| V2 去掉 fuzzy | 看姓名错别字/简称查询是否退化 |
| V2 去掉查询扩展 | 看研究方向查询是否退化 |
| V2 去掉 RRF | 看多路召回是否真的需要融合策略 |

建议把评测 query 分成几类，避免只挑对系统有利的例子：

| 查询类型 | 示例 | 主要考察 |
|---|---|---|
| 姓名精确查询 | 周国栋、李领治、马欢飞 | name exact |
| 姓名模糊查询 | 周国、李领、马欢 | fuzzy |
| 研究方向查询 | 自然语言处理、机器学习、量子材料 | research/content |
| 论文/成果查询 | 机器翻译、知识图谱、光伏材料 | papers/research |
| 学院 + 方向 | 数学科学学院 动力系统、物理学院 凝聚态 | college filter + ranking |
| 口语化查询 | 做推荐系统的老师、研究图像处理的老师 | expansion + semantic |

最终报告里的表格可以这样设计：

| 系统版本 | Precision@5 | MRR | 平均耗时 | 说明 |
|---|---:|---:|---:|---|
| V0 Baseline BM25 | 待跑 | 待跑 | 待跑 | 当前系统 |
| V1 Field-aware BM25 | 待跑 | 待跑 | 待跑 | 字段级权重 |
| V2 Adaptive Hybrid | 待跑 | 待跑 | 待跑 | 主方案 |
| V3 Semantic Enhanced | 待跑 | 待跑 | 待跑 | 可选增强 |

这会比“至少两个优化点”更有说服力，因为它体现了：

- 有明确问题定义。
- 有 baseline。
- 有主方案。
- 有消融实验。
- 有指标。
- 有可解释的失败分析。

### 6.4 可选高阶优化

#### Hybrid Retrieval：BM25 + Dense Embedding

动机：

BM25 对字面匹配强，embedding 对语义相似更强。

推荐结构：

```text
BM25 召回 Top-50
Embedding 召回 Top-50
RRF 或加权融合
输出 Top-20
```

融合方式：

```text
RRF: score += 1 / (k + rank)
```

适合使用：

- BGE-small-zh
- BGE-M3
- text2vec

风险：

- 需要下载模型。
- 运行环境可能慢。
- 需要缓存向量。

建议作为选做，不要作为唯一优化。

#### Top-K 重排序

动机：

先用 BM25/Hybrid 找候选，再用更强模型判断相关性。

可选方式：

```text
BGE reranker
LLM prompt 打分
规则 rerank
```

建议：

- 如果使用 LLM，只 rerank Top-10 或 Top-20。
- 报告中说明成本和耗时。
- 和 baseline 对比 Precision@5、MRR、耗时。

风险：

- API 费用。
- 网络不稳定。
- 结果可能不可复现。

#### LLM 查询扩展 / HyDE

截图中提到的 Query2doc/HyDE 可以作为亮点，但不建议作为主线。

原因：

- 课程项目时间有限。
- LLM 生成内容可能漂移。
- 需要额外评测证明有效。

可作为实验性优化：

```text
原查询：自然语言处理
LLM 扩展：机器翻译、文本生成、信息抽取、语义理解、中文信息处理
再交给 BM25/Hybrid 检索
```

## 7. 建议实现顺序

### 第一阶段：锁定 baseline 和评测标准

目标：

- 用 cleaned JSONL 运行当前 BM25。
- 生成 baseline Top-5。
- 建立评测 query。

交付：

```text
data/eval/queries.jsonl
scripts/evaluate_search.py
docs/experiments.md 更新 baseline 指标
```

### 第二阶段：实现主线优化系统

目标：

- 查询意图识别。
- 字段级 BM25。
- 姓名 fuzzy。
- 学院/职称过滤。
- 领域词典查询扩展。
- RRF 或加权融合。

交付：

```text
suda_ir/ir/query.py
suda_ir/ir/enhanced_searcher.py
suda_ir/ir/expansion.py
suda_ir/ir/fusion.py
```

### 第三阶段：评测对比

目标：

对比：

```text
baseline_bm25
optimized_adaptive_hybrid
optional_hybrid
```

指标：

```text
Precision@5
MRR
平均耗时
```

### 第四阶段：可选语义优化

如果时间够，再做：

- embedding 检索。
- RRF 融合。
- reranker。
- LLM query expansion。

## 8. 推荐组内分工

### 数据/清洗同学

- 维护 `handoff_teachers.clean.jsonl`。
- 检查 low/medium 质量样本。
- 补充数据质量说明。

### Baseline/评测同学

- 写 `data/eval/queries.jsonl`。
- 写 `scripts/evaluate_search.py`。
- 跑 baseline 指标。

### 优化算法同学

- 实现查询意图识别。
- 实现 fuzzy matching。
- 实现查询扩展。
- 可选实现 Hybrid/RRF。

### 前端同学

- 接入 cleaned JSONL。
- 增加学院、职称、质量筛选。
- 展示命中字段和分数。
- 支持 baseline/optimized 切换。

## 9. 推荐落地方案

建议不要在报告里写成“做了两个优化点”。更好的写法是：我们实现了一个完整但可控的 `Adaptive Hybrid Retrieval` 优化系统。

```text
Baseline：当前 BM25 字段加权。
Optimized：Adaptive Hybrid Retrieval。

核心模块：
1. 查询意图识别。
2. 字段级 BM25 与自适应权重。
3. 姓名/关键词 fuzzy matching。
4. 领域词典查询扩展。
5. RRF 或加权融合。

可选增强：
6. embedding 召回。
7. Top-K reranker。
8. LLM 查询扩展或相关度打分。

评测：15-20 个 query，Precision@5 + MRR + 耗时。
展示：Streamlit 支持 baseline/optimized 对比。
```

这个方案不是为了卡“至少 2 项优化”的下限，而是围绕导师信息检索的真实难点形成一条完整优化链路。

## 9.1 推荐汇报口径

建议在报告和 PPT 中这样讲：

```text
我们没有只针对单个模块做局部调参，而是针对导师信息检索的三个主要困难：
1. 查询意图多样；
2. 教师主页字段半结构化且噪声较多；
3. 用户查询词与网页表述不完全一致；

设计了一个自适应混合检索框架。
```

对应关系：

```text
查询意图多样 -> Query Understanding
字段半结构化 -> Field-aware BM25
表述不一致 -> Query Expansion + Fuzzy Matching
多路结果冲突 -> RRF Fusion
优化是否有效 -> Precision@5 / MRR / 耗时评测
```

这样显得方案更扎实，也更像 IR 系统设计。

## 10. 报告中可以强调的创新点

- 面向导师主页的垂直检索，而不是通用搜索。
- 利用教师信息结构进行字段加权。
- 针对姓名、研究方向、论文标题设计不同查询策略。
- 使用领域词典进行可解释查询扩展。
- 使用模糊匹配处理用户输入误差。
- 用 Precision@5、MRR、耗时量化优化效果。
- 可选使用 Hybrid/RRF 或 LLM rerank 作为高级拓展。
