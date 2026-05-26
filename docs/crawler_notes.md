# 爬虫进度与数据策略

更新时间：2026-05-26

## 真实网页观察

苏州大学教师主页数据不是一个完全规整的数据源，当前观察到的情况包括：

- `https://web.suda.edu.cn/xylb/list.htm` 入口页静态正文较少，学院列表和教师列表不一定能从普通 HTML 直接解析出来。
- 新版教师主页通常有统一板块，例如“个人资料、个人简介、研究领域、论文、科研项目”等。
- 旧版或老师自建主页格式更自由，例如周国栋老师页面中直接出现“研究方向：自然语言处理、信息抽取、统计机器翻译、机器学习等。”。
- 部分 URL 会从 `https` 跳到 `http` 或自动补全尾部 `/`。
- 邮箱和电话需要脱敏后再进入检索数据。

## 当前爬虫策略

当前实现不强依赖学院列表页一次性解析成功，而是采用混合策略：

1. 使用 `data/seeds/teacher_seeds.csv` 维护教师主页种子。
2. 从种子 URL 抓取静态页面，并继续发现同域名静态链接。
3. 保存原始 HTML 到 `data/raw/`，便于后续复查和补解析规则。
4. 用 `is_probable_teacher_page` 过滤明显不是教师详情页的页面。
5. 对新版模板和自由格式页面都尝试抽取：
   - 姓名
   - 学院
   - 职称
   - 研究方向
   - 论文或成果
   - 个人简介
   - 清洗全文
6. 对电话和邮箱进行脱敏，统一替换为 `***`。

## 运行方式

用种子文件抓取：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/teacher_seeds.csv --max-pages 20 --output data/processed/teachers.jsonl
```

只测试单个教师页：

```bash
python -m suda_ir.crawler.run_crawler --seed https://web.suda.edu.cn/gdzhou/ --college 计算机科学与技术学院 --max-pages 1 --output data/processed/test_teachers.jsonl --no-delay
```

## 和两套检索系统的关系

爬虫数据应当由基础系统和优化系统共用。

后续实验建议统一使用：

```text
data/processed/teachers.jsonl
```

基础系统、模糊查询系统、语义向量系统或 LLM 重排序系统都读取同一份清洗数据。这样优化对比时唯一变化是检索算法，而不是数据源，实验结论更可信。

## 当前限制

- 目前种子文件只放了计算机学院的一批教师主页示例，尚未覆盖 5 个学院。
- 学院列表页动态内容尚未完全解析，后续可以补充 Playwright/Selenium 或手工维护学院种子 URL。
- 字段抽取仍是规则法，真实页面越多，越需要继续补充解析规则。

## 2026-05-26 交接记录

### 本次已经完成

本次对爬虫做了第一轮针对苏州大学教师主页的适配，改动集中在：

- `suda_ir/crawler/fetcher.py`
  - 增加 URL 标准化。
  - 增加客户端跳转识别，包括 `meta refresh` 和简单 `location.href`。
  - 增加 HTML bytes 解码策略，优先按 UTF-8 解码，失败后再尝试页面声明、`gb18030` 和 `gbk`。
  - 增加 HTTPS 失败后的 HTTP 兜底，解决部分 `web.suda.edu.cn` 页面 HTTPS EOF 的问题。
  - 增加请求头，模拟普通浏览器访问。
  - 增加失败页记录，避免某一个坏 URL 导致整个批量爬取中断。

- `suda_ir/crawler/parser.py`
  - 重写字段解析逻辑，修复之前中文字段别名乱码的问题。
  - 支持新版教师主页常见栏目：`个人资料`、`个人概况`、`个人简介`、`研究领域`、`论文`、`科研项目`、`科技成果`、`荣誉及奖励`、`招生信息`。
  - 支持旧版自由格式页面，例如 `研究方向：...`、`学术论文：...` 这种正文写法。
  - 增加姓名识别规则，例如 `周国栋的个人主页`、`姓名：刘安`、`陈伟 副教授`。
  - 增加职称识别，注意优先匹配 `特聘教授`、`副教授`、`副研究员` 这类长词。
  - 增加电话和邮箱脱敏，含 `xxx [at] suda.edu.cn`、`xxx at suda dot edu dot cn` 这类混写格式。

- `suda_ir/crawler/run_crawler.py`
  - 支持 `--seed-file`，从 CSV 批量读取教师主页种子。
  - 支持 `--no-delay`，方便本地小规模测试。
  - 支持跳过明显不是教师详情页的页面。
  - 保存原始 HTML 到 `data/raw/`，清洗后的 JSONL 输出到 `data/processed/`。

- `data/seeds/teacher_seeds.csv`
  - 暂时维护了一批计算机学院教师主页种子。
  - 后续需要补全到至少 5 个学院。

- `tests/test_parser.py`
  - 增加新版模板页和旧版自由格式页的解析测试。
  - 覆盖姓名、学院、职称、研究方向、论文、隐私脱敏和教师页过滤。

### 已验证结果

本地单元测试已通过：

```bash
python -m unittest discover -s tests
```

已用真实页面做过小规模验证：

```bash
python -m suda_ir.crawler.run_crawler --seed https://web.suda.edu.cn/gdzhou/ --college 计算机科学与技术学院 --max-pages 1 --output data/processed/test_teachers.jsonl --no-delay
python -m suda_ir.app.cli --data data/processed/test_teachers.jsonl --query 自然语言处理
```

验证结果：可以抓取周国栋老师主页，解析出姓名、学院、职称和研究方向，并能被现有 BM25 检索系统检索到。

### 关于“动态网页”的说明

当前没有直接解决学院总入口页 `https://web.suda.edu.cn/xylb/list.htm` 的动态加载问题。原因是该页的学院/教师列表不一定完整存在于初始静态 HTML 中，普通 `requests + BeautifulSoup` 不适合直接从这个入口自动发现所有教师。

当前采用的是更稳的课程项目策略：

1. 先人工或半自动收集教师主页 URL，写入 `data/seeds/teacher_seeds.csv`。
2. 教师详情页本身多数是静态 HTML。
3. 图形界面里的多个栏目通常已经在 HTML 中，只是前端用导航切换显示，因此可以通过正文提取拿到。
4. 所有栏目文字先进入 `content` 全文字段，核心字段再尽量结构化抽取。

所以当前爬虫能支撑基础 IR 系统的数据建设，但还不是“从动态入口页全自动发现全部教师”的最终版本。

### 图中栏目是否能抓

图中这种教师主页包含：

- `个人资料`
- `个人概况`
- `研究领域`
- `开授课程`
- `科研项目`
- `论文`
- `科研成果`
- `荣誉及奖励`
- `招生信息`

当前爬虫的能力是：

- 可以把这些栏目里的文字提取进 `content` 全文字段。
- 已经会优先结构化抽取 `个人资料`、`个人简介/个人概况`、`研究领域/研究方向`、`论文/科研成果`。
- 暂时没有把 `开授课程`、`科研项目`、`荣誉及奖励`、`招生信息` 单独拆成独立字段。

如果后续界面需要按栏目展示，建议在 `TeacherDoc.extra` 中增加：

```python
extra = {
    "sections": {
        "个人资料": "...",
        "个人概况": "...",
        "研究领域": "...",
        "开授课程": "...",
        "科研项目": "...",
        "论文": "...",
        "科研成果": "...",
        "荣誉及奖励": "...",
        "招生信息": "..."
    }
}
```

这样不会破坏现有基础检索，同时能支持更好的前端展示和字段加权。

### 需要组员继续优化

优先任务：

1. 补全 `data/seeds/teacher_seeds.csv`，覆盖至少 5 个学院，并至少包含计算机学院。
2. 批量运行爬虫，检查 `data/processed/teachers.jsonl` 的字段质量。
3. 抽样查看 `data/raw/` 中解析失败或字段为空的页面，补充 `parser.py` 规则。
4. 将更多栏目拆入 `extra["sections"]`，尤其是 `开授课程`、`科研项目`、`荣誉及奖励`、`招生信息`。
5. 如果必须从动态入口页自动发现教师，可以新建 Playwright/Selenium 版本爬虫，但不要替换当前静态爬虫；建议作为可选补充模块。

注意：`data/raw/` 和 `data/processed/` 默认不提交 GitHub，避免上传大量网页原文和潜在隐私信息。正式报告里可以统计数量和展示脱敏后的样例。
