# IR 检索系统优化交接文档

更新时间：2026-06-10

本文档用于交接当前 IR 检索系统的已实现能力、评测结果、代码入口和后续优化任务。当前版本已经不是单纯 BM25 baseline，而是具备 baseline/optimized 双模式、正式 qrels 评测和前端引擎切换的可演示版本。

## 1. 当前结论

本轮已按前期 plan 补齐以下关键点：

1. `scripts/evaluate_search.py` 已支持正式 `queries.jsonl + qrels.jsonl` 评测，并输出 overall/per-category 指标。
2. `suda_ir/ir/query_intent.py` 与 `backend/suda_ir/query_intent.py` 新增查询意图识别，包括学院别名、职称词、论文成果词、口语化 filler 处理。
3. `FieldedBM25Index.search()` 支持动态字段权重、扩展词权重和候选文档过滤。
4. optimized 检索支持学院 hard filter：如 `计科院/计算机学院/软件学院` 归一到 `计算机科学与技术学院`。
5. optimized 检索支持按意图调整权重：研究方向、论文成果、学院+方向、职称+方向使用不同字段权重和 expansion weight。
6. 论文成果类查询新增轻量 RRF：只在 `paper` intent 下融合 optimized fielded BM25 与 baseline BM25，避免论文长列表噪声。
7. 前端已支持在搜索栏切换 `基础 BM25` 和 `优化检索`，并在搜索栈中记录 engine。
8. 后端 `bm25/optimized` engine 均可通过 `/api/search?engine=...` 调用，后端副本逻辑已与主包同步。

当前还未作为主线结论采用的高级项：

- embedding 语义召回已接入并用 `BAAI/bge-small-zh-v1.5` 跑通，但当前指标低于 optimized BM25 hybrid，建议作为探索实验，不作为主创新点。
- reranker / LLM 重排序。
- 全查询类型的多路召回 RRF。当前 RRF 只用于论文成果类 query。
- baseline/optimized 同屏对比 UI。当前前端是切换式展示，不是并排对比。

## 2. 当前代码入口

### 2.1 IR 主包

| 文件 | 作用 | 当前状态 |
|---|---|---|
| `suda_ir/ir/index.py` | V0 baseline BM25，使用重复 token 实现粗字段权重 | 已实现 |
| `suda_ir/ir/fielded_index.py` | 字段级 BM25，支持动态权重、扩展词权重、候选过滤 | 已更新 |
| `suda_ir/ir/fuzzy.py` | rapidfuzz/SequenceMatcher 模糊姓名匹配 | 已实现 |
| `suda_ir/ir/query_expansion.py` | 领域词典扩展，如 NLP、机器翻译、知识图谱 | 已实现 |
| `suda_ir/ir/query_intent.py` | 查询意图识别、学院别名、动态权重策略 | 本轮新增 |
| `suda_ir/ir/semantic_index.py` | 可选语义向量召回，支持 sentence-transformers 与 hashing 冒烟后端 | 本轮新增 |
| `suda_ir/ir/searcher.py` | baseline/optimized 统一入口，含学院过滤与 paper RRF | 已更新 |

### 2.2 后端副本

后端目前仍维护一份 `backend/suda_ir/` 副本，`backend/engine/bm25.py` 和 `backend/engine/optimized.py` 调用的是这份代码。因此主包改动必须同步到：

```text
backend/suda_ir/fielded_index.py
backend/suda_ir/query_intent.py
backend/suda_ir/searcher.py
```

本轮已同步。后续若继续优化 IR，建议优先考虑消除这份重复代码，让 backend 直接复用根目录 `suda_ir/`，否则容易出现 CLI 指标和前端结果不一致。

### 2.3 前端入口

相关文件：

```text
frontend/src/api/search.js
frontend/src/stores/search.js
frontend/src/components/SearchBarPanel.vue
frontend/src/components/SearchStackPanel.vue
```

当前行为：

- `searchTeachers(params, engine)` 会请求 `/api/search?engine=${engine}`。
- Pinia store 增加 `engine: "bm25"`。
- 搜索栏新增 `基础 BM25 / 优化检索` 单选。
- 每条搜索 session 会保存 `engine`，搜索栈中显示 `BM25` 或 `优化检索`。

## 3. optimized 检索流程

当前 optimized 查询流程如下：

```text
用户 query
  -> analyze_query(query)
  -> 解析学院别名、职称词、论文成果词、口语化 filler
  -> 得到 cleaned_query / kind / college / field_weights / expansion_weight
  -> 如识别 college，先做 hard filter
  -> FieldedBM25Index 按动态权重排序
  -> 短 query 启用 fuzzy name bonus
  -> paper intent 额外与 baseline BM25 做 RRF
  -> 返回 Top-K
```

已支持的学院别名包括：

| 用户 query 可能写法 | 归一学院 |
|---|---|
| 计科院、计算机学院、软件学院 | 计算机科学与技术学院 |
| 数学学院 | 数学科学学院 |
| 物理学院 | 物理科学与技术学院 |
| 纳米学院、纳米研究院 | 功能纳米与软物质研究院 |
| 未来学院 | 未来科学与工程学院 |

## 4. 评测命令

单元测试：

```bash
python -m unittest discover -s tests
```

sample 兼容性评测：

```bash
python scripts/evaluate_search.py \
  --data data/sample/teachers.jsonl \
  --queries data/sample/eval_queries.jsonl \
  --top-k 5 \
  --no-breakdown
```

正式消融评测：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --ablation
```

如需保存指标 JSON：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --ablation \
  --output data/processed/eval/ir_metrics.json
```

注意：`data/processed/` 通常被 git ignore，指标 JSON 如需进仓库，应另存到 `docs/` 或复制表格到文档。

V3 轻量语义向量召回评测：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --modes baseline,optimized,semantic,hybrid_semantic \
  --semantic-model BAAI/bge-small-zh-v1.5 \
  --semantic-cache data/processed/eval/bge-small-zh-v1.5.npz \
  --semantic-local-files-only
```

首次运行前需要安装可选依赖：

```bash
python -m pip install -r requirements-semantic.txt
```

当前已能用本地缓存离线加载 `BAAI/bge-small-zh-v1.5`。如果首次运行尚未缓存模型，需要先联网下载；下载成功后建议使用 `--semantic-local-files-only` 复现实验，避免每次请求 HuggingFace。

仅用于冒烟测试的 fallback 命令：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --modes baseline,optimized,semantic,hybrid_semantic \
  --semantic-backend hashing \
  --semantic-cache data/processed/eval/handoff_hashing_semantic.npz \
  --no-breakdown
```

注意：`hashing` 后端不是深度学习模型，只是无依赖环境下检查代码路径的词面向量 fallback，不能作为“轻量深度学习语义召回”的实验结果。

## 5. 本轮验证结果

测试环境：

```text
数据：data/processed/handoff/handoff_teachers.clean.jsonl
docs：283
queries：48
qrels：data/eval/qrels.jsonl
相关阈值：relevance >= 2
Top-K：5
```

已运行：

```text
python -m unittest discover -s tests
结果：19 tests OK
```

sample 评测：

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| baseline | 0.1500 | 0.7500 | 0.7500 |
| optimized | 0.2000 | 1.0000 | 1.0000 |

正式 48 query 消融：

| 版本 | P@5 | MRR | NDCG@5 | 平均耗时 |
|---|---:|---:|---:|---:|
| baseline | 0.4583 | 0.7899 | 0.6300 | 4.74 ms |
| fielded | 0.4417 | 0.7378 | 0.5992 | 16.31 ms |
| fielded+fuzzy | 0.4625 | 0.8420 | 0.7034 | 21.71 ms |
| fielded+expand | 0.4458 | 0.7795 | 0.6128 | 12.96 ms |
| adaptive | 0.5500 | 0.9219 | 0.8052 | 7.31 ms |
| optimized | 0.5708 | 0.9219 | 0.8186 | 7.57 ms |

版本含义：

| 版本 | 含义 |
|---|---|
| `baseline` | 原始 BM25 + 姓名精确/包含匹配 |
| `fielded` | 字段级 BM25，不启用 fuzzy，不启用 expansion |
| `fielded+fuzzy` | 字段级 BM25 + fuzzy 姓名召回 |
| `fielded+expand` | 字段级 BM25 + 领域词典查询扩展 |
| `adaptive` | fuzzy + expansion + 查询意图识别 + 动态字段权重 + 学院 hard filter，不启用 paper RRF |
| `optimized` | `adaptive` + 论文成果类 paper-only RRF |

optimized 相比 baseline：

```text
P@5:    0.4583 -> 0.5708
MRR:    0.7899 -> 0.9219
NDCG@5: 0.6300 -> 0.8186
```

这说明当前优化不是只“堆功能”，而是在正式测试集上确实提高了相关教师进入 Top-5 和排在前列的能力。

adaptive 与 optimized 的差异也能解释 paper RRF 的贡献：

```text
adaptive:  P@5=0.5500, NDCG@5=0.8052
optimized: P@5=0.5708, NDCG@5=0.8186
```

其中 `paper_achievement` 类别从 adaptive 的 `P@5=0.5667, NDCG@5=0.7899` 提升到 optimized 的 `P@5=0.7333, NDCG@5=0.8967`，说明 paper-only RRF 不是装饰性模块，而是在论文/成果类 query 上补回了字段级 BM25 的短板。

## 6. 创新点可写入性审查

严格按 IR 算法模块计，当前有 5 个可讨论的优化/创新点；如果把工程验证也算上，则另有 2 个支撑性创新点。

### 6.1 算法创新点

| 模块 | 是否建议作为创新点写入报告 | 消融证据 | 报告口径 |
|---|---|---|---|
| 字段级 BM25 | 可以写，但不能写成“单独提升” | `fielded` 整体低于 baseline：P@5 0.4417 < 0.4583 | 写成“可解释字段建模基础”，说明单独使用受字段缺失和权重影响，需要与后续模块结合 |
| fuzzy 姓名匹配 | 可以强写 | `fuzzy_name` 从 baseline 的 MRR/NDCG=0 提升到 0.8333；整体 `fielded+fuzzy` 也优于 `fielded` | 写成对姓名错别字、近似输入的鲁棒性优化 |
| 领域词典查询扩展 | 可以写，但要写成“定向有效” | `fielded+expand` 整体不如 baseline，但 `colloquial_compound`、`title_research`、`soft_preference` 有提升 | 写成对 NLP/知识图谱/机器翻译等领域词和口语化 query 的增强；不要声称单独全局提升 |
| 查询意图识别 + 动态字段权重 + 学院 hard filter | 可以作为核心创新点强写 | `adaptive` 相比 baseline：P@5 0.4583 -> 0.5500，NDCG@5 0.6300 -> 0.8052；`college_research` NDCG 0.6698 -> 0.8019 | 写成自适应混合检索核心：按 query 类型调整字段权重，并把学院约束从普通词转为 hard filter |
| paper-only RRF 融合 | 可以写，但限定为论文成果类 | `paper_achievement` 从 adaptive P@5 0.5667 -> optimized 0.7333，NDCG 0.7899 -> 0.8967 | 写成“针对论文/成果 query 的局部融合策略”，不要写成全查询多路融合 |

### 6.2 工程与评测支撑点

| 模块 | 是否建议写入报告 | 说明 |
|---|---|---|
| 正式 qrels 评测与消融脚本 | 建议写入实验设计 | 支持 `queries.jsonl + qrels.jsonl`、P@5、MRR、NDCG@5、per-category 指标，使优化可量化 |
| 前端 BM25/优化检索切换 | 建议写入系统实现 | 方便演示 baseline 与 optimized；但它是工程展示点，不是 IR 排序算法创新 |

### 6.3 不能夸大的部分

以下内容不能写成“已完整实现”：

1. 完整多路召回 RRF：当前 RRF 只用于 `paper` intent，不是所有 query 都融合。
2. embedding 语义召回：实验版代码和真实 BGE 指标已跑通，但当前效果低于 optimized，不能写成“提升型主创新点”。
3. reranker/LLM 重排序：尚未实现。 
4. 字段级 BM25 单独提升：消融不支持这个说法。
5. 查询扩展单独全局提升：消融不支持，只能写定向有效。

### 6.4 V3 语义向量模块状态

当前已新增 `SemanticIndex` 和评测模式：

```text
semantic：纯语义向量召回
hybrid_semantic：optimized Top-50 + semantic Top-50 的 RRF 融合
```

真实 BGE 语义向量召回已经跑通，正式集结果如下：

| 版本 | P@5 | MRR | NDCG@5 | 说明 |
|---|---:|---:|---:|---|
| optimized | 0.5708 | 0.9219 | 0.8186 | 当前主线最优 |
| semantic-BGE | 0.3250 | 0.7438 | 0.5691 | 纯语义召回，低于 BM25 hybrid |
| hybrid_semantic-BGE, weight=0.05 | 0.5542 | 0.9219 | 0.8113 | 接近 optimized，但仍略低 |
| hybrid_semantic-BGE, weight=0.6 | 0.4583 | 0.8958 | 0.7142 | 语义权重过高会明显引入噪声 |

因此：V3 代码可以保留，也可以在报告中作为“探索性深度学习语义增强实验”简要说明；但不建议作为第 6 个主创新点，因为它没有超过当前 optimized。这个结果本身也有解释价值：教师主页数据规模较小、字段结构较强，BM25 + 意图规则已经很贴合任务，而通用 BGE 语义向量容易把主题相近但非 qrels 标注目标的教师引入 Top-5。

推荐报告总口径：

```text
本文实现了一个面向导师信息检索的自适应混合检索框架。系统以 BM25 为 baseline，
引入字段级建模、模糊姓名匹配、领域词典查询扩展、查询意图识别、学院 hard filter、
动态字段权重和论文成果类 RRF 融合。消融实验表明，单独字段级建模和无约束查询扩展
并不总是带来全局提升，但在意图识别和动态权重控制后，最终 optimized 模式在正式评测集上
取得 P@5、MRR、NDCG@5 的整体提升。
```

## 7. 分类别表现

| 类别 | baseline P@5 | optimized P@5 | baseline NDCG@5 | optimized NDCG@5 | 说明 |
|---|---:|---:|---:|---:|---|
| exact_name | 0.2000 | 0.2000 | 1.0000 | 1.0000 | 单一相关文档，P@5 天然只有 0.2；MRR=1 正常 |
| fuzzy_name | 0.0000 | 0.1667 | 0.0000 | 0.8333 | fuzzy 是明确正收益 |
| research_direction | 0.8333 | 0.8667 | 0.8325 | 0.8394 | 动态 research 权重后超过 baseline |
| paper_achievement | 0.7000 | 0.7333 | 0.9265 | 0.8967 | paper RRF 提升 P@5；排序质量仍可继续调 |
| college_research | 0.7000 | 0.7667 | 0.6698 | 0.8019 | 学院 hard filter 修复了原短板 |
| title_research | 0.4000 | 0.5333 | 0.5916 | 0.6575 | 职称/方向动态权重有效，但 MRR 仍可调 |
| soft_preference | 0.3333 | 0.5667 | 0.4527 | 0.7204 | 软偏好 query 明显收益 |
| colloquial_compound | 0.5000 | 0.7333 | 0.5671 | 0.7994 | 口语化 filler 清洗 + 查询扩展有效 |

关键解释：

1. `fuzzy_name`：baseline 对错别字姓名基本无能为力，optimized 通过 fuzzy name search 能召回。
2. `college_research`：上一版最大短板是把学院当普通词排序；现在 hard filter 后 P@5 和 NDCG 均提升。
3. `paper_achievement`：论文类只用 fielded BM25 会被长论文列表干扰；加入 paper-only RRF 后 P@5 从 0.5667 提到 0.7333。
4. `exact_name`：P@5=0.2 不代表差，因为每个姓名 query 通常只有一个强相关教师；看 MRR/NDCG 更合理。

## 8. 和实验报告 plan 的对齐

| 计划模块 | 当前状态 | 说明 |
|---|---|---|
| V0 Baseline BM25 | 已实现 | `BM25Index` |
| V1 Field-aware BM25 | 已实现 | `FieldedBM25Index` |
| fuzzy 姓名匹配 | 已实现 | `fuzzy_name_search` |
| 查询扩展 | 已实现 | `DOMAIN_SYNONYMS` |
| 查询意图识别 | 已初步实现 | 学院、论文、职称、口语化、研究方向 |
| 学院 hard filter | 已实现 | 从 query 自动解析学院别名 |
| 动态字段权重 | 已实现 | 按 intent 调整 `field_weights` |
| RRF 融合 | 部分实现 | 当前只用于 paper intent |
| 前端 engine 切换 | 已实现 | BM25 / 优化检索 |
| 正式 qrels 评测 | 已实现 | 支持 overall + per-category |
| embedding 语义召回 | 已接入实验版 | `SemanticIndex` + `semantic/hybrid_semantic` 评测模式；真实模型依赖未安装，尚未验证指标 |
| reranker / LLM rerank | 未实现 | 后续 V3 |

报告表述建议：

```text
本系统实现了以 BM25 为基础的自适应混合检索雏形：在字段级 BM25 的基础上，
结合查询意图识别、学院别名归一化、学院硬过滤、动态字段权重、领域词典查询扩展、
模糊姓名匹配和论文类 RRF 融合。实验表明，optimized 模式在正式 48 条 query 评测集上
较 baseline 的 P@5、MRR、NDCG@5 均有提升。
```

不要写成：

```text
已完成并验证 embedding 语义检索、LLM 重排序、完整多路召回系统。
```

这些还没有落地。

## 9. 当前还需优化的点

### P0：补充更细的 per-query 误差分析

现在评测脚本已能输出 per-category，但还没有保存每条 query 的 Top-K 结果和命中情况。建议下一步给 `evaluate_search.py` 增加：

```text
--details-output docs/ir_eval_details.json
```

用于报告中挑案例截图和解释错误来源。

### P1：继续调 paper 排序质量

当前 `paper_achievement` 的 P@5 高于 baseline，但 NDCG@5 仍略低于 baseline：

```text
baseline NDCG@5=0.9265
optimized NDCG@5=0.8967
```

说明相关教师能进 Top-5，但强相关教师的排序还可以再调。方向：

1. 对 `ACL/CCF/Nature/SCI` 等强论文词给 phrase bonus。
2. 对 query 中研究主题词和论文场景词拆开加权。
3. paper RRF 中调整 optimized/baseline 权重，而不是等权 RRF。

### P2：优化 title_research 的 MRR

`title_research` P@5/NDCG 有提升，但 MRR 从 baseline 0.8889 变成 optimized 0.7500。说明前五里相关更多，但第一位命中不够稳定。方向：

1. 对职称词如 `教授/副教授/讲师/博导` 做更明确的 title filter 或 title boost。
2. 对“年轻教师”等软条件建立规则特征。

### P3：前端增加对比模式

当前前端只有 engine 切换。报告展示会更需要：

```text
同一 query 左侧 BM25，右侧 optimized
展示 Top-5、score、matched_terms
```

这能直接用于报告截图。

### P4：统一主包和后端副本

当前 `suda_ir/ir/` 和 `backend/suda_ir/` 有重复实现。短期已经同步，但长期容易分叉。建议：

1. backend 直接 import 根目录 `suda_ir`。
2. 删除或弃用 `backend/suda_ir` 副本。
3. 用测试确认 CLI 和 API 返回一致。

### P5：可选语义增强

V3 语义增强已经有实验版代码和真实 BGE 指标，并新增 `conditional_semantic` 条件触发模式。目前仍不建议替代主线 `optimized`，但可以作为语义泛化场景的补充召回模块：

1. 只在 `soft_preference` 或自然语言长 query 上触发语义融合，而不是所有 query 都融合。
2. 尝试更适合短文本检索的模型或中文 reranker。
3. 尝试对教师文档摘要做更短、更干净的 embedding 文本，减少论文列表和简介噪声。
4. 若后续 `conditional_semantic` 在更多真实 query 上稳定超过 optimized，再升级为默认线上排序策略。

当前更稳的主线仍是已经验证过的 BM25 hybrid；V3 建议作为“条件触发的补充增强”和语义泛化实验写入报告。

## 10. 文档口径提醒

1. 正式评测统一使用 `data/eval/queries.jsonl + data/eval/qrels.jsonl`。
2. 根目录 `eval/` 与 `data/eval/` 内容重复，后续文档只引用 `data/eval/`。
3. `docs/experiments.md` 里如果还引用不存在的旧文件，需要后续同步更新。
4. `data/processed/` 和 `data/raw/` 是数据产物，通常不直接提交 GitHub。
5. 当前数据清洗策略是保留并规范化官网公开联系方式，不再默认脱敏；报告和测试应保持一致。

## 11. 语义泛化补充测试集

为验证 V3 “轻量语义向量召回 + RRF 融合”是否确实适合语义改写类查询，新增一个小型补充测试集：

```text
data/eval/semantic_generalization_queries.jsonl
data/eval/semantic_generalization_qrels.jsonl
```

设计原则：

1. 共 10 条 query，全部是自然语言语义改写，不直接照抄原始关键词。
2. 标注沿用正式 qrels 中相近主题 query 的相关教师，保证不是临时按结果倒推标注。
3. 该子集只用于补充分析“语义泛化能力”，不替代正式 48 条 `queries.jsonl + qrels.jsonl` 主评测。

典型 query 示例：

| query_id | 查询 | 对应正式 query |
|---|---|---|
| S001 | 研究人类语言理解和文本分析的老师 | Q013 自然语言处理 |
| S002 | 做跨语言文本分析与翻译技术的导师 | Q014 机器翻译 |
| S005 | 研究非线性系统长期行为的导师 | Q017 动力系统 |
| S008 | 研究文本情感理解和观点分析的老师 | Q020 情感分析 |
| S009 | 纳米学院研究二维材料界面调控的老师 | Q047 二维材料/表界面 |

运行命令：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/semantic_generalization_queries.jsonl \
  --qrels data/eval/semantic_generalization_qrels.jsonl \
  --top-k 5 \
  --modes baseline,optimized,conditional_semantic,semantic,hybrid_semantic \
  --semantic-model BAAI/bge-small-zh-v1.5 \
  --semantic-cache data/processed/eval/bge-small-zh-v1.5.npz \
  --semantic-local-files-only
```

当前结果：

| 模式 | P@5 | MRR | NDCG@5 | 平均耗时 |
|---|---:|---:|---:|---:|
| baseline | 0.4600 | 0.7500 | 0.4926 | 6.42 ms |
| optimized | 0.4600 | 0.8833 | 0.5437 | 13.06 ms |
| semantic-BGE | 0.3400 | 0.7250 | 0.4543 | 1248.95 ms |
| hybrid_semantic-BGE | 0.5000 | 0.9000 | 0.5667 | 26.43 ms |
| conditional_semantic-BGE | 0.5000 | 0.9000 | 0.5699 | 1501.03 ms |

耗时会受 BGE 模型首次加载和缓存状态影响，报告中建议主要比较 P@5、MRR、NDCG@5。

结论：

1. 在正式 48 query 主测试集上，`hybrid_semantic` 仍略低于 `optimized`，因此不能作为主线最终排序器。
2. 在这个语义泛化补充子集上，`conditional_semantic` 相比 `optimized` 有小幅提升：P@5 从 0.4600 到 0.5000，MRR 从 0.8833 到 0.9000，NDCG@5 从 0.5437 到 0.5699。
3. 纯 `semantic-BGE` 仍然不稳定，说明教师主页这种小规模、强字段结构数据并不适合完全依赖通用向量召回。
4. 更合理的报告口径是：V3 可以作为“面向自然语言语义改写查询的条件触发补充召回模块”，在语义泛化场景有验证收益；但主系统仍采用 `optimized`，避免在所有查询上引入语义噪声。

当前已实现的条件触发策略：

1. 新增 `suda_ir/ir/semantic_gate.py`，负责判断是否启用 BGE 语义召回。
2. `scripts/evaluate_search.py` 新增 `conditional_semantic` 模式。
3. 不触发场景：姓名查询、论文/成果查询、字段过滤查询、短关键词查询、已经含有明确领域词典关键词的研究方向查询。
4. 触发场景：长自然语言 query、口语化软描述、同义改写明显且不直接命中领域词典的查询。
5. 触发后使用 `optimized Top-50 + semantic Top-50` 做加权 RRF 融合，默认语义权重为 `0.05`。

正式 48 query 主测试集复测：

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| baseline | 0.4583 | 0.7899 | 0.6300 |
| optimized | 0.5708 | 0.9219 | 0.8186 |
| conditional_semantic | 0.5708 | 0.9219 | 0.8186 |

这说明条件触发没有破坏正式主测试集表现；在语义泛化补充集上则带来提升。因此报告里可以把 V3 写成“已实现并验证的补充创新点”，但要强调它是条件触发模块，不是替代 optimized 的默认主排序器。

当前 gate 触发范围：

```text
正式 48 query：触发 6 条（Q038,Q042,Q043,Q046,Q047,Q048）
语义泛化 10 query：触发 8 条（S001,S002,S005,S006,S007,S008,S009,S010）
```

后续如果继续优化 V3，优先方向：

1. embedding 文本不要直接使用完整教师主页全文，可改为 `name + college + title + research_interests + papers标题摘要` 的短摘要，减少页面导航、页脚和论文长列表噪声。
2. 对 `conditional_semantic` 输出 Top-K 明细做 per-query 对比，重点观察 S002、S005、S006、S008 这类语义改写明显的查询。
3. 如果接入前端，建议仍把 `optimized` 作为默认模式，只在后端内部满足 gate 条件时自动补充语义召回。
