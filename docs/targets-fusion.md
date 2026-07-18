# 胰腺癌靶点配置融合说明

日期：2026-07-18  
分支：`feat/chictr-cn-trials`（靶点融合与 ChiCTR 实验同分支落地，**不改 main 默认推送逻辑**）

---

## 1. 三份输入对比

| 文件 | 体量 | 定位 | 优点 | 缺点 |
|------|------|------|------|------|
| `assets/pdac_targets_search_v2.yaml`（知识层） | 82 targets / 667 flat index | PDAC 检索+归一化+报告抽取 | 分层 tier、突变/检测、中英/药物词、ChiCTR 友好 | 直接当 KEYWORDS 会 OR 爆炸（core/A/B/C 的 trial_query≈304） |
| `clinicaltrials-search/config/genes.yaml` | 27 genes | 月报/技能 | category/report/cn_desc/NCCN 段落 | 检索词偏少、缺 PALB2/MSI 等 |
| 旧 `assets/pancreatic_targets.yaml` | 22 targets | 运行时 KEYWORDS | 简单可跑 | 别名浅、无突变/药物层 |

### pdac v2 结构要点

- `schema_version: 2.0`，疾病 PDAC
- `priority_tiers`: core / A / B / C / emerging / exploratory / context
- 每靶点：`canonical, type, aliases, alterations, pathway, clinical_tags, recommended_detection, search_terms{exact,zh,drug_or_class,trial_query_terms}, source_tags`
- `retrieval_config` / `user_defined_groups` / `ingestion_fields` / `flat_keyword_index`
- **用途覆盖**：CTGov/ChiCTR 检索、实体归一化、患者报告字段抽取（比单纯 gene list 宽）

---

## 2. 融合策略

**不做**「把 82 靶点全塞进默认 KEYWORDS」。  
**做**「运行时精简 + 知识层保留 + 单一靶点富展开」。

```
pdac_targets_search_v2.yaml  ─┐
genes.yaml                   ─┼─► scripts/fuse_pdac_targets.py ─► assets/pancreatic_targets.yaml
旧 runtime 分组/中文名        ─┘
```

| 层 | 内容 | 何时用 |
|----|------|--------|
| `targets[]`（34） | genes 全量 + immune/palb2/msi_mmr/brca/alk/ros1/arid1a | 默认 `KEYWORDS=yaml` 展开 keywords |
| `knowledge_targets[]`（48） | 未进 runtime 的 emerging/exploratory/context 等 | 匹配扩展 / 情报；**默认不进 KEYWORDS** |
| `search_terms` | exact/zh/drug/trial_query 子集 | `--target` / 菜单 5 **rich 展开** |
| `retrieval_profiles` | default / single_target / wide_monitor | 文档化三种用法 |

运行时字段仍兼容 `lib/targets.py`：`id/name/group/aliases/keywords/cn_name`。

---

## 3. 数量结果（生成后）

- runtime targets：**34**（core8 / A12 / B10 / C4）
- knowledge_targets：**48**
- 默认 KEYWORDS 去重：**~185**（可接受；比 trial_query 全量 300+ 可控）
- 单一靶点例：`b7h3`→CD276 富词；`sotorasib` 可命中 KRAS；`PRMT5` 命中 knowledge

---

## 4. 如何再生

```bash
# 更新知识源后
cp /path/to/pdac_targets_search_v2.yaml assets/pdac_targets_search_v2.yaml
python3 scripts/fuse_pdac_targets.py
```

依赖：本机可读 `~/.agents/skills/clinicaltrials-search/config/genes.yaml`。

---

## 5. 代码改动

- `lib/targets.py`：`search_terms` 参与匹配；`target_keywords(rich=True)` 单一靶点富展开；可匹配 `knowledge_targets`
- 默认 `expand_keywords()` **不**吃 trial_query 全量

---

## 6. 风险与后续

| 风险 | 缓解 |
|------|------|
| 默认 185 词仍偏宽 | 可把 default_groups 缩成 core+A；或 profile=strict |
| genes 与 pdac id 不一致（erbb2 vs HER2） | 融合用别名交叉；保留 genes id 稳定 |
| 知识源更新 | 重跑 fuse 脚本，勿手改大段生成结果（小修可手改 keywords） |

可选后续：

1. `KEYWORDS_PROFILE=default|single|wide` 环境变量  
2. 把 genes.yaml 的 report_defaults 同步脚本化  
3. ChiCTR 中文检索优先用 `search_terms.zh`  
