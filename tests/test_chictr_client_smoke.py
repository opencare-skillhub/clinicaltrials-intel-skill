#!/usr/bin/env python3
"""ChiCTR client 冒烟：默认不强制外网成功。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.chictr import adapt_to_ctgov_study, search_trials
from lib.chictr.client import _dispatch
from lib.chictr.models import SearchQuery, UnifiedTrial


class TestChiCTRClientSmoke(unittest.TestCase):
    def test_import_and_empty_keyword(self):
        # 空关键词应安全返回
        rows = search_trials(keyword="", use_cache=False)
        self.assertIsInstance(rows, list)

    def test_direct_provider_soft_fail(self):
        res = _dispatch("chictr_direct", SearchQuery(keyword="胰腺癌"))
        self.assertEqual(res.provider, "chictr_direct")
        self.assertTrue(res.error)
        self.assertEqual(res.trials, [])

    def test_merge_helper_shape(self):
        t = UnifiedTrial(
            id="ChiCTR2500111173",
            title="demo",
            status="招募中",
            source="chictr",
            url="https://www.chictr.org.cn/showproj.html?proj=1",
        )
        study = adapt_to_ctgov_study(t)
        self.assertEqual(
            study["protocolSection"]["identificationModule"]["nctId"],
            "ChiCTR2500111173",
        )


if __name__ == "__main__":
    unittest.main()
