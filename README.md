# clinicaltrials-intel skill

胰腺癌临床试验情报自动化系统的开发与运维 ZCode 技能。沉淀了 `clinicaltrials推送和订阅` 项目的架构、运行流程、配置规范与开发约定。

## 内容

```
clinicaltrials-intel-skill/
├── SKILL.md                         # 技能主体（系统概览 + 运行 + 开发约定）
├── assets/
│   ├── .env.template                # 凭据模板（占位符,无真实密钥）
│   └── config.yaml.template         # 渠道/流程/翻译模型 fallback 链模板
├── references/
│   ├── architecture.md              # 架构决策与历史背景
│   └── config-reference.md          # 配置项逐条参考
├── scripts/
│   └── install.sh                   # 安装到 ~/.agents/skills
├── .gitignore                       # 保护敏感文件(只提交模板)
└── README.md
```

## 安装到默认技能目录

```bash
./scripts/install.sh            # 软链接（默认,源更新即技能更新）
./scripts/install.sh --copy     # 复制（独立副本）
./scripts/install.sh --uninstall
```

或手动软链接：

```bash
ln -s "$(pwd)" ~/.agents/skills/clinicaltrials-intel
```

安装后重启 ZCode 会话即可触发。

## 配置文件安全约定

- **模板可提交**：`assets/.env.template`、`assets/config.yaml.template` 只含占位符。
- **真实配置绝不提交**：`.env`、`config.yaml` 等含真实凭据的文件已在 `.gitignore` 中，本地可用，禁止上传 git。
- 新增含凭据的文件时，同步加进 `.gitignore`。

## 触发场景

提到以下内容时自动触发：临床试验订阅推送、ClinicalTrials.gov 抓取翻译、FastGPT 知识库同步、GeWe/飞书/TG 推送渠道、pancreatic cancer 情报系统、配置文件模板。

## 许可

AGPL-3.0 + 非商业性使用限制（继承自主项目）。
