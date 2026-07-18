"""
ChiCTR 中国临床试验数据源（实验模块）。

默认不接入 main 自动流程；由调用方显式 import 使用：

    from lib.chictr import search_trials, get_trial_detail, adapt_to_ctgov_study

设计文档：docs/chictr-design.md
"""

from lib.chictr.adapt_ctgov import adapt_many, adapt_to_ctgov_study
from lib.chictr.client import get_trial_detail, merge_with_ctgov, search_trials
from lib.chictr.models import SearchQuery, UnifiedTrial

__all__ = [
    "SearchQuery",
    "UnifiedTrial",
    "search_trials",
    "get_trial_detail",
    "adapt_to_ctgov_study",
    "adapt_many",
    "merge_with_ctgov",
]
