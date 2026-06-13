# 文档入口

本目录现在按“当前权威文档”和“历史过程记录”区分。后续写报告、调代码、交接任务时，优先看当前权威文档；`archive/` 只用于追溯过程，不作为运行依据。

## 当前权威文档

| 文档 | 用途 |
|---|---|
| `ir_model_handoff.md` | IR 检索系统当前实现、创新点、消融结果、BGE 条件触发补充召回设计、后续优化建议。写实验报告和继续优化 IR 时优先看这个。 |
| `data_cleaning_report.md` | 数据清洗流程、字段结构、质量控制和清洗产物说明。 |
| `crawler_notes.md` | web.suda 教师主页发现、AJAX seed 提取、学院分目录爬取和原始 HTML 交接记录。 |
| `engine_interface.md` | 后端 Engine 接口与前端/后端调用约定。 |

## 历史过程记录

`archive/` 下的文档是早期讨论稿、阶段性实验记录或分工记录，文件名已统一加上 `process_record`：

| 文档 | 说明 |
|---|---|
| `archive/experiments_process_record.md` | 早期实验记录，指标不是最新口径。 |
| `archive/ir_optimization_plan_process_record.md` | 早期 IR 优化方案讨论稿，最终实现以后续 handoff 为准。 |
| `archive/refactor_engine_process_record.md` | 后端 Engine 重构过程记录。 |
| `archive/progress_log_process_record.md` | 早期项目进度记录。 |
| `archive/team_plan_process_record.md` | 早期组员分工讨论。 |
| `archive/retrieval_related_work_process_record.md` | 早期相关工作梳理。 |

## 当前推荐阅读顺序

1. 想理解整个 IR 系统和创新点：读 `ir_model_handoff.md`。
2. 想复现实验指标：按 `ir_model_handoff.md` 的评测命令运行。
3. 想理解数据怎么来的：读 `crawler_notes.md` 和 `data_cleaning_report.md`。
4. 想接前端或改后端接口：读 `engine_interface.md`，再看 `suda_ir/app/` 和 `suda_ir/ir/`。
5. 写报告时需要过程材料，再去 `archive/` 找早期方案和进度证据。
