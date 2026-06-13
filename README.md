# Soochow IR Tutor Search

苏州大学导师信息垂直检索系统课程项目骨架。

目标是搭建一个可协作、可扩展、可演示的导师信息垂直检索系统：基础版本使用网页爬取、正文解析、JSONL 存储、BM25 排序检索；当前优化版本已经加入模糊查询、查询扩展、查询意图识别、字段动态权重、论文类 RRF，以及离线评测用的条件触发 BGE 语义补充召回。

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

导入本项目中的本地 HTML：

```bash
python scripts/parse_handoff_html_to_jsonl.py data/raw \
  --seed-root data/seeds/colleges \
  --output data/processed/handoff/handoff_teachers.jsonl \
  --report data/processed/handoff/handoff_teachers.report.json \
  --skip-nonteacher
```

清洗导出的教师 JSONL：

```bash
python scripts/clean_teacher_jsonl.py \
  --input data/processed/handoff/handoff_teachers.jsonl \
  --output data/processed/handoff/handoff_teachers.clean.jsonl \
  --report data/processed/handoff/handoff_teachers.clean.report.json
```

检查汇总数量：

```bash
python -c "from pathlib import Path; print(sum(1 for _ in Path('data/processed/handoff/handoff_teachers.jsonl').open(encoding='utf-8'))); print(sum(1 for _ in Path('data/processed/handoff/handoff_teachers.clean.jsonl').open(encoding='utf-8')))"
```

当前 5 个学院的预期输出为 `283`、`283`。如果数量不同，优先检查是否漏写 `--seed-root data/seeds/colleges` 或 `--skip-nonteacher`。

## IR 模型与评测入口

当前推荐的检索输入是：

```text
data/processed/handoff/handoff_teachers.clean.jsonl
```

该文件由本地 HTML 解析和清洗脚本生成，属于数据产物，默认不提交 GitHub；需要由组员在本地或通过压缩包交接后生成。

当前代码中保留三类主要检索/评测模式：

| 模式 | 含义 |
|---|---|
| `baseline` | 基础 BM25 检索 |
| `optimized` | 字段 BM25 + 模糊姓名 + 查询扩展 + 查询意图识别 + 学院过滤 + paper RRF |
| `conditional_semantic` | 离线评测模式；在 `optimized` 基础上，对长自然语言/语义改写类 query 条件触发 BGE 语义向量补充召回 |

正式消融评测：

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --ablation
```

语义泛化补充评测：

```bash
python -m pip install -r requirements-semantic.txt

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

说明：

- `conditional_semantic` 不是无条件替代主模型，而是在 query 符合语义改写/自然语言描述特征时才补充向量召回，避免 embedding 噪声影响姓名、论文成果、短关键词等查询。
- 当前前端/后端演示只提供 `bm25` 和 `optimized`；`conditional_semantic` 已在评测脚本中实现和验证，尚未接入前端 engine。
- 文档入口见 `docs/README.md`。
- 详细设计、消融结果和后续优化建议见 `docs/ir_model_handoff.md`。
- 阶段性方案讨论已归档到 `docs/archive/ir_optimization_plan_process_record.md`，不要作为当前运行依据。

## 最终数据格式

最终用于检索的教师数据保存在 `data/processed/handoff/handoff_teachers.clean.jsonl` 中，采用 **JSONL** 格式：

- 每行一个教师文档
- 每行是一个完整 JSON 对象
- 适合后续直接做 BM25 建索引、字段检索、向量化或导入数据库

顶层字段结构如下：

```json
{
  "doc_id": "7862149ee883b878",
  "name": "袁建宇",
  "college": "功能纳米与软物质研究院",
  "title": "副研究员",
  "research": "主要研究方向为基于溶液法制程的新型光伏材料与器件：...",
  "papers": "120余篇，撰写专著章节1章，总引用~4500次，H因子40，...",
  "profile": "袁建宇 (Yuan Jianyu)\n2021年8月-至今, 苏州大学功能纳米与软物质实验室，教授...",
  "content": "功能纳米与软物质研究院\n\n袁建宇\n\n副研究员\n\n个人简介\n...",
  "url": "https://web.suda.edu.cn/jyyuan/",
  "final_url": "https://web.suda.edu.cn/jyyuan/",
  "extra": {
    "sections": {
      "个人简介": "...",
      "研究领域": "...",
      "论文": "...",
      "招生信息": "..."
    },
    "seed_file": "../handoff_teacher_html_5_colleges_2026-05-26/colleges/功能纳米与软物质研究院/teacher_seeds.csv",
    "raw_path": "../handoff_teacher_html_5_colleges_2026-05-26/功能纳米与软物质研究院/3458a522122bfeb6.html",
    "is_teacher_page": true,
    "page_reason": "chinese_teacher_signals",
    "source": "handoff_html",
    "cleaned_from": "handoff_teachers.jsonl",
    "clean_quality": "high",
    "clean_flags": []
  }
}
```

字段含义如下：

| 字段 | 类型 | 含义 |
|---|---|---|
| `doc_id` | `str` | 文档唯一 ID，用于索引和检索结果定位 |
| `name` | `str` | 教师姓名 |
| `college` | `str` | 所属学院/研究院，优先使用种子目录名 |
| `title` | `str` | 职称，如教授、副教授、研究员等 |
| `research` | `str` | 研究方向/研究领域，适合做主题召回 |
| `papers` | `str` | 论文、成果、引用统计等长文本 |
| `profile` | `str` | 个人简介、教育/经历摘要等长文本 |
| `content` | `str` | 重组后的全文正文，适合做全文检索主字段 |
| `url` | `str` | 原始教师主页 URL |
| `final_url` | `str` | 跳转后的最终 URL；若无跳转则与 `url` 相同 |
| `extra` | `dict` | 辅助元数据、原始解析信息、清洗质量标记 |

`extra` 中当前常用的子字段：

| 子字段 | 含义 |
|---|---|
| `sections` | 从页面中按栏目抽出的结构化小节，如“个人简介”“研究领域”“论文” |
| `seed_file` | 该教师 URL 来源的种子 CSV 文件 |
| `raw_path` | 对应原始 HTML 的本地路径 |
| `is_teacher_page` | 是否判定为教师页 |
| `page_reason` | 教师页判定依据，如 `chinese_teacher_signals` |
| `source` | 数据来源标记，目前为 `handoff_html` |
| `cleaned_from` | 说明该文件由哪个原始 JSONL 清洗得到 |
| `clean_quality` | 清洗质量等级：`high` / `medium` / `low` |
| `clean_flags` | 清洗时发现的问题标记，如 `missing_profile`、`lab_like_homepage` |

当前相关产物说明：

| 文件 | 说明 |
|---|---|
| `data/processed/handoff/handoff_teachers.jsonl` | 从本地 HTML 初步解析得到的原始结构化结果 |
| `data/processed/handoff/handoff_teachers.clean.jsonl` | 清洗后的完整数据，推荐作为检索输入 |
| `data/processed/handoff/handoff_teachers.filtered.jsonl` | 在清洗基础上去掉 `low` 质量样本后的版本 |
| `data/processed/handoff/*.report.json` | 对应清洗/过滤统计报告 |

## 基础流程

1. 从学院/教师页面爬取 HTML。
2. 保存原始 HTML 和最终 URL，避免跳转或解析失败导致数据丢失。
3. 使用多规则解析抽取姓名、学院、职称、研究方向、论文、简介等字段。
4. 清洗并规范化官网公开文本；当前实验口径保留官网公开联系方式，不再默认脱敏。
5. 将结构化字段和全文正文写入 JSONL。
6. 基于教师文档构建 BM25 索引。
7. 查询时优先处理姓名精确匹配，再进行字段加权全文排序。

## 四人协作建议

| 成员 | 方向 | 主要文件 |
|---|---|---|
| A | 爬虫与数据清洗 | `suda_ir/crawler/`, `suda_ir/data/` |
| B | 基础检索与排序 | `suda_ir/ir/` |
| C | 优化算法与评测 | `docs/ir_model_handoff.md`, `scripts/evaluate_search.py`, `suda_ir/ir/` |
| D | 界面、报告与展示 | `suda_ir/app/`, `docs/` |

## 后续优化路线

- 模糊查询：`rapidfuzz` 或编辑距离。
- 查询扩展：同义词词表、领域词典。
- 语义向量检索：当前已实现 BGE 条件触发补充召回的离线评测模式，后续可视部署成本接入后端 engine。
- LLM 重排序：BM25 召回 Top-K 后调用大模型评分。
- 评价指标：Precision@5、MRR、查询耗时。
