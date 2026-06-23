# Soochow IR Tutor Search

面向苏州大学导师主页的垂直信息检索系统课程项目。

本项目从真实教师主页出发，完成了教师主页 seed 发现、HTML 抓取、结构化解析、数据清洗、BM25 baseline、自适应混合检索、BGE 条件触发语义补充召回、query/qrels benchmark、消融实验，以及 FastAPI + Vue 前后端演示系统。

## 项目当前状态

当前实现已经不是早期项目骨架，而是一个完整的导师信息垂直 IR 系统：

```text
真实教师主页
  -> seed 发现与 HTML 抓取
  -> 教师 JSONL 结构化解析
  -> 数据清洗与质量标记
  -> baseline BM25
  -> optimized 自适应混合检索
  -> conditional_semantic 条件式 BGE 语义补充
  -> query/qrels 评测与消融实验
  -> FastAPI + Vue 可交互展示
```

### 核心工作

| 方向 | 当前实现 |
|---|---|
| 数据工程 | 从 5 个学院/研究院采集教师主页，296 个 raw HTML 解析清洗为 283 条教师文档 |
| 基础检索 | BM25 baseline，支持中文分词、字符 n-gram 兜底、字段加权拼接和姓名精确匹配 |
| 自适应检索 | query intent 识别、字段级 BM25、动态字段权重、学院别名归一、学院 hard filter、fuzzy 姓名匹配、领域词典扩展、paper-only RRF |
| 语义增强 | BGE-small-zh-v1.5 语义向量召回，使用 semantic gate 条件触发，避免无条件 embedding 噪声 |
| Benchmark | 自建任务驱动 query/qrels：48 条主测试 query + 216 条 qrels，10 条语义泛化 query + 65 条 qrels |
| 前后端 | FastAPI 后端 + Vue/Pinia/Element Plus 前端，支持 BM25/optimized 切换、字段选择、Top-K、搜索栈、教师详情和匹配词展示 |

## 主要结论

### 主测试集

在 `data/eval/queries.jsonl` 和 `data/eval/qrels.jsonl` 上，`optimized` 相比 `baseline` 明显提升：

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| baseline | 0.4583 | 0.7899 | 0.6300 |
| optimized | 0.5708 | 0.9219 | 0.8186 |

消融结果显示，单独使用 fixed fielded BM25 或无条件 query expansion 不一定提升；真正有效的是 query intent 驱动的组合策略。

### 语义泛化补充测试集

在 `data/eval/semantic_generalization_queries.jsonl` 和 `data/eval/semantic_generalization_qrels.jsonl` 上，`conditional_semantic` 相比普通 `optimized` 有额外收益：

| 模式 | P@5 | MRR | NDCG@5 |
|---|---:|---:|---:|
| optimized | 0.4600 | 0.8833 | 0.5437 |
| conditional_semantic | 0.5000 | 0.9000 | 0.5699 |

结论：BGE 不适合无条件替代 BM25/optimized；它更适合作为自然语言改写场景下的条件触发补充召回。

## 目录结构

```text
suda_ir/
  crawler/       网页抓取、编码处理、HTML 解析
  data/          JSONL 读写工具
  ir/            BM25、字段检索、query intent、fuzzy、query expansion、BGE 语义召回
  app/           早期 CLI/Streamlit 入口
scripts/         seed 发现、HTML 汇总解析、数据清洗、检索评测
data/
  sample/        可直接运行的示例数据
  seeds/         教师主页 seed CSV
  eval/          query/qrels benchmark
  raw/           原始 HTML，默认不提交 Git
  processed/     清洗后数据产物，默认不提交 Git
backend/         FastAPI 后端
frontend/        Vue 前端
docs/            当前文档、报告素材和历史过程记录
tests/           单元测试
```

## 环境准备

推荐 Python 3.10+ 和 Node.js 18+。

安装 Python 依赖：

```bash
python -m pip install -r requirements.txt
```

语义召回/BGE 评测需要额外安装：

```bash
python -m pip install -r requirements-semantic.txt
```

安装前端依赖：

```bash
cd frontend
pnpm install
```

如果没有 pnpm，也可以使用 npm：

```bash
cd frontend
npm install
```

## 快速冒烟运行

GitHub 仓库中包含 `data/sample/teachers.jsonl`，可以直接测试基础检索链路：

```bash
python -m suda_ir.app.cli --data data/sample/teachers.jsonl --query 自然语言处理
python -m suda_ir.app.cli --data data/sample/teachers.jsonl --query 周国栋 --field name
```

运行单元测试：

```bash
python -m unittest discover -s tests
```

## 完整数据复现

完整实验使用的推荐检索输入为：

```text
data/processed/handoff/handoff_teachers.clean.jsonl
```

该文件由真实教师主页 HTML 解析和清洗得到。由于 `data/raw/` 和 `data/processed/` 属于数据产物，默认不提交 GitHub；如果老师/助教需要复现实验指标，需要先通过本地交接压缩包或重新抓取生成这些文件。

### 从本地 raw HTML 生成 clean JSONL

如果已经有 `data/raw/` 和 `data/seeds/colleges/`：

```bash
python scripts/parse_handoff_html_to_jsonl.py data/raw \
  --seed-root data/seeds/colleges \
  --output data/processed/handoff/handoff_teachers.jsonl \
  --report data/processed/handoff/handoff_teachers.report.json \
  --skip-nonteacher

python scripts/clean_teacher_jsonl.py \
  --input data/processed/handoff/handoff_teachers.jsonl \
  --output data/processed/handoff/handoff_teachers.clean.jsonl \
  --report data/processed/handoff/handoff_teachers.clean.report.json
```

预期结果：

```text
handoff_teachers.jsonl       283 条
handoff_teachers.clean.jsonl 283 条
```

### 从 seed 重新抓取某个学院

以计算机科学与技术学院为例：

```bash
python -m suda_ir.crawler.run_crawler \
  --seed-file data/seeds/colleges/计算机科学与技术学院/teacher_seeds.csv \
  --max-pages 101 \
  --output data/processed/计算机科学与技术学院/cs_teachers.jsonl \
  --raw-dir data/raw/计算机科学与技术学院 \
  --no-delay
```

其他学院替换 seed 文件、输出路径和 raw 目录即可。真实网站可能变化，因此论文报告中的指标以 2026-06-13 本地固定数据产物复跑结果为准。

## 评测复现

### 主测试集消融

```bash
python scripts/evaluate_search.py \
  --data data/processed/handoff/handoff_teachers.clean.jsonl \
  --queries data/eval/queries.jsonl \
  --qrels data/eval/qrels.jsonl \
  --top-k 5 \
  --ablation
```

包含模式：

```text
baseline
fielded
fielded+fuzzy
fielded+expand
adaptive
optimized
```

### 语义泛化补充评测

如果本地已经有 BGE embedding 缓存：

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

如果没有本地模型缓存，可以去掉 `--semantic-local-files-only`，让 `sentence-transformers` 下载模型。

## 前后端运行

### 后端

后端默认使用 `backend/mock/teachers.jsonl`，适合快速启动。若要使用完整 283 条教师数据，需要通过环境变量指定数据文件。

Windows PowerShell：

```powershell
cd backend
$env:SUDA_IR_DEFAULT_DATA="../data/processed/handoff/handoff_teachers.clean.jsonl"
$env:SUDA_IR_SEMANTIC_OPTIMIZED="0"
python run.py
```

macOS/Linux：

```bash
cd backend
SUDA_IR_DEFAULT_DATA=../data/processed/handoff/handoff_teachers.clean.jsonl \
SUDA_IR_SEMANTIC_OPTIMIZED=0 \
python run.py
```

后端地址：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

说明：

- `SUDA_IR_SEMANTIC_OPTIMIZED=0` 表示前端演示时先关闭 BGE，避免缺少模型缓存导致首次启动慢。
- 如果要启用 optimized 内部 BGE 门控补充，可设置 `SUDA_IR_SEMANTIC_OPTIMIZED=1`，并配置 `SUDA_IR_SEMANTIC_CACHE`。

### 前端

```bash
cd frontend
pnpm dev
```

或：

```bash
cd frontend
npm run dev
```

前端默认访问：

```text
http://localhost:5173
```

前端支持：

- `基础 BM25` / `优化检索` engine 切换
- 字段选择：全部、姓名、学院、研究方向
- Top-K 滑条
- 按相关度、姓名、学院排序
- 搜索栈 session 记录
- 教师结果卡片和多教师详情面板
- 匹配词、相关度、主页链接展示
- light/dark 主题切换

## 数据格式

最终用于检索的教师数据采用 JSONL 格式，每行一个教师对象：

```json
{
  "doc_id": "7862149ee883b878",
  "name": "袁建宇",
  "college": "功能纳米与软物质研究院",
  "title": "副研究员",
  "research": "主要研究方向为...",
  "papers": "论文、成果、引用统计等...",
  "profile": "个人简介...",
  "content": "重组后的全文正文...",
  "url": "https://web.suda.edu.cn/jyyuan/",
  "final_url": "https://web.suda.edu.cn/jyyuan/",
  "extra": {
    "sections": {},
    "clean_quality": "high",
    "clean_flags": []
  }
}
```

常用字段：

| 字段 | 含义 |
|---|---|
| `name` | 教师姓名 |
| `college` | 所属学院/研究院 |
| `title` | 职称 |
| `research` | 研究方向 |
| `papers` | 论文或科研成果 |
| `profile` | 个人简介 |
| `content` | 清洗重组后的全文 |
| `extra.clean_quality` | high / medium / low 清洗质量等级 |
| `extra.clean_flags` | 字段缺失、短文本、实验室主页等质量标记 |

## 重要文档

| 文档 | 用途 |
|---|---|
| `docs/ir_model_handoff.md` | IR 模型实现、消融结果、BGE 条件触发设计 |
| `docs/data_cleaning_report.md` | 数据清洗流程、质量标记和字段说明 |
| `docs/crawler_notes.md` | seed 发现、AJAX 接口分析、网页抓取记录 |
| `docs/engine_interface.md` | 后端 engine 接口和前后端调用约定 |
| `data/eval/README.md` | query/qrels benchmark 设计说明 |

## 注意事项

1. `data/raw/`、`data/processed/`、`frontend/node_modules/` 和 `backend/static/` 默认不提交 GitHub。
2. `conditional_semantic` 是离线评测模式；前端仍只展示 `bm25` 和 `optimized` 两个入口。
3. BGE 语义召回依赖 `sentence-transformers` 和模型缓存；没有缓存时首次运行会下载模型并较慢。
4. 当前 benchmark 是面向本项目任务的自建评测集，不是公开标准测试集；它用于客观比较本项目不同检索模式。
5. 若重新抓取官网，网页内容可能变化，数量和指标可能与报告固定结果略有差异。
