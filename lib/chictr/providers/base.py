"""Provider 抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from lib.chictr.models import ProviderResult, SearchQuery, UnifiedTrial


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: SearchQuery) -> ProviderResult:
        raise NotImplementedError

    def get_detail(self, registration_number: str) -> UnifiedTrial | None:
        return None
