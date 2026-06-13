# IR 检索系统技术总结与交接文档

更新时间：2026-06-12

本文档用于交接当前 Soochow_IR 项目中 IR 检索系统的真实实现状态、算法创新点、评测结果、代码入口和后续优化边界。它可以直接作为后续汇报、实验报告和组员继续开发的技术总览。

## 1. 一句话结论

当前项目已经从基础 BM25 检索升级为一个面向导师主页数据的自适应混合检索系统：

```text
baseline BM25
  -> 字段级 BM25
  -> fuzzy 姓名匹配
  -> 领域词典查询扩展
  -> 查询意图识别
  -> 学院别名归一与 hard filter
  -> 动态字段权重
  -> 论文成果类 paper-only RRF
  -> BGE 条件触发语义补充召回（离线评测 + 后端 optimized 可选内部路径）
```

当前主线线上/前端可演示模式是：

```text
基础 BM25 / 优化检索 optimized
```

当前需要特别区分两个入口：

```text
前端/后端演示入口：bm25 / optimized
离线消融评测入口：conditional_semantic
```

其中 `conditional_semantic` 用于离线评测和报告创新点说明；后端演示不新增第三个前端按钮，而是让 `optimized` 在内部按同一套 gate 逻辑触发 BGE 补充召回。当 query 是长自然语言描述、口语化软描述或明显语义改写时，系统额外触发 BGE 向量召回，并与 optimized 结果做加权 RRF 融合；若依赖或模型缓存不可用，则自动回退普通 optimized。

## 2. 当前数据与评测集

### 2.1 检索数据

推荐检索输入文件：

```text
data/processed/handoff/handoff_teachers.clean.jsonl
```

当前本地数据规模：

```text
教师文档：283
学院：5 个
数据来源：5 个学院教师主页 HTML 解析与清洗结果
```

注意：

1. `data/raw/` 和 `data/processed/` 是数据产物，通常不提交 GitHub。
2. 组员需要通过本地生成或压缩包交接获得 `handoff_teachers.clean.jsonl`。
3. 当前清洗口径是保留并规范化官网公开联系方式，不再默认脱敏。测试 `tests/test_parser.py` 已按这个口径更新。

### 2.2 正式主评测集

```text
data/eval/queries.jsonl
data/eval/qrels.jsonl
```

规模：

```text
queries：48
qrels：人工/半人工相关性标注
相关阈值：relevance >= 2
Top-K：5
```

query 类型覆盖：

| 类别 | 目的 |
|---|---|
| `exact_name` | 姓名精确查询 |
| `fuzzy_name` | 姓名错别字/近似查询 |
| `research_direction` | 单研究方向查询 |
| `paper_achievement` | 论文/成果类查询 |
| `college_research` | 学院 + 研究方向硬约束 |
| `title_research` | 学院/职称/方向复合查询 |
| `soft_preference` | 青年老师、成果较多等软偏好 |
| `colloquial_compound` | 口语化复合查询 |

### 2.3 语义泛化补充评测集

```text
data/eval/semantic_generalization_queries.jsonl
data/eval/semantic_generalization_qrels.jsonl
```

规模：

```text
queries：10
qrels：65
```

设计目的：

1. 专门测试“用户不直接输入关键词，而是换一种自然语言说法”的场景。
2. qrels 沿用正式测试集中相近主题 query 的相关教师，避免临时按结果倒推标注。
3. 该子集只用于补充分析语义泛化能力，不替代 48 条正式主评测集。

典型 query：

| query_id | 查询 | 对应主题 |
|---|---|---|
| S001 | 研究人类语言理解和文本分析的老师 | 自然语言处理 |
| S002 | 做跨语言文本分析与翻译技术的导师 | 机器翻译 |
| S005 | 研究非线性系统长期行为的导师 | 动力系统 |
| S008 | 研究文本情感理解和观点分析的老师 | 情感分析 |
| S009 | 纳米学院研究二维材料界面调控的老师 | 二维材料/表界面 |

## 3. 当前代码入口

### 3.1 主 IR 包

| 文件 | 作用 |
|---|---|
| `suda_ir/ir/index.py` | baseline BM25，使用合并字段文本建索引 |
| `suda_ir/ir/fielded_index.py` | 字段级 BM25，支持动态字段权重、扩展词权重、候选文档过滤 |
| `suda_ir/ir/fuzzy.py` | fuzzy 姓名匹配，优先 rapidfuzz，缺依赖时退回 SequenceMatcher |
| `suda_ir/ir/query_expansion.py` | 领域词典扩展，如 NLP、机器翻译、知识图谱、计算机视觉 |
| `suda_ir/ir/query_intent.py` | 查询意图识别、学院别名归一、职称词/论文词识别、动态权重策略 |
| `suda_ir/ir/searcher.py` | CLI/主包搜索入口，支持 baseline 与 optimized |
| `suda_ir/ir/semantic_index.py` | BGE/句向量召回，支持 sentence-transformers 和 hashing 冒烟后端 |
| `suda_ir/ir/semantic_gate.py` | 条件触发语义召回 gate，决定是否启用 BGE 补充召回 |

### 3.2 后端副本

后端目前仍有一份重复实现：

```text
backend/suda_ir/
```

后端 `bm25/optimized` engine 调用的是这份副本：

```text
backend/engine/bm25.py
backend/engine/optimized.py
```

当前已同步的后端副本文件：

```text
backend/suda_ir/fielded_index.py
backend/suda_ir/query_intent.py
backend/suda_ir/searcher.py
```

重要边界：

1. 后端 API 当前注册的是 `bm25`、`optimized`、`stub`。
2. 前端当前只支持 `基础 BM25 / 优化检索` 两个系统入口，不提供单独的 `conditional_semantic` 选项。
3. `conditional_semantic` 保留在 `scripts/evaluate_search.py` 中用于离线消融；同一设计已经接入 `backend/engine/optimized.py`，作为 optimized 的可选内部语义补充路径。
4. 该路径由 `SUDA_IR_SEMANTIC_OPTIMIZED` 控制，依赖 `sentence-transformers` 与 BGE 模型缓存；不可用时自动回退普通 optimized，避免影响前端演示。

### 3.3 前端入口

相关文件：

```text
frontend/src/api/search.js
frontend/src/stores/search.js
frontend/src/components/SearchBarPanel.vue
frontend/src/components/SearchStackPanel.vue
```

当前前端能力：

1. 搜索栏支持字段选择：全部、姓名、学院、研究方向。
2. 搜索栏支持引擎切换：`基础 BM25` / `优化检索`。
3. 请求路径为 `/api/search?engine=...`。
4. 搜索栈会记录每次查询使用的 engine，便于演示对比。

## 4. 各模式含义

### 4.1 baseline

基础 BM25。

特点：

1. 使用合并后的教师文本建索引。
2. 支持基础姓名精确/包含匹配。
3. 不理解学院别名、查询意图、字段差异和论文类特殊需求。

### 4.2 fielded

字段级 BM25。

特点：

1. 对 `name/research/papers/title/profile/college/content` 分字段计算 BM25。
2. 使用固定字段权重。
3. 不启用 fuzzy，不启用 query expansion。

单独使用时效果不一定好，因为教师主页字段缺失、栏目质量不一，固定字段权重容易放大噪声。

### 4.3 fielded+fuzzy

字段级 BM25 + fuzzy 姓名匹配。

主要解决：

```text
周国东 -> 周国栋
李守山 -> 李寿山
李军会 -> 李军辉
```

这是当前最明确的单点正收益模块之一。

### 4.4 fielded+expand

字段级 BM25 + 领域词典查询扩展。

典型扩展：

```text
NLP -> 自然语言处理 / 中文信息处理 / 机器翻译 / 信息抽取
知识图谱 -> 知识表示 / 图数据 / 智能问答 / 语义网络
计算机视觉 -> 图像处理 / 医学图像 / 深度学习
```

注意：查询扩展单独使用不保证全局提升，报告中应写成“对口语化/同义表达场景定向有效”。

### 4.5 adaptive

当前 optimized 的主体，但不含 paper RRF。

流程：

```text
query
  -> analyze_query
  -> 学院别名归一
  -> 职称词、论文词、口语 filler 识别
  -> cleaned_query
  -> intent.kind
  -> 动态 field_weights / expansion_weight
  -> 学院 hard filter
  -> FieldedBM25Index.search
```

核心价值：

1. 把“计算机学院/计科院/软件学院”等别名统一为标准学院。
2. 把学院从普通检索词变成 hard filter。
3. 对不同 query 类型使用不同字段权重。
4. 对研究方向、论文成果、学院+方向、职称+方向分别建模。

### 4.6 optimized

当前主线最优模式。

```text
optimized = adaptive + paper-only RRF
```

paper-only RRF 只在 `intent.kind == "paper"` 时触发：

```text
optimized fielded BM25 Top-N
+ baseline BM25 Top-N
-> RRF merge
```

它不是全查询多路融合，而是针对论文/成果类 query 的局部策略。报告中不能夸大为“完整多路召回系统”。

### 4.7 semantic

纯 BGE/向量召回。

实现位置：

```text
suda_ir/ir/semantic_index.py
scripts/evaluate_search.py::_semantic
```

文档构造：

```text
姓名 + 学院 + 职称 + 研究方向 + 论文成果 + 个人简介
```

每个字段会截断，减少超长主页内容噪声。

当前结论：纯 semantic 低于 optimized，不适合作为主排序器。

### 4.8 hybrid_semantic

无条件语义融合：

```text
optimized Top-50
+ semantic Top-50
-> weighted RRF
```

默认语义权重：

```text
semantic_weight = 0.05
```

当前结论：在语义泛化子集上有收益，但在正式主评测集上略低于 optimized，因此不适合作为默认全局策略。

### 4.9 conditional_semantic

当前 BGE 最新设计，也是最适合写入报告的语义增强版本。

核心思想：

```text
默认使用 optimized。
只有 query 满足语义改写/自然语言描述特征时，才触发 BGE 补充召回。
```

流程：

```text
query
  -> optimized Top-50
  -> analyze_query
  -> semantic_gate.should_use_semantic
      -> False: 直接返回 optimized Top-K
      -> True: 计算 semantic Top-50，并与 optimized 做 weighted RRF
```

不触发场景：

1. 姓名查询。
2. 论文/成果查询。
3. 字段过滤查询。
4. 短关键词查询。
5. 已经直接命中领域词典关键词的研究方向查询。

触发场景：

1. 长自然语言 query。
2. 口语化软描述。
3. 同义改写明显但没有直接关键词命中的 query。
4. optimized 结果为空时的兜底场景。

当前触发范围：

```text
正式 48 query：6 条
Q038,Q042,Q043,Q046,Q047,Q048

语义泛化 10 query：8 条
S001,S002,S005,S006,S007,S008,S009,S010
```

重要边界：

1. `conditional_semantic` 已实现并通过离线评测验证。
2. 前端不提供第三个 `conditional_semantic` 选项；BGE 作为 `optimized` 后端内部的可选补充召回路径接入。
3. 报告中可写为“已实现并验证，并已按 gate 接入 optimized 后端路径的补充创新点”，但不要写成“所有查询默认都使用 BGE”。

## 5. 评测命令

### 5.1 单元测试

```bash
python -m unittest discover -s tests
```

最新结果：

```text
Ran 26 tests OK
```

### 5.2 正式主评测

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --modes baseline,fielded,fielded+fuzzy,fielded+expand,adaptive,optimized,conditional_semantic \
  --semantic-model BAAI/bge-small-zh-v1.5 \
  --semantic-cache data/processed/eval/bge-small-zh-v1.5.npz \
  --semantic-local-files-only \
  --no-breakdown
```

如果只需要基础消融：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --ablation
```

### 5.3 语义泛化补充评测

首次使用 BGE 前安装可选依赖：

```bash
python -m pip install -r requirements-semantic.txt
```

运行评测：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/semantic_generalization_queries.jsonl \
  --qrels data/eval/semantic_generalization_qrels.jsonl \
  --top-k 5 \
  --modes baseline,optimized,conditional_semantic,semantic,hybrid_semantic \
  --semantic-model BAAI/bge-small-zh-v1.5 \
  --semantic-cache data/processed/eval/bge-small-zh-v1.5.npz \
  --semantic-local-files-only \
  --no-breakdown
```

说明：

1. 如果本机没有缓存 `BAAI/bge-small-zh-v1.5`，首次运行不能加 `--semantic-local-files-only`，需要联网下载模型。
2. 模型下载后建议加 `--semantic-local-files-only` 复现实验。
3. `avg_ms` 会受到模型首次加载、缓存和运行顺序影响，报告中主要比较 P@5、MRR、NDCG@5。

## 6. 最新评测结果

### 6.1 正式 48 query 主测试集

本次复跑时间：2026-06-12

```text
data=data/processed/handoff/handoff_teachers.clean.jsonl
docs=283
cases=48
top_k=5
rel_threshold=2
```

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| baseline | 0.4583 | 0.7899 | 0.6300 |
| fielded | 0.4417 | 0.7378 | 0.5992 |
| fielded+fuzzy | 0.4625 | 0.8420 | 0.7034 |
| fielded+expand | 0.4458 | 0.7795 | 0.6128 |
| adaptive | 0.5500 | 0.9219 | 0.8052 |
| optimized | 0.5708 | 0.9219 | 0.8186 |
| conditional_semantic | 0.5708 | 0.9219 | 0.8186 |

关键结论：

1. `optimized` 相比 `baseline` 明显提升：

```text
P@5:    0.4583 -> 0.5708
MRR:    0.7899 -> 0.9219
NDCG@5: 0.6300 -> 0.8186
```

2. `fielded` 单独低于 baseline，说明字段建模本身不是直接收益来源，需要与 fuzzy、intent、hard filter 结合。
3. `adaptive` 已经大幅提升，说明查询意图识别、动态字段权重、学院 hard filter 是核心贡献。
4. `optimized` 比 `adaptive` 继续提升，说明 paper-only RRF 对论文成果类 query 有贡献。
5. `conditional_semantic` 在正式主测试集上不破坏 optimized 表现，三项指标完全持平。

### 6.2 语义泛化 10 query 补充测试集

本次复跑时间：2026-06-12

```text
data=data/processed/handoff/handoff_teachers.clean.jsonl
docs=283
cases=10
top_k=5
rel_threshold=2
```

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| baseline | 0.4600 | 0.7500 | 0.4926 |
| optimized | 0.4600 | 0.8833 | 0.5437 |
| conditional_semantic | 0.5000 | 0.9000 | 0.5699 |
| semantic | 0.3400 | 0.7250 | 0.4543 |
| hybrid_semantic | 0.5000 | 0.9000 | 0.5667 |

关键结论：

1. 纯 `semantic` 明显低于 optimized，不能作为主排序器。
2. 无条件 `hybrid_semantic` 在语义泛化子集上有效，但在正式主评测集上不如 optimized 稳。
3. `conditional_semantic` 在语义泛化子集上超过 optimized：

```text
P@5:    0.4600 -> 0.5000
MRR:    0.8833 -> 0.9000
NDCG@5: 0.5437 -> 0.5699
```

4. 因此最准确的报告口径是：BGE 不是替代主模型，而是条件触发的语义泛化补充召回。

## 7. 当前可写入报告的创新点

建议把当前创新点组织为 6 个，其中前 5 个是主线 IR 模型创新，第 6 个是补充语义增强创新。

### 创新点 1：字段级 BM25 建模

设计：

```text
把教师文档拆成 name/research/papers/title/profile/college/content 等字段，
分别计算 BM25，再按字段权重融合。
```

报告口径：

1. 它提供了可解释字段建模基础。
2. 它单独使用并不一定提升，消融中 `fielded` 低于 baseline。
3. 它的价值在于支持后续动态字段权重和查询意图识别。

不要写成：

```text
字段级 BM25 单独显著提升检索效果。
```

### 创新点 2：fuzzy 姓名匹配

设计：

```text
对姓名查询和短 query 使用 rapidfuzz/SequenceMatcher 进行近似匹配。
```

解决问题：

```text
错别字、近似字、手误输入。
```

证据：

```text
fielded -> fielded+fuzzy
P@5:    0.4417 -> 0.4625
MRR:    0.7378 -> 0.8420
NDCG@5: 0.5992 -> 0.7034
```

### 创新点 3：领域词典查询扩展

设计：

```text
用人工构建的领域同义词词典扩展 query，例如 NLP/自然语言处理、知识图谱/智能问答。
```

报告口径：

1. 查询扩展对口语化、同义表达、复合 query 有帮助。
2. 单独全局效果不一定提升，因此不能夸大。
3. 它在 adaptive/optimized 中与 intent 和字段权重结合后发挥作用。

### 创新点 4：查询意图识别 + 学院 hard filter + 动态字段权重

这是当前最核心的主线创新点。

设计：

```text
analyze_query(query)
  -> 识别 college/title/paper/colloquial/research 等意图
  -> 清理 filler
  -> 学院别名归一
  -> 输出 cleaned_query、kind、field_weights、expansion_weight
```

学院别名示例：

| 用户写法 | 归一结果 |
|---|---|
| 计科院、计算机学院、软件学院 | 计算机科学与技术学院 |
| 数学学院 | 数学科学学院 |
| 物理学院 | 物理科学与技术学院 |
| 纳米学院、纳米研究院 | 功能纳米与软物质研究院 |
| 未来学院 | 未来科学与工程学院 |

证据：

```text
baseline -> adaptive
P@5:    0.4583 -> 0.5500
MRR:    0.7899 -> 0.9219
NDCG@5: 0.6300 -> 0.8052
```

报告口径：

```text
系统不是固定字段权重，而是根据 query 类型动态调整检索策略。
```

### 创新点 5：论文成果类 paper-only RRF

设计：

```text
当 intent.kind == "paper" 时，
融合 fielded optimized BM25 与 baseline BM25 的结果。
```

为什么只对 paper 触发：

1. 论文字段长、噪声多。
2. 论文标题、会议、成果词可能分散在不同字段。
3. 全查询 RRF 会引入额外噪声，因此当前只在 paper intent 局部使用。

证据：

```text
adaptive -> optimized
P@5:    0.5500 -> 0.5708
NDCG@5: 0.8052 -> 0.8186
```

旧分项结果显示 `paper_achievement` 类别 P@5 从 adaptive 的 0.5667 提升到 optimized 的 0.7333，可作为报告中的案例解释。

### 创新点 6：BGE 条件触发语义补充召回

这是最新补上的语义增强点。

设计动机：

1. 纯 BM25 擅长关键词匹配，但不擅长“换一种说法”的 query。
2. 纯 BGE 语义召回又容易引入主题相近但不精确的教师。
3. 因此采用条件触发：默认 optimized，只在语义改写明显时补充 BGE。

实现：

```text
suda_ir/ir/semantic_index.py
suda_ir/ir/semantic_gate.py
scripts/evaluate_search.py::conditional_semantic
backend/suda_ir/semantic_index.py
backend/suda_ir/semantic_gate.py
backend/engine/optimized.py
```

融合：

```text
optimized Top-50 + semantic Top-50
weighted RRF, semantic_weight=0.05
```

证据：

```text
正式 48 query：
optimized             P@5=0.5708 MRR=0.9219 NDCG@5=0.8186
conditional_semantic  P@5=0.5708 MRR=0.9219 NDCG@5=0.8186

语义泛化 10 query：
optimized             P@5=0.4600 MRR=0.8833 NDCG@5=0.5437
conditional_semantic  P@5=0.5000 MRR=0.9000 NDCG@5=0.5699
```

报告口径：

```text
本项目引入了轻量深度学习语义增强模块，但没有将其无条件替代 BM25。
系统通过查询 gate 判断是否启用 BGE 补充召回，在保持正式主测试集不下降的同时，
提升了语义泛化 query 子集表现。
```

不能写成：

```text
前端有一个独立 BGE 模型按钮。
所有 optimized 查询都会使用 BGE。
当前 BGE 全面超过 optimized。
纯语义向量召回优于 BM25。
```

## 8. 和老师 PPT 要求的对齐

老师 PPT 要求至少体现基础 IR 系统和优化方案。当前项目可对应如下：

| PPT 要求 | 当前实现 |
|---|---|
| 垂直检索系统 | 面向苏大 5 个学院导师信息 |
| 图形化查询界面 | Vue + Element Plus 前端，支持搜索、字段选择、引擎切换 |
| 多次迭代和模糊查询 | fuzzy 姓名匹配、口语化 query 处理 |
| 机器学习/深度学习相关度计算 | BGE 语义向量召回，作为条件触发补充召回 |
| 排序式 IR 系统 | BM25、字段 BM25、动态权重、RRF |
| 优化效果证明 | `evaluate_search.py` + qrels + P@5/MRR/NDCG@5 |
| 实验报告总结优化方案 | 本文档；早期讨论稿见 `docs/archive/ir_optimization_plan_process_record.md` |

当前最适合的项目题目口径：

```text
面向导师信息垂直检索的自适应混合检索与条件式语义增强
```

或者更短：

```text
面向苏大导师主页的自适应混合 IR 检索系统
```

## 9. 前端与后端运行说明

### 9.1 后端

安装依赖：

```bash
cd backend
python -m pip install -r requirements.txt
```

启动：

```bash
cd backend
set SUDA_IR_DEFAULT_DATA=../data/processed/handoff/handoff_teachers.clean.jsonl
set SUDA_IR_SEMANTIC_OPTIMIZED=1
set SUDA_IR_SEMANTIC_CACHE=data/processed/eval/bge-small-zh-v1.5.npz
set SUDA_IR_SEMANTIC_LOCAL_FILES_ONLY=1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

路径说明：`SUDA_IR_DEFAULT_DATA` 由后端工作目录 `backend/` 解析，因此使用 `../data/...`；`SUDA_IR_SEMANTIC_CACHE` 由项目根目录解析，因此使用 `data/...`。如果本机还没有 BGE 模型缓存，需要先在联网状态下运行语义评测或关闭 `SUDA_IR_SEMANTIC_LOCAL_FILES_ONLY` 下载模型。

API 文档：

```text
http://127.0.0.1:8000/docs
```

### 9.2 前端

安装依赖：

```bash
cd frontend
pnpm install
```

启动：

```bash
cd frontend
pnpm run dev --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:5173/
```

注意：

1. 前端目前只展示 `基础 BM25` 和 `优化检索`。
2. `conditional_semantic` 是离线评测模式，不在前端下拉里；实际演示时，BGE 门控作为 `优化检索` 后端内部可选路径运行。
3. 若后端未设置 `SUDA_IR_DEFAULT_DATA`，可能读取 `backend/mock/teachers.jsonl`，数据数量和编码效果会与 clean 数据不同。
4. 后端语义补充由 `SUDA_IR_SEMANTIC_OPTIMIZED`、`SUDA_IR_SEMANTIC_MODEL`、`SUDA_IR_SEMANTIC_CACHE`、`SUDA_IR_SEMANTIC_LOCAL_FILES_ONLY` 等环境变量控制；默认启用本地缓存模式，模型不可用时回退普通 optimized。

## 10. 仍需优化或注意的点

### P0：统一主包和后端副本

当前 `suda_ir/ir/` 和 `backend/suda_ir/` 有重复代码。短期已同步，但长期容易分叉。

建议后续：

1. backend 直接 import 根目录 `suda_ir`。
2. 删除或弃用 `backend/suda_ir` 副本。
3. 增加 CLI 与 API 一致性测试。

### P1：完善 optimized 内部 BGE 门控的演示可解释性

当前 BGE 增强已经接入 `backend/engine/optimized.py`，作为 `optimized` 内部可选路径，而不是新增第三个前端 engine。

后续更适合补的是：

```text
后端 stats / result debug 字段
前端“本次是否触发语义补充”的轻量提示
模型缓存检查与启动说明
```

但要注意：

1. BGE 模型加载较慢。
2. 首次运行需要下载模型。
3. Web 服务中应缓存 SemanticIndex，否则每次查询会很慢。
4. BGE 不建议直接替代 optimized，只适合作为 gate 控制下的补充召回。

### P2：输出 per-query 明细

当前评测脚本输出 overall 和 by-category，但没有保存每条 query 的 Top-K 明细。

建议新增：

```text
--details-output docs/ir_eval_details.json
```

用途：

1. 报告中挑选案例。
2. 分析哪些 query 被 BGE 改善。
3. 分析哪些 query 被语义噪声影响。

### P3：继续调 paper 排序

论文成果类 query 的 P@5 提升明显，但排序仍可继续优化。

方向：

1. 对 `ACL/CCF/Nature/SCI` 等强论文词给 phrase bonus。
2. paper RRF 使用可调权重，而不是固定等价融合。
3. 对 query 中的研究主题词和成果场景词拆分加权。

### P4：前端增加同屏对比

当前前端是切换式展示，不是同屏对比。

汇报时更有说服力的形态：

```text
左侧 baseline BM25 Top-5
右侧 optimized Top-5
显示 score / matched_terms / engine
```

### P5：优化 BGE 输入文本

当前 embedding 文本为：

```text
姓名、学院、职称、研究方向、论文成果、个人简介
```

后续可试：

1. 减少论文长列表噪声。
2. 强化研究方向和代表性成果。
3. 生成短摘要后再 embedding。

## 11. 报告可直接使用的总结段

可以在实验报告中使用或改写：

```text
本项目实现了一个面向苏州大学导师主页的垂直信息检索系统。系统以 BM25 为 baseline，
在此基础上构建字段级 BM25、模糊姓名匹配、领域词典查询扩展、查询意图识别、学院别名归一化、
学院 hard filter、动态字段权重和论文成果类 RRF 融合。为了进一步处理自然语言语义改写查询，
项目还实现了基于 BGE-small-zh-v1.5 的条件触发语义补充召回模块：系统默认使用 optimized BM25，
仅当 query 呈现长自然语言描述或同义改写特征时，才引入语义向量召回并与 optimized 结果进行加权 RRF 融合。

在 48 条正式 qrels 测试集上，optimized 相比 baseline 的 P@5 从 0.4583 提升到 0.5708，
MRR 从 0.7899 提升到 0.9219，NDCG@5 从 0.6300 提升到 0.8186。conditional_semantic
在正式测试集上保持与 optimized 相同的整体指标，说明条件触发机制没有破坏主模型稳定性。
在 10 条语义泛化补充测试集上，conditional_semantic 相比 optimized 的 P@5 从 0.4600 提升到 0.5000，
MRR 从 0.8833 提升到 0.9000，NDCG@5 从 0.5437 提升到 0.5699，验证了语义增强模块对自然语言改写查询的补充价值。
```

## 12. 当前不要误写的内容

以下说法不准确，不建议出现在报告或汇报中：

1. “前端有独立 BGE 模型按钮”或“所有 optimized 查询都会使用 BGE”。
2. “纯语义向量召回优于 optimized BM25”。
3. “完整多路召回 RRF 已覆盖所有 query”。
4. “字段级 BM25 单独带来全局提升”。
5. “查询扩展单独带来全局提升”。
6. “LLM reranker 已实现”。

更准确的说法是：

```text
项目主线是 optimized BM25 hybrid；BGE 是条件触发的补充语义召回模块，已在离线评测中验证对语义泛化 query 有收益，并已作为 optimized 后端内部的可选补充路径接入。
```
