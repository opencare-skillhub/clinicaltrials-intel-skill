# ChiCTR 中国本地临床试验模块 — 设计说明

分支：`feat/chictr-cn-trials`（**不合并前不影响 `main` 默认 CTGov 链路**）  
日期：2026-07-18

---

## 1. 背景与问题

本仓库现有抓取完全依赖 **ClinicalTrials.gov API v2**。  
对中国本土试验存在三类缺口：

| 缺口 | 说明 |
|------|------|
| 覆盖不全 | 部分仅在 **ChiCTR（中国临床试验注册中心）** 注册，未同步/未镜像到 CTGov |
| 字段语言 | ChiCTR 中文标题、PI、伦理、入排更贴近国内患者可读性 |
| 时效 | 新注册试验可能先出现在 chictr.org.cn，WHO/CTGov 镜像滞后 |

目标：在**不干扰 main 默认流程**的前提下，补齐可插拔的 **ChiCTR 中国源**。

---

## 2. 数据源评估

### 2.1 chictr.org.cn（一手源）

| 项 | 结论 |
|----|------|
| 入口 | 搜索：`/searchproj.html`、`/searchprojen.html`；详情：`/showproj.html?proj=` / `showprojen.html` |
| 公开 API | **无稳定官方 REST API**（本次检索未见官方开放接口文档） |
| 反爬 | 强：WAF / 滑动验证码 / 无浏览器 UA 易 405；高频易触发挑战 |
| 解析 | 列表页 `table.table1`；详情页 `td.left_title` 标签-值表 |
| 适用 | 最新、最全中文字段；成本高（浏览器或 FlareSolverr） |

现场探针（本机）：无浏览器直接 GET 搜索页返回 **405**；与历史脚本「必须浏览器自动化」结论一致。

### 2.2 WHO ICTRP（镜像源）

| 项 | 结论 |
|----|------|
| 入口 | `https://trialsearch.who.int/`（Trial2.aspx?TrialID=ChiCTR…） |
| 优点 | 可走普通 HTTP；ChiCTR 记录会进 ICTRP；适合「无浏览器」基线 |
| 缺点 | 站点稳定性一般（超时/运行时错误偶发）；字段英文为主；同步有延迟 |
| 适用 | **默认 fallback / 零依赖基线** |

### 2.3 ClinicalTrials.gov 中国中心过滤（已有能力）

```text
query.locn=China + SEARCH_CONDITION + KEYWORDS
```

| 项 | 结论 |
|----|------|
| 优点 | 已稳定集成；API 正式、结构化 |
| 缺点 | 只覆盖「在 CTGov 注册且标了 China 地点」的试验，**不能替代 ChiCTR** |
| 定位 | 与 ChiCTR **互补**，不是替代 |

### 2.4 药监相关 chinadrugtrials.org.cn

CDE 药物临床试验登记与信息公示平台，偏**药物试验**监管视角，字段与 ChiCTR 不同。  
本阶段 **不纳入 MVP**，可作为后续第二中国源。

---

## 3. 开源项目对比（gh + 网页调研）

> Tavily 脚本本机 SSL 证书失败；改用 `gh search/api` + raw GitHub + jina/curl 探针。  
> agent-reach：`github` 后端可用（`gh CLI`）。

| 项目 | 星标/状态 | 技术路线 | 可借鉴点 | 风险 |
|------|-----------|----------|----------|------|
| [PancrePal-xiaoyibao/chictr-mcp-server](https://github.com/PancrePal-xiaoyibao/chictr-mcp-server)（即本地 `~/Downloads/chictr_trials`） | ~5★，活跃 2026-07 | Playwright + cheerio + SQLite 双层缓存 + 挑战状态机 + MCP | 列表/详情解析、验证码检测、限速熔断、project_id 映射 | 重依赖浏览器；headless 难过滑块 |
| [JAGAN666/chictr-mcp](https://github.com/JAGAN666/chictr-mcp) | 0★，2026-03 | **双源**：FlareSolverr→ChiCTR 主，**WHO ICTRP 备**；可选 CTGov 交叉验证 | **分层数据源架构最值得抄**；质量分；RAG 文档形状 | 仓库较新、社区热度低；FlareSolverr 运维成本 |
| [luyang93/clinical-trials-scrapy](https://github.com/luyang93/clinical-trials-scrapy) | 2★，**archived** | Scrapy 爬 chictr + chinadrugtrials | 历史选择器参考 | 已归档，站点改版后大概率失效 |
| [feverbase/feverbase](https://github.com/feverbase/feverbase) `fetch/faucets/chictr.py` | 9★（项目整体） | 旧站 `searchprojen.aspx` + requests | 说明早期可用纯 HTTP | URL/结构已过时 |
| [serghiou/rchictr](https://github.com/serghiou/rchictr) | 0★ | R 包抽 ChiCTR | 字段清单参考 | R 生态，难直接复用 |
| [CancerDAO/clinical-trial-matching](https://github.com/CancerDAO/clinical-trial-matching) | 0★ | CTGov + ChiCTR 双源匹配 skill | 产品形态：双源 + LLM 分析 | 实现深度待核 |

**结论：没有「高星、生产级、免运维」的 ChiCTR 官方客户端。**  
相对最可取的架构是 JAGAN 的 **双源瀑布** + 你方 MCP 的 **解析/缓存/挑战机** 经验。

本地 `chictr_trials` 不完善点（对照生产情报系统）：

1. 默认强依赖 Playwright，部署重  
2. 验证码只能提示/人工恢复，难无人值守 cron  
3. 输出 MCP 形状，未对接本仓库 `content_builder` / GeWe 推送  
4. 与 CTGov 结果无统一 schema、无 NCT/ChiCTR 去重  
5. 搜索默认 `createyear=当前年`，易漏历史在研  
6. 与 `pancreatic_targets.yaml` 靶点体系未打通  

---

## 4. 目标架构（本分支）

```
                    ┌─────────────────────────┐
   CLI / 菜单(可选)  │  main --source chictr    │  ← 默认关闭，不影响 main 行为
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │   lib/chictr/client.py  │  瀑布查询 + 缓存
                    └───────────┬─────────────┘
           ┌────────────────────┼────────────────────┐
           ▼                    ▼                    ▼
   ┌───────────────┐   ┌────────────────┐   ┌─────────────────┐
   │ provider_who  │   │ provider_direct│   │ (future CDE)    │
   │ ICTRP HTTP    │   │ browser/flare  │   │ chinadrugtrials │
   └───────┬───────┘   └───────┬────────┘   └─────────────────┘
           └────────────────────┼────────────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  normalize → UnifiedTrial│
                    │  (与 CTGov 推送字段对齐)  │
                    └───────────┬─────────────┘
                                ▼
              content_builder / GeWe / FastGPT（复用，不强绑）
```

### 4.1 Provider 优先级（可配置）

| 顺序 | Provider | 何时用 |
|------|----------|--------|
| 1 | `who_ictrp` | 默认；无浏览器 |
| 2 | `chictr_direct` | 设置 `CHICTR_DIRECT=1` 且具备 Playwright/FlareSolverr |
| 3 | 本地缓存 | 任一源成功后写入；挑战/超时时先读缓存 |

失败策略：**软失败**（返回 `[]` + 日志），不抛崩主流程。

### 4.2 统一模型 `UnifiedTrial`

最小推送字段（对齐现有日报）：

- `id`：ChiCTR 号（如 `ChiCTR2500111173`）
- `title` / `title_cn`
- `status`（招募状态）
- `condition` / `intervention`
- `sponsor` / `institution`
- `phase` / `study_type`
- `registration_date` / `last_update`
- `url`（优先 ChiCTR，其次 WHO）
- `source`：`chictr` | `who_ictrp`
- `raw`：原始 dict（调试）

适配层可把 `UnifiedTrial` 转成 **伪 CTGov study 结构**（仅填充 `content_builder` 用到的路径），从而复用翻译与推送，而不改 GeWe 渠道代码。

### 4.3 与现有 CTGov 的关系

| 模式 | 行为 |
|------|------|
| 默认（main 现状） | 只走 CTGov |
| `--source chictr` | 只走 ChiCTR 模块 |
| `--source both`（后续） | 双源抓取后按 id/标题模糊去重合并 |

**合并前规则草案**：ChiCTR 号与 NCT secondary id 交叉；标题+申办方模糊匹配；保留双方 URL。

### 4.4 合规与频率

- 仅用于情报检索/患者教育，遵守站点 ToS，控制 QPS  
- 默认间隔 ≥ 1.5–5s；缓存优先  
- 不实现验证码自动破解；挑战时冷却并降级 WHO/缓存  
- 不在仓库提交 Cookie/会话  

---

## 5. 模块落地（本分支文件）

```
lib/chictr/
  __init__.py          # 对外 API
  models.py            # UnifiedTrial / SearchQuery
  cache.py             # 简单 JSON 文件缓存（cache/chictr/）
  client.py            # 瀑布门面 search_trials / get_detail
  providers/
    base.py
    who_ictrp.py       # WHO ICTRP HTTP
    chictr_html.py     # 纯 HTML 解析（列表/详情选择器，供 direct 用）
  adapt_ctgov.py       # UnifiedTrial → 伪 CTGov study 结构
docs/chictr-design.md  # 本文
tests/test_chictr_*.py
fixtures/chictr/*.html # 离线解析夹具
```

可选后续（不阻塞 MVP）：

- 包装本地 `chictr_trials` MCP 为 subprocess provider  
- `main.py` 菜单「ChiCTR 中国源」开关（默认隐藏或明确标注实验）  
- 与 `pancreatic_targets.yaml` 中文病种词扩展  

---

## 6. MVP 验收标准

1. `from lib.chictr import search_trials` 可 import  
2. 离线夹具解析列表/详情字段测试通过（不依赖外网）  
3. 在线 WHO 可用时：关键词「胰腺癌」或「pancreatic」能返回 ≥0 条（网络失败记 soft-fail，不红）  
4. `adapt_to_ctgov_study` 输出可被 `get_nct_id` 类逻辑读到 id（ChiCTR 号）  
5. **默认** `python3 main.py --10 --china --send-gewe-txt` 行为与合并前一致（不启用 ChiCTR）  

---

## 7. 推荐实施节奏

| 阶段 | 内容 | 风险 |
|------|------|------|
| P0（本分支） | 模型 + HTML 解析 + WHO provider 骨架 + 适配 + 设计文档 + 单测 | 低 |
| P1 | 可选 Playwright direct（复用 chictr_trials 经验）或调用 MCP | 中（验证码） |
| P2 | main 菜单/CLI `--source`、双源去重、日报标注来源徽章 | 低 |
| P3 | chinadrugtrials、批量同步 FastGPT | 中 |

---

## 8. 参考链接

- ChiCTR：https://www.chictr.org.cn/  
- WHO ICTRP：https://www.who.int/clinical-trials-registry-platform  
- 本地实现：`/Users/qinxiaoqiang/Downloads/chictr_trials`  
- npm：`chictr-mcp-server`（PancrePal）  
- 双源参考：https://github.com/JAGAN666/chictr-mcp  
