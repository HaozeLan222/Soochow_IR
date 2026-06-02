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
