#!/usr/bin/env python3
"""ChiCTR HTML 解析与适配单测（离线夹具，不依赖外网）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.chictr.adapt_ctgov import adapt_to_ctgov_study
from lib.chictr.providers.chictr_html import (
    build_search_url,
    parse_detail_html,
    parse_search_html,
)


FIXTURES = ROOT / "fixtures" / "chictr"


class TestChiCTRHtml(unittest.TestCase):
    def test_parse_search_list(self):
        html = (FIXTURES / "search_sample.html").read_text(encoding="utf-8")
        trials = parse_search_html(html)
        self.assertEqual(len(trials), 2)
        self.assertEqual(trials[0].id, "ChiCTR2500111173")
        self.assertIn("胰腺癌", trials[0].title)
        self.assertEqual(trials[0].project_id, "2500111173")
        self.assertTrue(trials[0].url.endswith("proj=2500111173"))
        self.assertEqual(trials[1].id, "ChiCTR2400084905")

    def test_parse_detail(self):
        html = (FIXTURES / "detail_sample.html").read_text(encoding="utf-8")
        t = parse_detail_html(html, registration_number="ChiCTR2500111173")
        self.assertEqual(t.id, "ChiCTR2500111173")
        self.assertIn("胰腺癌", t.title)
        self.assertEqual(t.status, "招募中")
        self.assertEqual(t.condition, "胰腺癌")
        self.assertIn("CAR-T", t.intervention)
        self.assertEqual(t.phase, "I期")

    def test_adapt_ctgov_shape(self):
        html = (FIXTURES / "detail_sample.html").read_text(encoding="utf-8")
        t = parse_detail_html(html)
        study = adapt_to_ctgov_study(t)
        idm = study["protocolSection"]["identificationModule"]
        self.assertEqual(idm["nctId"], "ChiCTR2500111173")
        self.assertTrue(idm["briefTitle"])
        status = study["protocolSection"]["statusModule"]["overallStatus"]
        self.assertEqual(status, "RECRUITING")
        self.assertEqual(study["_source"], "chictr")

    def test_build_search_url(self):
        url = build_search_url(keyword="胰腺癌", year=2025, page=1)
        self.assertIn("searchproj.html", url)
        self.assertIn("createyear=2025", url)
        self.assertIn("btngo=btn", url)


if __name__ == "__main__":
    unittest.main()
