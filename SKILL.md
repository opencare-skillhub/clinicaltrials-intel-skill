---
name: clinicaltrials-intel
description: 胰腺癌临床试验情报自动化系统的开发与运维技能。从 ClinicalTrials.gov 抓取试验、双路径处理（TG 推送 + 全文精翻）、清洗，并同步到 FastGPT RAG 知识库；支持 Telegram / GeWe 微信群 / 飞书 / FastGPT 多渠道推送。当用户提到临床试验订阅推送、ClinicalTrials.gov 抓取翻译、FastGPT 知识库同步、GeWe/飞书/TG 推送渠道开发、 pancreatic cancer 情报系统、config.yaml 配置或 .env 模板时，使用此技能——即使用户没有明确说"clinicaltrials-intel"。
---

# Clinical Trials Intel Skill

面向胰腺癌（Pancreatic Cancer）临床试验情报自动化系统的开发与运维技能。本技能沉淀了 `clinicaltrials推送和订阅` 项目的架构、运行流程、配置规范和开发约定，帮助在该项目（或同类系统）上快速开发与排障。

---

## 系统是什么

一套闭环情报系统，核心流程：

```
ClinicalTrials.gov API
   └─ 阶段1: 批量处理（抓取 → 精翻 → 落地）
        ├─ output/{Date}-Pancreatic_Cancer/{NCT}.json   (sync_status=pending)
        ├─ cn/{date}-{NCT}-{title}-zh.md                 (中文精翻，FastGPT 同步源)
        └─ telegram_push_report.txt                       (TG/GeWe 简报)
   └─ 阶段2: 多渠道推送（各自消费独立内容源）
        ├─ TG / GeWe 文字   ← 消费 summary + detail_groups
        ├─ GeWe 卡片 / 飞书 ← 消费 study 对象
        └─ FastGPT 知识库   ← 消费 cn/*-zh.md
```

**关键契约（改动代码前必须理解）**：

- JSON 的 `sync_status` 字段是 RAG 与抓取阶段的隐式契约：`pending` → 待翻译，`synced` → 已处理。
- 中文精翻文件统一加 `-zh` 后缀，这是 FastGPT 同步的过滤标识。
- NCT 编号（`NCT\d{8}`）是去重唯一键，从文件名提取，与文件名变化无关。
- 阶段 1 与阶段 2 必须分离：阶段 1 批量落地完成后，阶段 2 各渠道才消费。不要写成"单篇下载翻译就推送"。

---

## 项目布局（改代码先看这里）

```
main.py                  # 主控台：交互菜单 + 自动流程(--auto)
push_existing_report.py  # 独立推送已有报告（补发/测试场景）
daily_ctgov_check_tgbot.py   # 阶段1：抓取 + TG 简报
ctgov_full_sync_rag.py       # RAG 精翻引擎（JSON→en/cn Markdown）
fastgpt_sync.py              # FastGPT 同步引擎（NCT去重+Hash指纹）
config.yaml                  # 渠道开关 + 流程行为 + 翻译模型 fallback 链
.env                         # 凭据（永不提交 git）
lib/
├── config.py            # 配置加载（config.yaml + .env）
├── ctgov_api.py         # ClinicalTrials.gov API v2 封装
├── content_builder.py   # 推送内容构建（summary/detail_groups）
├── llm_client.py        # OpenAI 兼容多模型 fallback 客户端
├── study_data.py        # study 对象处理
├── text_utils.py        # Markdown→纯文本、分批、清洗
└── channels/            # 推送渠道（每个渠道一个模块）
    ├── telegram.py
    ├── gewe.py          # GeWe 微信群（文字+卡片）
    ├── feishu.py        # 飞书交互卡片
    └── fastgpt.py
output/{Date}-Pancreatic_Cancer/   # 落地根目录（gitignore）
├── cn/  en/  {NCT}.json  telegram_push_report.txt
data/fastgpt_sync_state.json       # 同步指纹库（gitignore）
```

新增/修改推送渠道时，统一在 `lib/channels/` 下做模块，**不要**在主脚本里堆 if-else。这是 v2.2.0 已经确立的约定。

---

## 配置体系（三层，按优先级）

1. **`.env`**（凭据，本地存在，禁止提交 git）—— API key、bot token、群 ID。
2. **`config.yaml`**（行为与开关，提交 git）—— 渠道默认开关、流程行为、翻译模型 fallback 链。
3. **命令行参数**（最高优先级）—— `--send-xxx` / `--no-channels` 覆盖 config.yaml 默认值。

翻译模型走 **fallback 链**（见 `config.yaml` 的 `translate_models`），顺序即优先级，每个模型走 OpenAI 兼容协议，`api_key_env` 引用 `.env` 里的变量名（敏感信息不写进 yaml）。向后兼容旧的 `LLM_PROVIDER` + 小写变量。

> 配置文件模板见 `assets/config.yaml.template` 和 `assets/.env.template`。新环境部署时复制模板填值，**不要**把真实凭据写进模板。

---

## 日常运行

```bash
# 激活虚拟环境（推荐 uv）
source .venv/bin/activate

# 交互式菜单（默认仅上传当天）
python3 main.py

# 主菜单快捷推送（无参数进入 interactive_menu）：
#   3️⃣  10 个最近中国试验 → 微信文字 (gewe_txt)   ← 默认开启，开箱即用
#   4️⃣  10 个最近中国试验 → 微信卡片 (gewe_card)  ← 默认关闭，需先在 config.yaml 设 channels.gewe_card: true
# 两个选项都复用 run_cli_mode 两阶段流程（china=True, latest=True, top=10）。
# 选项 4 在卡片关闭时会拦在抓取前并提示配置，不白跑流程。

# 自动全流程（适合 cron）
python3 main.py --auto

# 推送已有报告（补发/测试）
python3 push_existing_report.py --latest --send-gewe-txt
python3 push_existing_report.py --file output/.../telegram_push_report.txt --channels tg,gewe_txt,feishu

# 独立执行单模块
python3 daily_ctgov_check_tgbot.py        # 抓取
python3 ctgov_full_sync_rag.py            # 精翻
python3 fastgpt_sync.py --once --mode=today   # 同步（today | all）
```

---

## 开发与排障约定

- **安全第一**：含真实凭据的文件（`.env`、`sample_gewe_*.py`、`curl_*_push.md`、`kick_off_member.py`、`openclaw.json`）已在 `.gitignore` 中。新增含凭据的文件时，**同步**把它加进 `.gitignore`，永远不要提交密钥。
- **FastGPT 数据清洗**：处理原始 JSON 时强制剔除 `ancestors`、`conditionBrowseModule`、`interventionBrowseModule`、`derivedSection`——这些字段产生索引噪音，降低 RAG 命中率。
- **中国中心高亮**：含中国医院的试验，TG 加 `🇨🇳` 标记，GeWe 卡片在标题前缀 + 描述末尾双重标注 `🇨🇳 中国有中心（优先关注）`。
- **GeWe 文字分批**：单条消息按 `GEWE_MSG_MAX_LEN`（默认 500）分批，避免微信折叠，分批加 `(续 i/n)` 尾标。
- **渠道默认开关**：`gewe_txt=true`、`gewe_card=false`。主菜单快捷推送以**文字为默认入口**（选项 3，开箱即用），卡片下移到选项 4 并提示用户先在 `config.yaml` 开启。新增菜单项时遵循同一原则——默认开启的渠道靠前、默认关闭的渠道带配置提示。
- **推送失败隔离**：多群循环推送时某群失败不影响其他群；微信失败不影响 TG 主渠道。
- **重试**：同步脚本内置 3 次重试，适配不稳定网络。

更详细的架构与历史决策见 `references/architecture.md`，配置项逐条说明见 `references/config-reference.md`。

---

## 安装到默认技能目录

本 skill 仓库放在任意位置（如 `~/Downloads/clinicaltrials-intel-skill`），通过软链接接入 ZCode 默认发现路径 `~/.agents/skills`：

```bash
ln -s ~/Downloads/clinicaltrials-intel-skill ~/.agents/skills/clinicaltrials-intel
```

这样仓库源码（可 git 发布）与技能安装位置解耦，更新仓库即更新技能。
