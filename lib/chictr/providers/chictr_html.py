"""
ChiCTR HTML 解析器（离线可测）。

选择器来自本地 chictr_trials / PancrePal chictr-mcp-server 实战经验：
- 列表：table.table1 tr + a[href*=showproj]
- 详情：td.left_title 标签-值表
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from lib.chictr.models import UnifiedTrial

CHICTR_BASE = "https://www.chictr.org.cn"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def parse_search_html(html: str, base_url: str = CHICTR_BASE) -> list[UnifiedTrial]:
    """解析搜索结果列表页 HTML。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError("需要 beautifulsoup4: pip install beautifulsoup4") from e

    soup = BeautifulSoup(html or "", "html.parser")
    trials: list[UnifiedTrial] = []

    # 新版常见 table.table1；兼容 table_list
    rows = soup.select("table.table1 tr") or soup.select("table.table_list tr")
    for idx, row in enumerate(rows):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        # 跳过表头
        if row.find("th"):
            continue

        reg = ""
        title = ""
        project_id = ""
        href = ""
        study_type = ""
        reg_date = ""
        institution = ""

        # 常见列：序号 | 注册号 | 题目/机构 | 类型 | 日期
        if len(cells) >= 5:
            reg = _clean(cells[1].get_text(" ", strip=True))
            link = cells[2].find("a") or cells[2].select_one("a.tit1")
            if link:
                title = _clean(link.get("title") or link.get_text(" ", strip=True))
                href = link.get("href") or ""
            institution = _clean(" ".join(p.get_text(" ", strip=True) for p in cells[2].find_all("p")))
            study_type = _clean(cells[3].get_text(" ", strip=True))
            reg_date = _clean(cells[4].get_text(" ", strip=True))
        else:
            # 宽松：任意含 ChiCTR 的行
            full = _clean(row.get_text(" ", strip=True))
            m = re.search(r"ChiCTR[\w-]+", full, re.I)
            if not m:
                continue
            reg = m.group(0)
            link = row.find("a")
            if link:
                title = _clean(link.get("title") or link.get_text(" ", strip=True))
                href = link.get("href") or ""

        if not reg and not title:
            continue

        m_proj = re.search(r"proj=(\d+)", href or "")
        if m_proj:
            project_id = m_proj.group(1)
        url = urljoin(base_url + "/", href) if href else (
            f"{base_url}/showproj.html?proj={project_id}" if project_id else ""
        )

        trials.append(
            UnifiedTrial(
                id=reg or f"unknown-{idx}",
                title=title,
                title_cn=title,
                status="",
                study_type=study_type,
                registration_date=reg_date,
                institution=institution,
                url=url,
                source="chictr",
                project_id=project_id,
                raw={"href": href},
            )
        )
    return trials


def _label_value_map(soup) -> dict[str, str]:
    """从详情页 left_title 表格提取 标签→值。"""
    data: dict[str, str] = {}
    for td in soup.select("td.left_title"):
        label = _clean(td.get_text(" ", strip=True)).rstrip("：:").strip()
        if not label:
            continue
        nxt = td.find_next_sibling("td")
        if not nxt:
            continue
        val = _clean(nxt.get_text(" ", strip=True))
        if label and val:
            data[label] = val
            # 也存去掉中英文噪声后的小写键
            data[label.lower()] = val
    return data


def _pick(d: dict[str, str], *keys: str) -> str:
    for k in keys:
        if k in d and d[k]:
            return d[k]
        # 包含匹配
        for dk, dv in d.items():
            if k.lower() in str(dk).lower() and dv:
                return dv
    return ""


def parse_detail_html(
    html: str,
    registration_number: str = "",
    url: str = "",
) -> UnifiedTrial:
    """解析详情页 HTML。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError("需要 beautifulsoup4: pip install beautifulsoup4") from e

    soup = BeautifulSoup(html or "", "html.parser")
    fields = _label_value_map(soup)

    # 页头标题
    el_cn = soup.select_one(".project-tit p.cn") or soup.select_one("p.cn")
    el_en = soup.select_one(".project-tit p.en") or soup.select_one("p.en")
    title_cn = _clean(el_cn.get_text(" ", strip=True) if el_cn else "")
    title_en = _clean(el_en.get_text(" ", strip=True) if el_en else "")

    reg = (
        _pick(fields, "注册号", "Registration number", "registration number")
        or registration_number
    )
    public_title = _pick(fields, "注册题目", "Public title", "public title")
    scientific = _pick(fields, "科学题目", "Scientific title", "scientific title")
    status = _pick(fields, "招募状态", "Recruitment status", "recruitment status")
    condition = _pick(fields, "目标疾病", "Target disease", "condition", "研究疾病")
    intervention = _pick(fields, "干预措施", "Interventions", "intervention")
    sponsor = _pick(fields, "主要申办者", "Primary sponsor", "申办者")
    institution = _pick(fields, "申请人所在单位", "Applicant institution", "研究实施负责单位")
    phase = _pick(fields, "研究阶段", "Study phase", "phase")
    study_type = _pick(fields, "研究类型", "Study type")
    reg_date = _pick(fields, "注册时间", "Date of registration", "registration date")
    last_update = _pick(fields, "最近更新日期", "Last refreshed on", "last update")

    title = public_title or title_cn or title_en or scientific or reg
    m_proj = re.search(r"proj=(\d+)", url or "")
    project_id = m_proj.group(1) if m_proj else ""

    return UnifiedTrial(
        id=reg or registration_number or "unknown",
        title=title,
        title_cn=title_cn or public_title,
        status=status,
        condition=condition,
        intervention=intervention,
        sponsor=sponsor,
        institution=institution,
        phase=phase,
        study_type=study_type,
        registration_date=reg_date,
        last_update=last_update,
        url=url or (f"{CHICTR_BASE}/showproj.html?proj={project_id}" if project_id else ""),
        source="chictr",
        project_id=project_id,
        raw={"fields": {k: v for k, v in fields.items() if not k.islower() or k != k.lower()}},
    )


def build_search_url(
    keyword: str = "",
    registration_number: str = "",
    year: int | None = None,
    page: int = 1,
    english: bool = False,
) -> str:
    """构造 ChiCTR 搜索 URL（供 direct provider / 浏览器使用）。"""
    path = "searchprojen.html" if english else "searchproj.html"
    params = [f"page={page}", "btngo=btn"]
    if keyword:
        from urllib.parse import quote
        params.append(f"title={quote(keyword)}")
    if registration_number:
        from urllib.parse import quote
        params.append(f"regno={quote(registration_number)}")
    if year:
        params.append(f"createyear={int(year)}")
    return f"{CHICTR_BASE}/{path}?{'&'.join(params)}"
