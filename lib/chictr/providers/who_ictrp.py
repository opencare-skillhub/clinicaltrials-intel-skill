"""
WHO ICTRP provider（默认零浏览器基线）。

说明：
- ICTRP 镜像 ChiCTR 记录，字段以英文为主，同步可能滞后
- 站点偶发超时/错误页；本 provider 一律软失败
- 解析策略：Trial2.aspx 详情页 span# 字段 + 搜索页链接抽 ChiCTR ID
"""

from __future__ import annotations

import re
from typing import Any

import requests

from lib.chictr.models import ProviderResult, SearchQuery, UnifiedTrial
from lib.chictr.providers.base import BaseProvider

ICTRP_BASE = "https://trialsearch.who.int"
ICTRP_DETAIL = f"{ICTRP_BASE}/Trial2.aspx"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        }
    )
    return s


def _span_map(html: str) -> dict[str, str]:
    """粗解析 id → text（不强制 bs4，正则兜底）。"""
    out: dict[str, str] = {}
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "html.parser")
        for el in soup.find_all(id=True):
            tid = el.get("id") or ""
            text = el.get_text(" ", strip=True)
            if tid and text:
                out[tid] = text
        return out
    except Exception:
        for m in re.finditer(
            r'id=["\']([^"\']+)["\'][^>]*>([^<]{1,500})<', html or "", re.I
        ):
            out[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
        return out


def parse_ictrp_detail_html(html: str, chictr_id: str = "") -> UnifiedTrial:
    spans = _span_map(html)
    # ICTRP 常见控件 id（不同皮肤可能变化，做多候选）
    def pick(*keys: str) -> str:
        for k in keys:
            if spans.get(k):
                return spans[k]
            for sk, sv in spans.items():
                if k.lower() in sk.lower() and sv:
                    return sv
        return ""

    rid = pick("MainContent_LabelTrialID", "TrialID", "lblTrialID") or chictr_id
    if not rid:
        m = re.search(r"ChiCTR[\w-]+", html or "", re.I)
        rid = m.group(0) if m else chictr_id or "unknown"

    title = pick(
        "MainContent_LabelPublicTitle",
        "PublicTitle",
        "lblPublicTitle",
        "MainContent_LblPublicTitle",
    )
    scientific = pick("MainContent_LabelScientificTitle", "ScientificTitle")
    status = pick("MainContent_LabelRecruitmentStatus", "RecruitmentStatus")
    condition = pick("MainContent_LabelHealthCondition", "HealthConditionBase")
    intervention = pick("MainContent_LabelIntervention", "Intervention")
    sponsor = pick("MainContent_LabelPrimarySponsor", "PrimarySponsor")
    phase = pick("MainContent_LabelPhase", "Phase")
    study_type = pick("MainContent_LabelStudyType", "StudyType")
    reg_date = pick("MainContent_LabelDateRegistration", "DateRegistration")
    last_update = pick("MainContent_LabelLastRefreshedOn", "LastRefreshedOn")
    institution = pick("MainContent_LabelSourceRegister", "SourceRegister")

    url = f"{ICTRP_DETAIL}?TrialID={rid}"
    return UnifiedTrial(
        id=rid,
        title=title or scientific or rid,
        title_cn="",
        status=status,
        condition=condition,
        intervention=intervention,
        sponsor=sponsor,
        institution=institution,
        phase=phase,
        study_type=study_type,
        registration_date=reg_date,
        last_update=last_update,
        url=url,
        source="who_ictrp",
        raw={"spans_sample": dict(list(spans.items())[:20])},
    )


def extract_chictr_ids_from_search_html(html: str, limit: int = 20) -> list[str]:
    ids = []
    seen = set()
    for m in re.finditer(r"ChiCTR[0-9A-Za-z-]+", html or "", re.I):
        rid = m.group(0)
        # 规范化大小写前缀
        if rid.lower().startswith("chictr"):
            rid = "ChiCTR" + rid[6:]
        if rid not in seen:
            seen.add(rid)
            ids.append(rid)
        if len(ids) >= limit:
            break
    return ids


class WhoIctprProvider(BaseProvider):
    name = "who_ictrp"

    def __init__(self, timeout: float = 25.0) -> None:
        self.timeout = timeout
        self._http = _session()

    def search(self, query: SearchQuery) -> ProviderResult:
        try:
            if query.registration_number:
                trial = self.get_detail(query.registration_number)
                return ProviderResult(
                    trials=[trial] if trial else [],
                    provider=self.name,
                )

            keyword = (query.keyword or "").strip()
            if not keyword:
                return ProviderResult(trials=[], provider=self.name, error="empty keyword")

            # ICTRP 搜索表单复杂且易超时；先用简单 GET 试探 Default.aspx + query 参数变体
            candidates = [
                f"{ICTRP_BASE}/Default.aspx",
            ]
            html = ""
            last_err = ""
            for url in candidates:
                try:
                    r = self._http.get(
                        url,
                        params={"content": keyword},
                        timeout=self.timeout,
                    )
                    if r.status_code == 200 and len(r.text) > 500:
                        html = r.text
                        break
                    last_err = f"HTTP {r.status_code} len={len(r.text)}"
                except Exception as e:
                    last_err = str(e)

            if not html:
                # 网络不可用：软失败，返回空
                return ProviderResult(
                    trials=[],
                    provider=self.name,
                    error=f"WHO ICTRP unreachable: {last_err}",
                )

            ids = extract_chictr_ids_from_search_html(html, limit=query.max_results)
            # 若首页无结果，至少不崩
            trials: list[UnifiedTrial] = []
            for rid in ids[: query.max_results]:
                # 列表级轻量对象；详情按需再拉
                trials.append(
                    UnifiedTrial(
                        id=rid,
                        title=rid,
                        url=f"{ICTRP_DETAIL}?TrialID={rid}",
                        source="who_ictrp",
                    )
                )
            # 年份过滤（若列表仅有 id，则在详情阶段再滤；此处尽量用 id 中年份位）
            if query.year and trials:
                y = str(query.year)
                filtered = [t for t in trials if y in t.id]
                if filtered:
                    trials = filtered
            return ProviderResult(trials=trials, provider=self.name)
        except Exception as e:
            return ProviderResult(trials=[], provider=self.name, error=str(e))

    def get_detail(self, registration_number: str) -> UnifiedTrial | None:
        rid = (registration_number or "").strip()
        if not rid:
            return None
        try:
            r = self._http.get(
                ICTRP_DETAIL,
                params={"TrialID": rid},
                timeout=self.timeout,
            )
            if r.status_code != 200 or len(r.text) < 200:
                return None
            if "Runtime Error" in r.text and "Trial" not in r.text[:2000]:
                return None
            return parse_ictrp_detail_html(r.text, chictr_id=rid)
        except Exception:
            return None
