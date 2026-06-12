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

## 2026-05-26 最新交接：计科院 seed 扩充任务

### 当前代码状态

当前爬虫已经形成一个可继续扩展的计科院专项版本：

- `data/seeds/teacher_seeds.csv` 已从 18 条扩充到 30 条，格式为 `college,name,url`。
- `run_crawler.py` 会读取 seed 中的 `name` 作为可信姓名兜底。如果页面标题或模板把姓名解析错，会用 seed 里的姓名覆盖，并把原解析结果放到 `doc.extra["parsed_name"]`。
- `parser.py` 已经支持将页面栏目拆入 `doc.extra["sections"]`，包括个人资料、个人概况、研究领域、开授课程、科研项目、论文、科研成果、荣誉及奖励、招生信息等。
- `run_crawler.py` 会输出抓取报告，默认路径为输出文件同名的 `.report.json`，用于查看每个 URL 是 `saved`、`fetch_error`、`skipped_nonteacher` 还是 `skipped_duplicate`。
- `fetcher.py` 已经加入编码识别、HTTPS 失败后 HTTP 兜底、失败页不中断批量任务等逻辑。

### 当前验证结果

最近一次完整命令：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/teacher_seeds.csv --max-pages 30 --output data/processed/cs_teachers.jsonl --no-delay
```

当前本地报告显示：

```text
seed_count = 30
report_total = 30
saved = 25
fetch_error = 5
```

注意：由于苏大站点和 VPN 状态不稳定，同一批 URL 多跑几次结果可能不同。之前 18 条 seed 曾出现过全部成功，也出现过部分 502。`fetch_error` 不一定代表 URL 错误，可能只是临时网络或服务器问题。

### 当前待提交改动

截至本记录，工作区有这些未提交改动：

```text
data/seeds/teacher_seeds.csv
docs/archive/team_plan_process_record.md
suda_ir/crawler/fetcher.py
suda_ir/crawler/parser.py
suda_ir/crawler/run_crawler.py
tests/test_parser.py
```

其中 `docs/archive/team_plan_process_record.md` 里有早期分工备注；其他文件都是本轮爬虫相关改动。

### 下一步核心任务

下一步任务不是继续改大框架，而是继续扩充计科院 seed：

1. 继续查找计科院/软件学院教师个人主页 URL。
2. 追加到 `data/seeds/teacher_seeds.csv`，保持三列：

```csv
college,name,url
计算机科学与技术学院（软件学院）,教师姓名,https://web.suda.edu.cn/xxxx/
```

3. 每扩充一批就运行：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/teacher_seeds.csv --max-pages <seed数量> --output data/processed/cs_teachers.jsonl --no-delay
```

4. 查看：

```text
data/processed/cs_teachers.report.json
```

5. 对 `fetch_error` 的 URL 先重跑确认，不要马上删除。对 `saved` 但字段缺失的页面，不一定要修，因为很多老师页面本身信息不完整。

### 给下一个 AI 窗口的提示

请从下面几点继续：

- 先读取 `data/seeds/teacher_seeds.csv`，统计已有 seed，避免重复添加。
- 目标是把计科院 seed 从当前 30 条扩展到尽可能接近 100+ 条。
- 不要把 `data/raw/` 和 `data/processed/` 提交到 GitHub，它们默认用于本地验证。
- 不要强行补齐网页本身没有的信息。字段缺失可以在报告里说明。
- 如果需要新增其他学院，建议另建 seed 文件或在同一个 CSV 中继续追加对应学院名称，后续统一输出 `teachers.jsonl`。

## 2026-05-26 更新：从 web.suda 动态列表发现计科院教师主页

### 最终结果

本轮已将 `data/seeds/teacher_seeds.csv` 收敛为只包含苏州大学教师个人主页站点 `web.suda.edu.cn` 的计科院 seed：

```text
seed_count = 101
domain = web.suda.edu.cn
college = 计算机科学与技术学院（软件学院）
duplicate_url = 0
bad_row = 0
```

此前临时加入过 88 条 `scst.suda.edu.cn` 学院官网导师详情页，用于兜底排查。由于实验课要求是在 `web.suda.edu.cn` 教师个人主页系统中搜索，本轮已移除这些非 `web.suda.edu.cn` URL，只保留刚从教师个人主页系统动态列表抓到的 101 条教师主页。

用于发现 seed 的脚本：

```bash
python scripts/discover_web_suda_seeds.py --max-pages 6 --dry-run --debug-html debug_web_suda.html --debug-ajax-dir debug_ajax
python scripts/discover_web_suda_seeds.py --max-pages 6
```

正式爬教师主页时仍使用原主爬虫：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/teacher_seeds.csv --max-pages 101 --output data/processed/cs_teachers.jsonl --no-delay
```

`debug_web_suda.html` 和 `debug_ajax/` 只是本地排查产物，已加入 `.gitignore`，不要提交。

### 正确入口

计科院教师个人主页列表入口是 `web.suda.edu.cn` 的教师分类查询结果页，不是学院官网 `scst.suda.edu.cn`：

```text
https://web.suda.edu.cn/ssjglm/list.htm?wp_tw_orgId=15&wp_tw_displayStyle=1&wp_tw_complete=1&wp_tw_orgName=<双重URL编码学院名>&wp_tw_language=1&wp_tw_teachStatus=1&wp_tw_deptTecOrder=1
```

其中：

```text
wp_tw_orgId = 15
wp_tw_orgName = 计算机科学与技术学院（软件学院）的双重 URL 编码
wp_tw_language = 1
wp_tw_teachStatus = 1
wp_tw_deptTecOrder = 1
```

注意 `wp_tw_orgName` 在浏览器地址栏里是双重编码，例如 `%25E8%25AE...`。脚本里用 `quote(quote(college_name, safe=""), safe="")` 生成，用 `repeated_unquote()` 读取时还原。

### 为什么浏览器能看到，requests 直接拿不到

这个页面是半动态页面：

- 浏览器地址栏显示的是 `list.htm?...`。
- Python `requests.get(list_url)` 拿到的是空模板，只有导航、搜索框、空的 `<ul id="searchTea"></ul>`。
- 教师卡片不是初始 HTML 直接给出的，而是页面加载后由 JavaScript 调用接口填充。

本地保存的 `debug_web_suda.html` 诊断特征是：

```text
title='苏州大学教师个人主页'
news_box=0
search_data=0
paging=0
contains_generalQuery=True
```

模板里能看到 JS 调用：

```javascript
getRequestData("/_wp3services/generalQuery?queryObj=teacherHome&t=...", 0, 1);
```

所以只用普通 HTML 解析会得到 0 条 seed。必须复现浏览器发出的 AJAX 请求。

### 关键 AJAX 接口与真实 Payload

接口路径：

```text
https://web.suda.edu.cn/_wp3services/generalQuery?queryObj=teacherHome
```

浏览器开发者工具 `Network -> generalQuery -> Payload` 中确认的真实表单字段如下：

```text
queryObj = teacherHome
t = 页面随机数
st = 页面随机数
siteId = 15
pageIndex = 1
rows = 20
articleType = 1
level = 0
deptTecOrder = 1_1
pageEvent = dataSearchByPageIndex
conditions = [
  {"field":"language","value":"1","judge":"="},
  {"field":"ownDepartment","value":"15","judge":"="},
  {"field":"title","value":"","judge":"like"},
  {"field":"published","value":"1","judge":"="}
]
orders = []
returnInfos = [
  {"field":"title","name":"title"},
  {"field":"career","name":"career"},
  {"field":"visitCount","name":"visitCount"},
  {"field":"headerPic","name":"headerPic"},
  {"field":"cnUrl","name":"cnUrl"},
  {"field":"department","name":"department"},
  {"field":"publishStatus","name":"publishStatus"}
]
```

最重要的是这几个点：

- 顶层 `siteId=15` 要保留。
- 过滤条件不是 `orgId=15`，而是 `ownDepartment=15`。
- `published=1` 表示只要已发布主页。
- `returnInfos` 必须请求 `title` 和 `cnUrl`，否则无法生成 `name,url` seed。
- 翻页通过 `pageIndex=1..6`，每页 `rows=20`。

最终响应验证：

```text
total = 101
pageCount = 6
page 1 rows = 20
page 2 rows = 20
page 3 rows = 20
page 4 rows = 20
page 5 rows = 20
page 6 rows = 1
department = 计算机科学与技术学院（软件学院）
```

### 探索过程中的错误结论与修正

1. 一开始搜索了 `scst.suda.edu.cn` 学院官网导师列表，能拿到 88 个学院详情页，但这不是实验课要求的 `web.suda.edu.cn` 教师个人主页系统，因此只适合作为排查参考，最终已移除。

2. 只访问 `https://web.suda.edu.cn/xylb/list.htm` 或 `jsflcx/list.htm` 会得到入口/模板页，不能直接发现计科院 101 个教师主页。

3. 只带 `wp_tw_orgId=15` 不够。脚本曾经得到 `total=9311` 的全校数据，说明后端没有按学院过滤。

4. 只用 `siteId=15` 过滤也不对。接口返回记录里 `siteId` 字段存在，但真正筛选条件需要使用 `ownDepartment=15`。

5. 尝试 JSON POST 时服务端经常返回 503；真实浏览器请求是 `application/x-www-form-urlencoded` 表单方式。因此脚本保留 JSON 尝试，但主要依赖 form POST。

6. 站点偶尔出现 HTTPS EOF、502 或 503。这类错误不一定代表 URL 错，可能是站点临时网络/服务问题。发现 seed 时建议保留 `--debug-ajax-dir`，便于查看接口真实响应。

### 如何扩展到其他学院

扩展其他学院时，不要重新改主爬虫框架，按下面步骤做：

1. 在浏览器打开 `web.suda.edu.cn` 教师个人主页系统，进入目标学院列表。
2. 从地址栏记录目标学院的 `wp_tw_orgId`、`wp_tw_orgName`、`wp_tw_teachStatus`、`wp_tw_deptTecOrder`。
3. 打开开发者工具 `Network`，过滤 `generalQuery`。
4. 刷新页面或点击下一页，复制真实 Payload。
5. 确认 `conditions` 中学院字段。计科院是：

```json
{"field":"ownDepartment","value":"15","judge":"="}
```

其他学院通常只需要替换这个 value 和 `siteId`。

6. 用脚本参数指定入口 URL、学院名和页数：

```bash
python scripts/discover_web_suda_seeds.py \
  --list-url "<目标学院完整 list.htm URL>" \
  --college "<目标学院名称>" \
  --max-pages <页数> \
  --dry-run \
  --debug-html debug_web_suda.html \
  --debug-ajax-dir debug_ajax
```

7. dry-run 检查输出中的 `total`、`pageCount`、每页数量和 `department` 是否与浏览器一致。
8. 确认无误后去掉 `--dry-run` 写入 seed。

如果某个学院 Payload 字段名不同，不要猜分页 URL；优先按浏览器开发者工具里的真实 Payload 修改脚本或增加参数。

## 2026-05-26 更新：计科院真实抓取结果与协作交付

### 抓取命令与最终统计

计科院 101 条 `web.suda.edu.cn` seed 已完成真实教师主页抓取：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/teacher_seeds.csv --max-pages 101 --output data/processed/cs_teachers.jsonl --no-delay
```

最终报告：

```text
seed_count = 101
report_total = 101
saved = 97
skipped_nonteacher = 4
fetch_error = 0
```

也就是说，所有 seed URL 都成功访问，最终保存 97 篇教师文档。未保存的 4 条不是网络失败，而是页面内容不适合作为计科院教师主页入库：

```text
https://web.suda.edu.cn/jjf2/
status_code = 403
reason = too_short
text_head = error / 正在同步中，请稍后再试……

https://web.suda.edu.cn/dt/
status_code = 200
reason = weak_teacher_signals
text_head = 代通 / 教师个人主页 / 师资队伍 ...
说明：seed 名称是邓滔，但页面头显示代通，疑似错主页或旧链接。

https://web.suda.edu.cn/zy2/
status_code = 200
reason = weak_teacher_signals
text_head = 苏州医学院药学院 / 教师个人主页 ...
说明：不是计科院页面。

https://web.suda.edu.cn/gj2/
status_code = 200
reason = weak_teacher_signals
text_head = 苏州医学院 / 教师个人主页 ...
说明：不是计科院页面。
```

### 特殊模板处理

教师主页系统中有部分英文/混合模板页面，不能只依赖中文栏目判断。例如：

- 赵朋朋：英文姓名、英文学院描述。
- 吕强：英文主页入口和 Research Interests。
- 李军辉：中英混合自然语言处理实验室页面。
- 陈宁：英文 homepage / Biography / Research Interest / Publications。

因此 `parser.py` 已经将教师页判定从单一中文特征扩展为分类函数：

```python
classify_teacher_page(text) -> tuple[bool, str]
```

当前保留的特殊规则：

- 中文模板：命中 `教师个人主页`、`个人简介`、`研究方向`、`职称` 等至少 2 个正向特征。
- 英文模板：命中 `homepage`、`biography`、`research interest`、`publications`、`professor`、`school of computer science`、`soochow university` 等至少 3 个英文特征。
- 中英混合模板：页面前部含 `计算机科学与技术学院`，并且出现 `研究兴趣`、`论文发表`、`教授`、`副教授`、`讲师` 等教师信号。
- 硬负例：`正在同步中，请稍后再试`、服务错误页等继续跳过。

`run_crawler.py` 的 report 现在会记录：

```text
reason
page_reason
```

用于说明页面为何保存或跳过，方便写报告时解释数据清洗逻辑。

### 可交给同学处理的文件

主数据：

```text
data/processed/cs_teachers.jsonl
```

质量报告：

```text
data/processed/cs_teachers.report.json
```

原始 HTML：

```text
data/raw/
```

协作建议：

- 先让同学基于 `cs_teachers.jsonl` 做检索、分词、索引或前端展示。
- 需要核查字段质量时，再对照 `cs_teachers.report.json` 和 `data/raw/`。
- `data/raw/` 和 `data/processed/` 已在 `.gitignore` 中，不要直接提交 GitHub。可用压缩包、网盘、课程平台共享。

给同学的简短说明：

```text
计科院 web.suda 教师主页 seed 共 101 条，成功解析 97 条。
剩余 4 条为同步中/疑似错主页/非计科院页面，已在 report 中保留原因。
处理主数据请使用 data/processed/cs_teachers.jsonl；
质量核查请参考 data/processed/cs_teachers.report.json 和 data/raw/ 原始 HTML。
```

## 其他学院抓取操作指南

### 总体流程

其他学院也分两步：

1. 先从 `web.suda.edu.cn` 动态列表发现教师主页 seed。
2. 再用主爬虫抓取 seed 对应的教师主页。

不要直接改主爬虫框架。发现 seed 的动态列表逻辑在：

```text
scripts/discover_web_suda_seeds.py
```

教师主页抓取逻辑仍在：

```text
suda_ir/crawler/run_crawler.py
```

### 第一步：找目标学院的列表参数

1. 浏览器打开苏州大学教师个人主页系统：

```text
https://web.suda.edu.cn/
```

2. 进入“学院列表”或“教师分类查询”，点目标学院。

3. 记录浏览器地址栏中的完整 URL，重点是：

```text
wp_tw_orgId
wp_tw_orgName
wp_tw_language
wp_tw_teachStatus
wp_tw_deptTecOrder
```

4. 打开开发者工具：

```text
F12 -> Network -> 过滤 generalQuery
```

5. 刷新页面或点击下一页，点开 `generalQuery?queryObj=teacherHome...` 请求。

6. 查看 Payload / Form Data，确认：

```text
siteId
pageIndex
rows
conditions
returnInfos
deptTecOrder
pageEvent
```

计科院已经验证过的关键条件是：

```json
{"field":"ownDepartment","value":"15","judge":"="}
```

其他学院一般只需要替换 `15` 为对应学院 ID。但如果浏览器 Payload 里字段名不同，以浏览器真实 Payload 为准。

### 第二步：dry-run 发现 seed

用目标学院完整 URL、学院名和页数运行：

```bash
python scripts/discover_web_suda_seeds.py \
  --list-url "<目标学院完整 list.htm URL>" \
  --college "<目标学院名称>" \
  --max-pages <浏览器显示页数> \
  --dry-run \
  --debug-html debug_web_suda.html \
  --debug-ajax-dir debug_ajax
```

检查输出：

```text
AJAX page 1: N seeds via form
page 2: N seeds via form
...
discovered unique new seeds: N
```

同时检查 `debug_ajax/ajax_page*_form.txt`：

```text
total 是否等于目标学院教师主页总数
pageCount 是否等于浏览器显示页数
data[].department 是否为目标学院
data[].cnUrl 是否为 web.suda.edu.cn 教师主页
```

如果出现 `total=9311`，说明接口没有按学院过滤，Payload 没对齐，需要回到开发者工具核对 `conditions`。

### 第三步：正式写入 seed

确认 dry-run 正常后去掉 `--dry-run`：

```bash
python scripts/discover_web_suda_seeds.py \
  --list-url "<目标学院完整 list.htm URL>" \
  --college "<目标学院名称>" \
  --max-pages <浏览器显示页数>
```

默认会追加到：

```text
data/seeds/teacher_seeds.csv
```

如果希望每个学院单独维护 seed，可以使用：

```bash
python scripts/discover_web_suda_seeds.py \
  --list-url "<目标学院完整 list.htm URL>" \
  --college "<目标学院名称>" \
  --max-pages <页数> \
  --output data/seeds/<college>_teacher_seeds.csv
```

### 第四步：真实抓取教师主页

单学院 seed：

```bash
python -m suda_ir.crawler.run_crawler \
  --seed-file data/seeds/<college>_teacher_seeds.csv \
  --max-pages <seed数量> \
  --output data/processed/<college>_teachers.jsonl \
  --no-delay
```

统一 seed：

```bash
python -m suda_ir.crawler.run_crawler \
  --seed-file data/seeds/teacher_seeds.csv \
  --max-pages <seed数量> \
  --output data/processed/teachers.jsonl \
  --no-delay
```

### 第五步：检查报告

统计状态：

```bash
python -c "import json; from collections import Counter; from pathlib import Path; r=json.loads(Path('data/processed/<college>_teachers.report.json').read_text(encoding='utf-8')); print('total',len(r)); print(Counter(x.get('status') for x in r)); [print(x.get('status'), x.get('status_code'), x.get('reason',''), x.get('url'), (x.get('text_head') or x.get('error') or '')[:120].replace(chr(10),' | ')) for x in r if x.get('status')!='saved']"
```

判断原则：

- `fetch_error`：先重跑确认，不要马上删除 URL。
- `skipped_nonteacher`：看 `reason` 和 `text_head`，判断是错主页、同步页、空壳页，还是特殊模板误判。
- 特殊模板误判：优先在 `parser.py` 增加有边界的正向规则，并补测试。
- 错主页/非本学院页面：保留在 report 中说明，不强行入库。

### 常见问题

1. `requests.get(list.htm)` 只有空模板：正常，动态列表必须走 `generalQuery`。

2. AJAX 返回 `total=9311`：没有按学院过滤，Payload 不对。

3. JSON POST 返回 503：正常浏览器使用 form POST，脚本主要依赖 form 方式。

4. 某些主页 403 或“正在同步中”：记录为不可用，不要强行保存。

5. 某些主页字段缺失：可以接受，很多教师主页本身信息不完整。

## 2026-05-26 更新：多学院文件夹约定

为避免不同学院数据混在一起，后续按下面结构存放：

```text
data/seeds/colleges/cs_teacher_seeds.csv
data/seeds/colleges/nano_teacher_seeds.csv

data/processed/cs/cs_teachers.jsonl
data/processed/cs/cs_teachers.report.json
data/processed/nano/nano_teachers.jsonl
data/processed/nano/nano_teachers.report.json

data/raw/cs/
data/raw/nano/
```

兼容旧脚本路径，根目录下仍保留：

```text
data/seeds/teacher_seeds.csv
data/seeds/nano_teacher_seeds.csv
data/processed/cs_teachers.jsonl
data/processed/cs_teachers.report.json
```

但后续协作时优先使用 `data/seeds/colleges/`、`data/processed/<college>/`、`data/raw/<college>/`。

### 纳米学院示例

纳米学院浏览器 Payload 中：

```text
siteId = 99
conditions 中 ownDepartment = 99
```

发现纳米学院 seed：

```bash
python scripts/discover_web_suda_seeds.py --org-id 99 --college "纳米科学技术学院" --output data/seeds/colleges/nano_teacher_seeds.csv --dry-run --debug-html debug/nano_web_suda.html --debug-ajax-dir debug/nano_ajax --ajax-page-cap 20
python scripts/discover_web_suda_seeds.py --org-id 99 --college "纳米科学技术学院" --output data/seeds/colleges/nano_teacher_seeds.csv --ajax-page-cap 20
```

查看 seed 数量：

```bash
python -c "import csv; from pathlib import Path; rows=list(csv.DictReader(Path('data/seeds/colleges/nano_teacher_seeds.csv').open(encoding='utf-8-sig'))); print(len(rows)); print(rows[:5])"
```

纳米学院当前 seed 数量为 17。因此真实抓取时不要写 `<seed数量>`，要写数字：

```bash
python -m suda_ir.crawler.run_crawler --seed-file data/seeds/colleges/nano_teacher_seeds.csv --max-pages 17 --output data/processed/nano/nano_teachers.jsonl --raw-dir data/raw/nano --no-delay
```

统计报告：

```bash
python -c "import json; from collections import Counter; from pathlib import Path; r=json.loads(Path('data/processed/nano/nano_teachers.report.json').read_text(encoding='utf-8')); print('total',len(r)); print(Counter(x.get('status') for x in r)); [print(x.get('status'), x.get('status_code'), x.get('reason',''), x.get('url'), (x.get('text_head') or x.get('error') or '')[:120].replace(chr(10),' | ')) for x in r if x.get('status')!='saved']"
```

## 2026-05-26 更新：中文目录规范与数学科学学院

后续多学院数据统一按中文学院名分目录保存，便于和同学协作时直接识别来源：

```text
data/seeds/colleges/计算机科学与技术学院/teacher_seeds.csv
data/seeds/colleges/功能纳米与软物质研究院/teacher_seeds.csv
data/seeds/colleges/数学科学学院/teacher_seeds.csv

data/processed/计算机科学与技术学院/
data/processed/功能纳米与软物质研究院/
data/processed/数学科学学院/

data/raw/计算机科学与技术学院/
data/raw/功能纳米与软物质研究院/
data/raw/数学科学学院/
```

当前已核验结果：

```text
计算机科学与技术学院：seed 101 条，raw HTML 101 个，crawl report 101 条，saved 97 条。
功能纳米与软物质研究院：seed 17 条，raw HTML 17 个，crawl report 17 条，saved 17 条。
```

数学科学学院浏览器 Payload 中的关键参数：

```text
siteId = 78
conditions 中 ownDepartment = 78
rows = 20
pageEvent = dataSearchByPageIndex
```

先发现数学科学学院 seed：

```bash
python scripts/discover_web_suda_seeds.py --org-id 78 --college "数学科学学院" --output "data/seeds/colleges/数学科学学院/teacher_seeds.csv" --max-pages 10 --dry-run --debug-html "debug/math_web_suda.html" --debug-ajax-dir "debug/math_ajax"
```

确认 dry-run 输出的是数学学院教师后，去掉 `--dry-run` 正式写入：

```bash
python scripts/discover_web_suda_seeds.py --org-id 78 --college "数学科学学院" --output "data/seeds/colleges/数学科学学院/teacher_seeds.csv" --max-pages 10 --debug-html "debug/math_web_suda.html" --debug-ajax-dir "debug/math_ajax"
```

检查 seed 数量：

```bash
python -c "import csv; from pathlib import Path; p=Path('data/seeds/colleges/数学科学学院/teacher_seeds.csv'); rows=list(csv.DictReader(p.open(encoding='utf-8-sig'))); print(len(rows)); print(rows[:5])"
```

真实抓取时把 `<seed数量>` 换成上一步打印出来的数字，不要保留尖括号：

```bash
python -m suda_ir.crawler.run_crawler --seed-file "data/seeds/colleges/数学科学学院/teacher_seeds.csv" --max-pages <seed数量> --output "data/processed/数学科学学院/math_teachers.jsonl" --raw-dir "data/raw/数学科学学院" --no-delay
```

检查数学学院抓取报告：

```bash
python -c "import json; from collections import Counter; from pathlib import Path; r=json.loads(Path('data/processed/数学科学学院/math_teachers.report.json').read_text(encoding='utf-8')); print('total',len(r)); print(Counter(x.get('status') for x in r)); [print(x.get('status'), x.get('status_code'), x.get('reason',''), x.get('url'), (x.get('text_head') or x.get('error') or '')[:120].replace(chr(10),' | ')) for x in r if x.get('status')!='saved']"
```

数学科学学院当前结果：

```text
数学科学学院：seed 66 条，crawl report 66 条，saved 64 条，skipped_nonteacher 2 条。
```

其中 `https://web.suda.edu.cn/hfma/index.html` 是马欢飞老师英文/中文混合特殊模板，文本包含 `Huanfei Ma's Homepage`、`数学科学学院`、`研究兴趣`、`论文与著作`，已在 `parser.py` 中加入混合模板正向规则。当前混合模板规则要求页面前部出现已知学院名，并且页面包含 `研究兴趣`、`论文发表`、`论文与著作`、职称等正向信号；已覆盖计算机科学与技术学院、功能纳米与软物质研究院、数学科学学院、物理科学与技术学院、未来科学与工程学院。剩余两条 `lf2/`、`zq2/` 分别指向继续教育学院和苏州医学院药学院，是跨学院错误主页，保留在 report 中说明，不强行入库。

## 2026-05-26 更新：物理科学与技术学院

物理科学与技术学院浏览器 Payload 中的关键参数：

```text
siteId = 79
conditions 中 ownDepartment = 79
rows = 20
pageEvent = dataSearchByPageIndex
```

目录约定：

```text
data/seeds/colleges/物理科学与技术学院/teacher_seeds.csv
data/processed/物理科学与技术学院/
data/raw/物理科学与技术学院/
```

先 dry-run 发现 seed：

```bash
python scripts/discover_web_suda_seeds.py --org-id 79 --college "物理科学与技术学院" --output "data/seeds/colleges/物理科学与技术学院/teacher_seeds.csv" --max-pages 10 --dry-run --debug-html "debug/physics_web_suda.html" --debug-ajax-dir "debug/physics_ajax"
```

确认输出是物理学院教师后正式写入：

```bash
python scripts/discover_web_suda_seeds.py --org-id 79 --college "物理科学与技术学院" --output "data/seeds/colleges/物理科学与技术学院/teacher_seeds.csv" --max-pages 10 --debug-html "debug/physics_web_suda.html" --debug-ajax-dir "debug/physics_ajax"
```

检查 seed 数量：

```bash
python -c "import csv; from pathlib import Path; p=Path('data/seeds/colleges/物理科学与技术学院/teacher_seeds.csv'); rows=list(csv.DictReader(p.open(encoding='utf-8-sig'))); print(len(rows)); print(rows[:5])"
```

真实抓取时把 `<seed数量>` 换成上一步打印出来的数字：

```bash
python -m suda_ir.crawler.run_crawler --seed-file "data/seeds/colleges/物理科学与技术学院/teacher_seeds.csv" --max-pages <seed数量> --output "data/processed/物理科学与技术学院/physics_teachers.jsonl" --raw-dir "data/raw/物理科学与技术学院" --no-delay
```

检查物理学院抓取报告：

```bash
python -c "import json; from collections import Counter; from pathlib import Path; r=json.loads(Path('data/processed/物理科学与技术学院/physics_teachers.report.json').read_text(encoding='utf-8')); print('total',len(r)); print(Counter(x.get('status') for x in r)); [print(x.get('status'), x.get('status_code'), x.get('reason',''), x.get('url'), (x.get('text_head') or x.get('error') or '')[:120].replace(chr(10),' | ')) for x in r if x.get('status')!='saved']"
```

物理科学与技术学院当前结果：

```text
物理科学与技术学院：seed 61 条，crawl report 61 条，saved 61 条，skipped_nonteacher 0 条。
```

## 2026-05-26 更新：未来科学与工程学院

未来科学与工程学院浏览器 Payload 中的关键参数：

```text
siteId = 179
conditions 中 ownDepartment = 179
rows = 20
pageEvent = dataSearchByPageIndex
```

目录约定：

```text
data/seeds/colleges/未来科学与工程学院/teacher_seeds.csv
data/processed/未来科学与工程学院/
data/raw/未来科学与工程学院/
```

先 dry-run 发现 seed：

```bash
python scripts/discover_web_suda_seeds.py --org-id 179 --college "未来科学与工程学院" --output "data/seeds/colleges/未来科学与工程学院/teacher_seeds.csv" --max-pages 10 --dry-run --debug-html "debug/future_web_suda.html" --debug-ajax-dir "debug/future_ajax"
```

确认输出是未来科学与工程学院教师后正式写入：

```bash
python scripts/discover_web_suda_seeds.py --org-id 179 --college "未来科学与工程学院" --output "data/seeds/colleges/未来科学与工程学院/teacher_seeds.csv" --max-pages 10 --debug-html "debug/future_web_suda.html" --debug-ajax-dir "debug/future_ajax"
```

检查 seed 数量：

```bash
python -c "import csv; from pathlib import Path; p=Path('data/seeds/colleges/未来科学与工程学院/teacher_seeds.csv'); rows=list(csv.DictReader(p.open(encoding='utf-8-sig'))); print(len(rows)); print(rows[:5])"
```

真实抓取时把 `<seed数量>` 换成上一步打印出来的数字：

```bash
python -m suda_ir.crawler.run_crawler --seed-file "data/seeds/colleges/未来科学与工程学院/teacher_seeds.csv" --max-pages <seed数量> --output "data/processed/未来科学与工程学院/future_teachers.jsonl" --raw-dir "data/raw/未来科学与工程学院" --no-delay
```

检查未来科学与工程学院抓取报告：

```bash
python -c "import json; from collections import Counter; from pathlib import Path; r=json.loads(Path('data/processed/未来科学与工程学院/future_teachers.report.json').read_text(encoding='utf-8')); print('total',len(r)); print(Counter(x.get('status') for x in r)); [print(x.get('status'), x.get('status_code'), x.get('reason',''), x.get('url'), (x.get('text_head') or x.get('error') or '')[:120].replace(chr(10),' | ')) for x in r if x.get('status')!='saved']"
```

未来科学与工程学院当前结果：

```text
未来科学与工程学院：seed 51 条，crawl report 51 条，saved 44 条，skipped_nonteacher 7 条。
```

跳过项判定：

```text
朱铭鲁 zml2：未来科学与工程学院空壳模板，仅学院名、教师个人主页、版权信息，无个人内容。
朱梦尧 zmy2：未来科学与工程学院空壳模板，仅学院名、版权信息，无个人内容。
王胜 ws2：跳转/返回苏州医学院模板页。
张朝阳 zcy2：跳转/返回苏州医学院模板页。
刘于一 lyy2：跳转/返回苏州医学院模板页。
李璐 ll2：跳转/返回王健法学院模板页。
辛亮 xl2：跳转/返回苏州医学院模板页。
```

上述 7 条不强行入库，保留在 report 中作为无效或空壳主页说明。

## 2026-05-26 更新：五个学院阶段性交接与 GitHub 提交流程

当前已经完成 5 个学院的教师主页发现与真实抓取：

```text
计算机科学与技术学院：seed 101，raw HTML 101，report 101，saved 97，skipped 4。
功能纳米与软物质研究院：seed 17，raw HTML 17，report 17，saved 17，skipped 0。
数学科学学院：seed 66，raw HTML 66，report 66，saved 64，skipped 2。
物理科学与技术学院：seed 61，raw HTML 61，report 61，saved 61，skipped 0。
未来科学与工程学院：seed 51，raw HTML 51，report 51，saved 44，skipped 7。

合计：seed/raw HTML 296，saved 283，skipped 13。
```

GitHub 提交原则：

```text
提交：爬虫代码、seed CSV、测试、文档、必要截图。
不提交：data/raw/、data/processed/、debug/、debug_ajax/、debug_web_suda.html。
```

原因：`data/raw/` 是网页原始 HTML，`data/processed/` 是运行产物，体积会继续增长，也可能包含网页上的联系方式等敏感信息。当前 `.gitignore` 已忽略这些目录，GitHub 上保留可复现实验的代码、seed 和说明即可。

推荐提交文件：

```text
.gitignore
scripts/discover_web_suda_seeds.py
suda_ir/crawler/parser.py
suda_ir/crawler/run_crawler.py
tests/test_parser.py
docs/crawler_notes.md
data/seeds/teacher_seeds.csv
data/seeds/nano_teacher_seeds.csv
data/seeds/colleges/
```

提交前检查：

```bash
git status --short
git status --short --ignored
```

确认 `data/raw/`、`data/processed/` 出现在 ignored 或不出现在待提交列表中。不要使用 `git add .`，建议显式添加：

```bash
git add .gitignore scripts/discover_web_suda_seeds.py suda_ir/crawler/parser.py suda_ir/crawler/run_crawler.py tests/test_parser.py docs/crawler_notes.md data/seeds/teacher_seeds.csv data/seeds/nano_teacher_seeds.csv data/seeds/colleges
git status --short
git commit -m "Expand web.suda teacher crawler seeds"
git push
```

如果 `docs/archive/team_plan_process_record.md` 中也记录了分工或进度，可以一并提交：

```bash
git add docs/archive/team_plan_process_record.md
```

与清洗同学交接时，不通过 GitHub 传原始 HTML，建议用压缩包或共享盘。推荐交接目录：

```text
data/raw/计算机科学与技术学院/
data/raw/功能纳米与软物质研究院/
data/raw/数学科学学院/
data/raw/物理科学与技术学院/
data/raw/未来科学与工程学院/

data/processed/计算机科学与技术学院/
data/processed/功能纳米与软物质研究院/
data/processed/数学科学学院/
data/processed/物理科学与技术学院/
data/processed/未来科学与工程学院/

data/seeds/colleges/
docs/crawler_notes.md
```

Windows 下可生成一个交接压缩包：

```powershell
Compress-Archive -Path "data/raw/计算机科学与技术学院","data/raw/功能纳米与软物质研究院","data/raw/数学科学学院","data/raw/物理科学与技术学院","data/raw/未来科学与工程学院","data/processed/计算机科学与技术学院","data/processed/功能纳米与软物质研究院","data/processed/数学科学学院","data/processed/物理科学与技术学院","data/processed/未来科学与工程学院","data/seeds/colleges","docs/crawler_notes.md" -DestinationPath "handoff_teacher_html_5_colleges_2026-05-26.zip" -Force
```

给清洗同学的说明：

```text
1. 每个学院一个独立 raw 目录，目录下每个 HTML 对应一个教师主页 URL。
2. 每个学院一个 processed 目录，jsonl 是当前解析结果，report.json 是抓取状态报告。
3. 清洗时优先读 processed/*.jsonl；字段缺失是网页本身不完整导致，允许为空。
4. 遇到 skipped_nonteacher 不要直接当教师数据清洗，先看 report 中 reason/text_head。
5. 跨学院错误页、空壳页保留在 report 中用于说明，不进入最终教师数据集。
6. 后续新增学院时复用 `scripts/discover_web_suda_seeds.py --org-id <id> --college "<学院名>"`，并按中文学院名分目录保存。
```
