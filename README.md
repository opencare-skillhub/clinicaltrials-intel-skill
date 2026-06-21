# clinicaltrials-intel

胰腺癌临床试验情报自动化系统——**开箱可配置**的通用技能包。自带完整业务代码，clone 后一条命令完成部署。不绑定任何特定产品，可作为独立工具运行，也可集成进你习惯的 AI 编程工作流。

## 快速开始

```bash
git clone https://github.com/opencare-skillhub/clinicaltrials-intel-skill.git
cd clinicaltrials-intel-skill
./scripts/setup.sh        # 一键:装依赖 + 生成配置 + 创建运行时目录
nano .env                 # 填入你的凭据(至少 1 个 LLM key)
python3 scripts/check_config.py   # 校验配置(分级报告)
python3 main.py           # 运行(必须在仓库根目录)
```

## 配置分级（零配置也能启动，按需提升能力）

| 级别 | 配什么 | 不配的后果 |
|------|--------|-----------|
| 🔴 启动必需 | Python 依赖 | `import` 崩溃（`setup.sh` 已解决） |
| 🟡 中文翻译 | `.env` 至少 1 个 `*_API_KEY`（推荐 `QWEN_API_KEY`） | 翻译降级为英文 |
| 🟢 推送渠道 | 各渠道凭据（见下） | 该渠道静默跳过，不影响其他 |

### 渠道凭据速查

| 渠道 | 环境变量 | 开关 | 说明 |
|------|---------|------|------|
| GeWe 微信 | `GEWE_APP_ID` + `GEWE_TOKEN` + `GEWE_TO_WXID` | `GEWE_ENABLED=true` | 💰 **付费服务**，见下方说明 |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | 默认开 | 免费 |
| 飞书 | `FEISHU_APP_ID` + `FEISHU_APP_SECRET` + `FEISHU_CHAT_IDS` | 默认开 | 免费 |
| FastGPT | `FASTGPT_BASE_URL` + `FASTGPT_API_KEY` + `FASTGPT_DATASET_ID` | 默认开 | 需自建/托管实例 |

> 💰 **GeWe 微信推送是付费服务**：微信群推送能力基于 [GeWeChat](https://www.geweapi.com/#/newHome) 平台，需自行注册并购买服务套餐，获取 `APP_ID` 和 `TOKEN`。官网：https://www.geweapi.com/#/newHome
>
> 不需要微信推送？保持 `GEWE_ENABLED=false`（默认）即可，Telegram/飞书渠道完全免费可用。

> 📖 **第一次申请凭据？** 各渠道的详细申请步骤见 [docs/credentials-guide.md](./docs/credentials-guide.md)（含 TG Bot 创建、飞书应用配置、GeWeChat 购买、翻译模型 Key 申请，以及合规提醒）。

## 仓库内容

```
clinicaltrials-intel-skill/
├── main.py / push_existing_report.py / daily_ctgov_check_tgbot.py   # 入口脚本
│   / ctgov_full_sync_rag.py / fastgpt_sync.py
├── lib/                       # 核心模块(config/ctgov_api/llm_client/channels/*)
├── config.yaml                # 运行时配置(setup.sh 生成,gitignore)
├── requirements.txt           # 依赖清单(补齐主项目漏掉的 PyYAML)
├── SKILL.md                   # 技能主体
├── assets/                    # 配置模板(.env.template / config.yaml.template)
├── scripts/                   # setup.sh(部署) check_config.py(校验) install.sh(装技能)
├── references/                # 架构文档 + 配置参考
└── docs/                      # 使用文档
```

## 常用命令

```bash
# 抓取 10 个最近中国试验并推 GeWe 文字(默认开箱渠道)
python3 main.py --10 --china --send-gewe-txt

# 主菜单(无参数)
python3 main.py

# 全自动流程(适合 cron)
python3 main.py --auto

# 推送已有报告(补发/测试)
python3 push_existing_report.py --latest --send-gewe-txt
```

## 集成与贡献

本技能包不绑定特定产品，可独立运行。若你想把它接入 AI 编程助手（如 ZCode）作为可复用技能：

```bash
./scripts/install.sh            # 软链接到 ~/.agents/skills/clinicaltrials-intel
```

也欢迎使用 [ZCode](https://zcode.dev) 等工具在本仓库基础上开发、迭代和贡献新功能。详细架构与开发约定见 [SKILL.md](./SKILL.md)。

## 安全

- ✅ `.env` / `config.yaml`（运行时配置）已在 `.gitignore`，**永不提交**
- ✅ 仓库只含模板（占位符）和业务代码，无真实凭据
- ✅ 含真实 token 的调试脚本（`kick_off_member.py` / `sample_gewe_*.py` 等）已排除
- 💡 **本地直接使用**：为方便真实运行，可从已有项目把真实 `.env` 和 `config.yaml` 复制到本仓库根目录——它们已被 `.gitignore` 排除，不会进 git，本地放心用。

## 许可

Apache License 2.0。详情见 [LICENSE](./LICENSE)。
