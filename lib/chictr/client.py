"""
ChiCTR 门面：瀑布 provider + 缓存。

默认：
  1) 缓存
  2) WHO ICTRP
  3) （可选）direct — 需 CHICTR_DIRECT=1 且外部浏览器能力，本 MVP 仅预留钩子

不抛异常打断主流程；失败返回空列表并打印警告。
"""

from __future__ import annotations

import os
from typing import Iterable

from lib.chictr.cache import FileCache
from lib.chictr.models import ProviderResult, SearchQuery, UnifiedTrial
from lib.chictr.providers.who_ictrp import WhoIctprProvider

_cache = FileCache(ttl_seconds=int(os.getenv("CHICTR_CACHE_TTL", "3600")))


def _cache_key(query: SearchQuery) -> str:
    return (
        f"search|{query.provider}|{query.keyword}|{query.registration_number}|"
        f"{query.year}|{query.max_results}"
    )


def search_trials(
    keyword: str = "",
    registration_number: str = "",
    year: int | None = None,
    max_results: int = 20,
    provider: str = "auto",
    use_cache: bool = True,
) -> list[UnifiedTrial]:
    """
    搜索中国临床试验（ChiCTR 号体系）。

    provider:
      - auto: 缓存 → WHO → (可选 direct)
      - who_ictrp
      - chictr_direct（MVP 未接浏览器时返回 error 提示）
    """
    query = SearchQuery(
        keyword=keyword,
        registration_number=registration_number,
        year=year,
        max_results=max_results,
        provider=provider or "auto",
    )

    if use_cache:
        cached = _cache.get(_cache_key(query))
        if cached:
            return [UnifiedTrial(**t) if isinstance(t, dict) else t for t in cached]

    results = _run_providers(query)
    if results and use_cache:
        _cache.set(_cache_key(query), [t.to_dict() for t in results])
    return results


def get_trial_detail(registration_number: str, use_cache: bool = True) -> UnifiedTrial | None:
    rid = (registration_number or "").strip()
    if not rid:
        return None
    key = f"detail|{rid}"
    if use_cache:
        cached = _cache.get(key)
        if cached and isinstance(cached, dict):
            return UnifiedTrial(**cached)

    who = WhoIctprProvider()
    trial = who.get_detail(rid)
    if trial and use_cache:
        _cache.set(key, trial.to_dict())
    return trial


def _run_providers(query: SearchQuery) -> list[UnifiedTrial]:
    order: list[str]
    if query.provider == "auto":
        order = ["who_ictrp"]
        if os.getenv("CHICTR_DIRECT", "").strip() in {"1", "true", "yes"}:
            order.append("chictr_direct")
    else:
        order = [query.provider]

    errors: list[str] = []
    for name in order:
        res = _dispatch(name, query)
        if res.trials:
            if res.error:
                print(f"⚠️  ChiCTR provider {name} partial: {res.error}")
            return res.trials[: query.max_results]
        if res.error:
            errors.append(f"{name}: {res.error}")
            print(f"⚠️  ChiCTR provider {name} failed: {res.error}")

    if errors:
        print("⚠️  ChiCTR 全部 provider 无结果 → " + " | ".join(errors))
    return []


def _dispatch(name: str, query: SearchQuery) -> ProviderResult:
    if name in {"who", "who_ictrp", "ictrp"}:
        return WhoIctprProvider().search(query)
    if name in {"direct", "chictr_direct", "chictr"}:
        # MVP：不强制拉起 Playwright，避免干扰主项目依赖
        # 后续可接 subprocess → chictr-mcp-server 或 playwright
        return ProviderResult(
            trials=[],
            provider="chictr_direct",
            error=(
                "chictr_direct 未在本 MVP 启用。"
                "可设置外部 MCP/Playwright 后扩展；"
                "HTML 解析器已在 lib/chictr/providers/chictr_html.py 就绪。"
            ),
        )
    return ProviderResult(trials=[], provider=name, error=f"unknown provider: {name}")


def merge_with_ctgov(
    chictr_trials: Iterable[UnifiedTrial],
    ctgov_studies: Iterable[dict],
) -> list[dict]:
    """
    粗合并：CTGov 列表在前，再追加无法用 secondary id 对上的 ChiCTR。
    完整交叉验证留给 P2。
    """
    from lib.chictr.adapt_ctgov import adapt_to_ctgov_study

    out = list(ctgov_studies)
    seen_ids = set()
    for s in out:
        nct = (
            s.get("protocolSection", {})
            .get("identificationModule", {})
            .get("nctId", "")
        )
        if nct:
            seen_ids.add(str(nct).upper())
        # secondary ids 若存在
        for sec in (
            s.get("protocolSection", {})
            .get("identificationModule", {})
            .get("secondaryIdInfos", [])
            or []
        ):
            sid = str(sec.get("id", "")).upper()
            if sid:
                seen_ids.add(sid)

    for t in chictr_trials:
        if t.id and t.id.upper() in seen_ids:
            continue
        out.append(adapt_to_ctgov_study(t))
        if t.id:
            seen_ids.add(t.id.upper())
    return out
