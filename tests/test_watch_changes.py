"""Offline tests for the change watchers: fixed page fragments, no network."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import watch_changes as w

BOP_PAGE = """
<tr class="policy-item" data-url="/policy/progstat/5160_006.pdf">
    <td class="table-td" width="15%">&nbsp;5160.06</td>
    <td class="table-td" width="72%">
        <a style="text-decoration: none; color: inherit;" href="/policy/progstat/5160_006.pdf">
            Designation of State Institutions for Service of Federal Sentence
        </a>
    </td>
    <td class="table-td">09-03-2026</td>
</tr>
<tr class="policy-item" data-url="/policy/progstat/5410.01_cn2.pdf">
    <td class="table-td" width="15%">&nbsp;5410.01 CN-2</td>
    <td class="table-td" width="72%">
        <a href="/policy/progstat/5410.01_cn2.pdf">
            First Step Act of 2018 - Time Credits
        </a>
    </td>
    <td class="table-td">03-10-2023</td>
</tr>
<tr class="policy-item" data-url="/policy/progstat/5410.01_cn-2_spn.pdf">
    <td class="table-td" width="15%">&nbsp;5410.01 CN-2</td>
    <td class="table-td" width="72%"><a href="/policy/progstat/5410.01_cn-2_spn.pdf">Ley del Primer Paso</a></td>
    <td class="table-td">03-10-2023</td>
</tr>
"""

SCOTUS_PAGE = """
<tr>
    <td style="text-align: center;">1</td>
    <td style="text-align: center;">10/14/2026</td>
    <td style="text-align: center; white-space: nowrap;">26-101</td>
    <td><a href='/opinions/26pdf/26-101_abcd.pdf' id="x">Smith v. United States</a></td>
"""


def policy(aid, citation, status="official_current_agency_guidance"):
    return {"authority_id": aid, "authority_type": "policy", "citation": citation, "publication_status": status}


class ParserTests(unittest.TestCase):
    def test_bop_index_rows_skip_spanish_duplicates(self):
        rows = w.parse_bop_index(BOP_PAGE)
        self.assertEqual([("5160.06", None, "2026-09-03"), ("5410.01", "CN-2", "2023-03-10")],
                         [(r["number"], r["change_notice"], r["date"]) for r in rows])
        self.assertEqual("https://www.bop.gov/policy/progstat/5160_006.pdf", rows[0]["url"])

    def test_scotus_rows(self):
        rows = w.parse_scotus_term(SCOTUS_PAGE)
        self.assertEqual([{"date": "2026-10-14", "docket": "26-101", "name": "Smith v. United States",
                           "url": "https://www.supremecourt.gov/opinions/26pdf/26-101_abcd.pdf"}], rows)

    def test_term_year(self):
        self.assertEqual(2026, w.term_year(date(2026, 10, 5)))
        self.assertEqual(2025, w.term_year(date(2026, 6, 30)))


class WatcherTests(unittest.TestCase):
    def test_replaced_policy_is_found_and_rescinded_records_are_skipped(self):
        auths = [policy("AUTH-OLD", "BOP PS 5160.05 (Jan. 16, 2003)"),
                 policy("AUTH-GONE", "BOP PS 5160.05 (Jan. 16, 2003)", "rescinded_agency_guidance"),
                 policy("AUTH-FTC", "BOP Program Statement 5410.01 CN-2 (Mar. 10, 2023)")]
        found, state = w.watch_bop(auths, {}, lambda u: (BOP_PAGE, u), date(2026, 11, 9))
        self.assertEqual([("replaced", ["AUTH-OLD"])], [(f["kind"], f["affects"]) for f in found])
        self.assertIn("5160.06", found[0]["detail"])
        # A later date for the same version is reported as a reissue.
        later = BOP_PAGE.replace("03-10-2023", "11-02-2026")
        found, _ = w.watch_bop(auths[2:], state, lambda u: (later, u), date(2026, 11, 16))
        self.assertEqual(["reissued"], [f["kind"] for f in found])

    def test_federal_register_reports_each_new_document_once(self):
        auths = [{"authority_id": "AUTH-CFR", "authority_type": "regulation", "citation": "28 C.F.R. §§ 523.40–523.44"}]
        doc = {"document_number": "2026-99999", "title": "Time Credits", "type": "Rule", "publication_date": "2026-11-02",
               "effective_on": "2026-12-02", "html_url": "https://www.federalregister.gov/d/2026-99999", "citation": "91 FR 70000"}
        page = json.dumps({"results": [doc, {**doc, "document_number": "2026-17752"}]})
        asked = []
        get = lambda u: (asked.append(u), (page, u))[1]
        found, state = w.watch_federal_register(auths, {"seen": ["2026-17752"], "checked_through": "2026-08-25"}, get, date(2026, 11, 9))
        self.assertEqual([("rule", ["AUTH-CFR"])], [(f["kind"], f["affects"]) for f in found])
        self.assertIn("conditions%5Bcfr%5D%5Bpart%5D=523", asked[0])
        found, _ = w.watch_federal_register(auths, state, get, date(2026, 11, 16))
        self.assertEqual([], found)

    def test_supreme_court_flags_cases_with_the_united_states(self):
        found, state = w.watch_supreme_court([], {}, lambda u: (SCOTUS_PAGE, u), date(2026, 11, 9))
        self.assertEqual([("new_opinion", "review")], [(f["kind"], f["severity"]) for f in found])
        found, _ = w.watch_supreme_court([], state, lambda u: (SCOTUS_PAGE, u), date(2026, 11, 16))
        self.assertEqual([], found)

    def test_rules_first_run_records_quietly_but_flags_proposals_near_december(self):
        page = '<a href="/sites/default/files/document/2026-scotus-package.pdf">package</a>'
        auths = [{"authority_id": "AUTH-PROP", "authority_type": "rule", "citation": "Proposed Fed. R. Crim. P. 17 amendment"}]
        url = "https://www.uscourts.gov/forms-rules/pending-rules-and-forms-amendments"
        found, state = w.watch_rules(auths, {}, lambda u: (page, url), date(2026, 11, 9))
        self.assertEqual(["effective_date_near"], [f["kind"] for f in found])
        newer = page + '<a href="/sites/default/files/document/2027-scotus-package.pdf">next</a>'
        found, _ = w.watch_rules(auths, state, lambda u: (newer, url), date(2027, 3, 1))
        self.assertEqual(["new_document"], [f["kind"] for f in found])

    def test_new_uscode_edition(self):
        auths = [{"authority_id": "AUTH-USC", "official_url": "https://www.govinfo.gov/link/uscode/18/3585"}]
        final = "https://www.govinfo.gov/content/pkg/USCODE-2025-title18/pdf/x.pdf"
        found, state = w.watch_uscode(auths, {"editions": {"18": "2024"}}, lambda u: ("", final), date(2027, 2, 1))
        self.assertEqual(["new_edition"], [f["kind"] for f in found])
        self.assertEqual({"18": "2025"}, state["editions"])

    def test_failing_watcher_keeps_its_last_state_and_others_still_run(self):
        def get(url):
            if "bop.gov" in url:
                raise w.fetch_once.__globals__["FetchError"]("timeout", "timed out")
            return ("", url)
        auths = [policy("AUTH-OLD", "BOP PS 5160.05 (Jan. 16, 2003)")]
        state = {"watchers": {"bop_policies": {"listing": {"5160": []}}}}
        report, new_state = w.run(auths, [], state, get, date(2026, 11, 9))
        self.assertEqual(["bop_policies"], [e["watcher"] for e in report["errors"]])
        self.assertEqual({"listing": {"5160": []}}, new_state["watchers"]["bop_policies"])
        self.assertIn("supreme_court", new_state["watchers"])
        self.assertFalse(report["legal_review_performed"])

    def test_review_dates_and_link_changes(self):
        mods = [{"module_id": "MOD-A", "next_review_date": "2026-11-23"}, {"module_id": "MOD-B", "next_review_date": "2027-02-01"}]
        self.assertEqual([["MOD-A"]], [f["affects"] for f in w.watch_review_dates(mods, date(2026, 11, 9))])
        before = {"sources": {"S1": {"url": "u1", "result": "opened"}, "S2": {"url": "u2", "result": "failed"}}}
        after = {"sources": {"S1": {"url": "u1", "result": "failed", "reason": "http_error"}, "S2": {"url": "u2", "result": "opened"}}}
        self.assertEqual(["newly_failing", "recovered"], [f["kind"] for f in w.link_changes(before, after)])

    def test_newly_failing_sources_are_grouped_by_host(self):
        before = {"sources": {s: {"url": f"https://www.ussc.gov/{s}", "result": "opened"} for s in ("A", "B")}}
        after = {"sources": {s: {"url": f"https://www.ussc.gov/{s}", "result": "failed", "reason": "http_error", "detail": "HTTP 403"} for s in ("A", "B")}}
        found = w.link_changes(before, after)
        self.assertEqual([("newly_failing", ["A", "B"])], [(f["kind"], f["affects"]) for f in found])

    def test_guidelines_manual_superseded_after_november_first(self):
        auths = [{"authority_id": "AUTH-G", "authority_type": "guideline", "citation": "U.S.S.G. § 1B1.10 (2025)"},
                 {"authority_id": "AUTH-H", "authority_type": "guideline", "citation": "U.S.S.G. §§ 1B1.1, 1B1.11 (Nov. 1, 2025)"}]
        self.assertEqual([], w.watch_guidelines(auths, date(2026, 10, 31)))
        found = w.watch_guidelines(auths, date(2026, 11, 1))
        self.assertEqual([("manual_superseded", ["AUTH-G", "AUTH-H"])], [(f["kind"], f["affects"]) for f in found])


if __name__ == "__main__":
    unittest.main()
