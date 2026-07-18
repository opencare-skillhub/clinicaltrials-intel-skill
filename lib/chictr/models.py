"""ChiCTR / WHO ICTRP 统一试验模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SearchQuery:
    """搜索参数。"""

    keyword: str = ""
    registration_number: str = ""
    year: int | None = None
    max_results: int = 20
    # who_ictrp | chictr_direct | auto
    provider: str = "auto"


@dataclass
class UnifiedTrial:
    """跨数据源统一结构，供推送适配使用。"""

    id: str
    title: str = ""
    title_cn: str = ""
    status: str = ""
    condition: str = ""
    intervention: str = ""
    sponsor: str = ""
    institution: str = ""
    phase: str = ""
    study_type: str = ""
    registration_date: str = ""
    last_update: str = ""
    url: str = ""
    source: str = "chictr"  # chictr | who_ictrp | cache
    project_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderResult:
    """单 provider 返回。"""

    trials: list[UnifiedTrial] = field(default_factory=list)
    provider: str = ""
    error: str = ""
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return not self.error
