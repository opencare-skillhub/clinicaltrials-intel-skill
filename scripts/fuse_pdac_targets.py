#!/usr/bin/env python3
"""
融合三份靶点配置，生成运行时兼容的 assets/pancreatic_targets.yaml

来源：
  1) Downloads/pdac_targets_search_v2.yaml  — 知识层（82 靶点、分层检索词、检测/突变）
  2) clinicaltrials-search/config/genes.yaml — 月报/技能基因定义
  3) 现有 assets/pancreatic_targets.yaml    — 运行时分组与中文名兜底

设计原则：
  - 保持 lib/targets.py 所需字段：id/name/group/aliases/keywords/cn_name
  - 默认 default_groups=core,A,B,C，避免 trial_query 全量 300+ 词撑爆 CTGov query
  - 单一靶点匹配时可用 search_terms 全量（exact+zh+drug）扩大召回
  - 不把 emerging/exploratory 放进默认 KEYWORDS
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# 优先仓库内知识源；不存在时回退用户 Downloads
PDAC_PATH = ROOT / "assets" / "pdac_targets_search_v2.yaml"
if not PDAC_PATH.exists():
    PDAC_PATH = Path("/Users/qinxiaoqiang/Downloads/pdac_targets_search_v2.yaml")
GENES_PATH = Path.home() / ".agents/skills/clinicaltrials-search/config/genes.yaml"
OUT_PATH = ROOT / "assets" / "pancreatic_targets.yaml"
LEGACY_PATH = ROOT / "assets" / "pancreatic_targets.yaml"


def norm(s: str) -> str:
    t = str(s or "").strip().lower()
    for ch in " -_./()（）[]":
        t = t.replace(ch, "")
    return t


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def uniq(seq):
    out = []
    seen = set()
    for x in seq:
        s = str(x).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def index_pdac(pdac: dict) -> dict[str, dict]:
    idx = {}
    for t in pdac.get("targets") or []:
        keys = {norm(t.get("id")), norm(t.get("canonical"))}
        for a in t.get("aliases") or []:
            keys.add(norm(a))
        st = t.get("search_terms") or {}
        for a in st.get("exact") or []:
            keys.add(norm(a))
        for k in keys:
            if k:
                idx.setdefault(k, t)
    return idx


def find_pdac(idx: dict, *names: str):
    for n in names:
        hit = idx.get(norm(n))
        if hit:
            return hit
    return None


def compact_keywords(pdac_t, aliases, search_terms, limit=12) -> list[str]:
    """
    默认 KEYWORDS 用精简词表，避免 CTGov OR 过长。
    更全的 exact/drug/zh 放 search_terms，供单一靶点模式展开。
    """
    kws = []
    # 1) 基因符号 / 规范名 / 主要别名
    if pdac_t:
        kws.append(pdac_t.get("canonical") or pdac_t.get("id"))
        kws.extend((pdac_t.get("aliases") or [])[:5])
        st = pdac_t.get("search_terms") or {}
        # exact 只取前几个「短」词（避免整句描述）
        for x in st.get("exact") or []:
            if len(str(x)) <= 28:
                kws.append(x)
            if len(uniq(kws)) >= 8:
                break
    kws.extend(aliases or [])
    for x in search_terms or []:
        kws.append(str(x).replace(" pancreatic", "").strip())
    # 过滤过宽噪声（单独出现会污染召回）
    block = {"RAS", "ADC", "CAR-T", "monoclonal antibody", "bispecific antibody", "MEK inhibitor"}
    kws = [k for k in uniq(kws) if k not in block]
    return kws[:limit]


def rich_search_terms(pdac_t) -> dict | None:
    if not pdac_t:
        return None
    st = pdac_t.get("search_terms") or {}
    return {
        "exact": uniq(st.get("exact") or [])[:30],
        "zh": uniq(st.get("zh") or [])[:20],
        "drug_or_class": uniq(st.get("drug_or_class") or [])[:20],
        # 单一靶点可展开；默认 KEYWORDS 不用这个全量
        "trial_query_terms": uniq(st.get("trial_query_terms") or [])[:50],
        "requires_context": bool(st.get("requires_context")),
    }


def group_for(gene_id: str, category: str | None) -> str:
    if gene_id in {"kras", "tp53", "atm", "brca", "brca1", "brca2", "immune", "palb2", "msi_mmr", "hrr"}:
        return "core"
    if category in {"guideline", "hotspot"}:
        return "A"
    if category == "advanced":
        return "B"
    if category == "supplementary":
        return "C"
    return "B"


def build_from_genes(genes_cfg: dict, pdac_idx: dict, legacy_by_id: dict) -> list[dict]:
    items = []
    for g in genes_cfg.get("genes") or []:
        gid = g["id"]
        legacy = legacy_by_id.get(gid) or {}
        pdac_t = find_pdac(
            pdac_idx,
            gid,
            g.get("name"),
            *(g.get("aliases") or []),
            *(legacy.get("aliases") or []),
        )
        aliases = uniq((g.get("aliases") or []) + (legacy.get("aliases") or []) + ((pdac_t or {}).get("aliases") or []))
        item = {
            "id": gid,
            "name": (pdac_t or {}).get("canonical") or g.get("name") or gid,
            "group": group_for(gid, g.get("category")),
            "tier": (pdac_t or {}).get("tier") or group_for(gid, g.get("category")),
            "type": (pdac_t or {}).get("type") or "gene",
            "aliases": aliases[:24],
            "keywords": compact_keywords(pdac_t, aliases, g.get("search_terms") or []),
            "cn_name": g.get("cn_name") or legacy.get("cn_name") or "",
            "cn_desc": g.get("cn_desc") or "",
            "report": bool(g.get("report", False)),
            "nccn_section": g.get("nccn_section") or "",
            "category": g.get("category") or "",
        }
        if pdac_t:
            item["pdac_id"] = pdac_t.get("id")
            item["canonical"] = pdac_t.get("canonical")
            item["alterations"] = pdac_t.get("alterations") or []
            item["pathway"] = pdac_t.get("pathway") or []
            item["clinical_tags"] = pdac_t.get("clinical_tags") or []
            item["recommended_detection"] = pdac_t.get("recommended_detection") or []
            item["source_tags"] = pdac_t.get("source_tags") or []
            rst = rich_search_terms(pdac_t)
            if rst:
                item["search_terms"] = rst
        items.append(item)
    return items


def add_extra(items: list[dict], pdac_idx: dict, extra_specs: list[dict]) -> list[dict]:
    have = {x["id"] for x in items}
    for spec in extra_specs:
        if spec["id"] in have:
            continue
        pdac_t = find_pdac(pdac_idx, spec["id"], spec.get("name"), *(spec.get("aliases") or []))
        aliases = uniq((spec.get("aliases") or []) + ((pdac_t or {}).get("aliases") or []))
        item = {
            "id": spec["id"],
            "name": (pdac_t or {}).get("canonical") or spec.get("name") or spec["id"],
            "group": spec.get("group", "B"),
            "tier": (pdac_t or {}).get("tier") or spec.get("group", "B"),
            "type": (pdac_t or {}).get("type") or "gene",
            "aliases": aliases[:24],
            "keywords": compact_keywords(pdac_t, aliases, spec.get("search_terms") or []),
            "cn_name": spec.get("cn_name") or "",
            "cn_desc": spec.get("cn_desc") or "",
            "report": bool(spec.get("report", False)),
            "nccn_section": spec.get("nccn_section") or "",
            "category": spec.get("category") or "",
        }
        if pdac_t:
            item["pdac_id"] = pdac_t.get("id")
            item["canonical"] = pdac_t.get("canonical")
            item["alterations"] = pdac_t.get("alterations") or []
            item["pathway"] = pdac_t.get("pathway") or []
            item["clinical_tags"] = pdac_t.get("clinical_tags") or []
            item["recommended_detection"] = pdac_t.get("recommended_detection") or []
            item["source_tags"] = pdac_t.get("source_tags") or []
            rst = rich_search_terms(pdac_t)
            if rst:
                item["search_terms"] = rst
        items.append(item)
        have.add(spec["id"])
    return items


def main() -> None:
    if not PDAC_PATH.exists():
        raise SystemExit(f"missing PDAC knowledge file: {PDAC_PATH}")
    if not GENES_PATH.exists():
        raise SystemExit(f"missing genes.yaml: {GENES_PATH}")

    pdac = load_yaml(PDAC_PATH)
    genes_cfg = load_yaml(GENES_PATH)
    legacy = load_yaml(LEGACY_PATH) if LEGACY_PATH.exists() else {}
    legacy_by_id = {t["id"]: t for t in legacy.get("targets") or []}
    pdac_idx = index_pdac(pdac)

    items = build_from_genes(genes_cfg, pdac_idx, legacy_by_id)

    # 运行时/匹配需要、genes 未单列的补充
    extras = [
        {
            "id": "immune",
            "name": "Immunotherapy",
            "group": "core",
            "aliases": ["Immune", "Immunotherapy", "免疫", "免疫治疗", "PD-1", "PD-L1"],
            "cn_name": "免疫治疗",
            "cn_desc": "免疫治疗宽召回标签",
            "category": "context",
        },
        {
            "id": "palb2",
            "name": "PALB2",
            "group": "core",
            "aliases": ["PALB2"],
            "cn_name": "PALB2",
            "cn_desc": "HRR/DDR 相关，PARP/铂类敏感线索",
            "category": "guideline",
            "report": True,
            "nccn_section": "DNA损伤修复",
        },
        {
            "id": "msi_mmr",
            "name": "MSI-H/dMMR",
            "group": "core",
            "aliases": ["MSI-H", "dMMR", "MSI", "MMR", "microsatellite instability"],
            "cn_name": "微卫星高度不稳定/错配修复缺陷",
            "cn_desc": "免疫治疗优势人群标志",
            "category": "guideline",
            "report": True,
            "nccn_section": "免疫治疗",
        },
        {
            "id": "brca",
            "name": "BRCA",
            "group": "core",
            "aliases": ["BRCA", "BRCA1/2", "BRCA1", "BRCA2"],
            "cn_name": "BRCA1/2",
            "cn_desc": "家族性/胚系突变宽召回（兼容旧 KEYWORDS）",
            "category": "guideline",
        },
        # 扩大匹配但不默认过噪：放 B，仍在 default_groups
        {
            "id": "alk",
            "name": "ALK",
            "group": "B",
            "aliases": ["ALK"],
            "cn_name": "ALK",
            "cn_desc": "融合驱动，篮子试验相关",
            "category": "advanced",
        },
        {
            "id": "ros1",
            "name": "ROS1",
            "group": "B",
            "aliases": ["ROS1"],
            "cn_name": "ROS1",
            "cn_desc": "融合驱动，篮子试验相关",
            "category": "advanced",
        },
        {
            "id": "arid1a",
            "name": "ARID1A",
            "group": "B",
            "aliases": ["ARID1A"],
            "cn_name": "ARID1A",
            "cn_desc": "SWI/SNF / DDR 相关探索靶点",
            "category": "advanced",
        },
    ]
    items = add_extra(items, pdac_idx, extras)

    # knowledge catalog: 非默认展开的 emerging/exploratory 摘要（便于匹配/文档）
    knowledge = []
    covered = set()
    for it in items:
        covered.add(norm(it["id"]))
        covered.add(norm(it.get("name")))
        covered.add(norm(it.get("pdac_id")))
        for a in it.get("aliases") or []:
            covered.add(norm(a))

    for t in pdac.get("targets") or []:
        keys = {norm(t.get("id")), norm(t.get("canonical"))}
        keys.update(norm(a) for a in (t.get("aliases") or []))
        if keys & covered:
            continue
        if t.get("tier") not in {"emerging", "exploratory", "context", "A", "B", "C", "core"}:
            continue
        knowledge.append(
            {
                "id": str(t.get("id")).lower(),
                "pdac_id": t.get("id"),
                "name": t.get("canonical") or t.get("id"),
                "tier": t.get("tier"),
                "type": t.get("type"),
                "aliases": (t.get("aliases") or [])[:12],
                "keywords": ((t.get("search_terms") or {}).get("exact") or t.get("aliases") or [])[:12],
                "pathway": t.get("pathway") or [],
                "clinical_tags": t.get("clinical_tags") or [],
            }
        )

    out = {}
    out["schema_version"] = "2.1"
    out["version"] = 2
    # disease 保持字符串以兼容旧逻辑；详情放 disease_meta
    out["disease"] = "Pancreatic Cancer"
    out["disease_meta"] = {
        "name_zh": (pdac.get("disease") or {}).get("name_zh") or "胰腺导管腺癌",
        "name_en": (pdac.get("disease") or {}).get("name_en") or "Pancreatic Cancer",
        "abbreviation": (pdac.get("disease") or {}).get("abbreviation") or "PDAC",
    }
    out["updated"] = date.today().isoformat()
    out["purpose"] = pdac.get("purpose") or [
        "临床试验检索关键词来源",
        "靶点别名归一化",
    ]
    out["source_note"] = (
        "融合 pdac_targets_search_v2.yaml + clinicaltrials-search/genes.yaml + 本仓库 runtime 分组。"
        "默认 KEYWORDS 仅展开 default_groups；单一靶点可用 search_terms 增强召回。"
    )
    out["knowledge_source"] = str(PDAC_PATH)
    out["normalization_rules"] = pdac.get("normalization_rules") or {
        "case_insensitive": True,
        "strip_punctuation": True,
        "normalize_hyphen_space": True,
    }
    out["priority_tiers"] = pdac.get("priority_tiers") or {}
    out["default_groups"] = ["core", "A", "B", "C"]
    out["groups"] = {
        "core": {"name": "通用监测", "description": "驱动突变 / 免疫 / DDR 等常监测项"},
        "A": {"name": "指南与热点靶点", "description": "指南推荐 + 临床热点（含 SHP2/TF/MET 等）"},
        "B": {"name": "进阶实体瘤靶点", "description": "ADC/CAR-T/融合等进阶靶点"},
        "C": {"name": "补测靶点", "description": "白片足够时可考虑补测"},
        "knowledge": {
            "name": "知识层扩展",
            "description": "emerging/exploratory 等，默认不进入 KEYWORDS，供匹配与情报扩展",
        },
    }
    out["retrieval_profiles"] = {
        "default": {
            "groups": ["core", "A", "B", "C"],
            "use_fields": ["keywords"],
            "note": "日常推送/抓取，控制 OR 词数量",
        },
        "single_target": {
            "groups": ["core", "A", "B", "C", "knowledge"],
            "use_fields": ["keywords", "search_terms.exact", "search_terms.zh", "search_terms.drug_or_class"],
            "note": "菜单单一靶点 / --target，扩大别名与药物词",
        },
        "wide_monitor": {
            "groups": ["core", "A", "B", "C", "knowledge"],
            "use_fields": ["keywords", "search_terms.trial_query_terms"],
            "note": "宽监测；可能过召回，慎用",
        },
    }
    out["targets"] = items
    out["knowledge_targets"] = knowledge
    out["scope_warning"] = pdac.get("scope_warning") or (
        "靶点分层仅表示检索优先级，不等于治疗推荐或入组判断。"
    )

    # PyYAML dump
    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# 胰腺癌靶点配置（融合增强版）\n")
        f.write("# 由 scripts/fuse_pdac_targets.py 生成；可手工微调后重跑融合。\n")
        f.write("# 运行时兼容 lib/targets.py：targets[].id/name/group/aliases/keywords\n\n")
        yaml.dump(
            out,
            f,
            allow_unicode=True,
            sort_keys=False,
            Dumper=NoAliasDumper,
            width=100,
        )

    # stats
    from collections import Counter

    c = Counter(t["group"] for t in items)
    kw = set()
    for t in items:
        if t["group"] in {"core", "A", "B", "C"}:
            kw.update(t.get("keywords") or [])
    print(f"wrote {OUT_PATH}")
    print(f"runtime targets: {len(items)} by group={dict(c)}")
    print(f"default keyword unique≈ {len(kw)}")
    print(f"knowledge_targets: {len(knowledge)}")


if __name__ == "__main__":
    main()
