"""Offline safety and behavior checks; no network requests are made."""
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import monitor_sources as monitor


URL = "https://www.govinfo.gov/test.pdf"


def evidence(body=b"official source body", url=URL):
    return {"requested_url": url, "final_url": url, "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body), "full_body_read": True, "http_status": 200}


def record(sid="SRC-TEST", url=URL):
    return {"source_id": sid, "url": url, "authority_ids": ["AUTH-TEST"],
            "claim_ids": ["CLM-TEST"], "module_ids": ["MOD-TEST"]}


class Response:
    def __init__(self, body=b"content", status=200, headers=None):
        self.body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}

    def read(self, limit):
        return self.body.read(limit)

    def getheader(self, key, default=None):
        return self.headers.get(key, default)


class URLSafetyTests(unittest.TestCase):
    def test_approved_hosts(self):
        for url in (URL, "https://www.ca9.uscourts.gov/rules", "https://law.justia.com/test"):
            monitor.validate_url(url)

    def test_unsafe_urls(self):
        for url in ("file:///etc/passwd", "http://localhost/test", "https://127.0.0.1/test",
                    "https://www.govinfo.gov.evil.example/test", "https://x@example.gov/test",
                    "https://example.gov:8443/test", "https://example.gov./test",
                    "https://example.gov\\@localhost/test", "https://example.gov/\nfoo",
                    "https://[::1]/test"):
            with self.subTest(url=url), self.assertRaises(monitor.FetchError):
                monitor.validate_url(url)

    @patch.object(monitor.socket, "getaddrinfo")
    def test_private_dns_rejected_even_with_public_answer(self, resolver):
        for private in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "224.0.0.1"):
            resolver.return_value = [(None, None, None, None, ("8.8.8.8", 443)),
                                     (None, None, None, None, (private, 443))]
            with self.subTest(private=private), self.assertRaises(monitor.FetchError):
                monitor.public_addresses("example.gov", 443)

    @patch.object(monitor.socket, "getaddrinfo", side_effect=socket.gaierror("failed"))
    def test_dns_failure_classified(self, resolver):
        with self.assertRaises(monitor.FetchError) as ctx:
            monitor.public_addresses("example.gov", 443)
        self.assertEqual(ctx.exception.kind, "dns_error")


class FetchTests(unittest.TestCase):
    def fetch(self, responses, **kwargs):
        connections = []
        for response in responses:
            connection = Mock()
            connection.sock = Mock()
            connection.getresponse.return_value = response
            connections.append(connection)
        with patch.object(monitor, "public_addresses", return_value=["8.8.8.8"]), \
                patch.object(monitor, "PinnedConnection", side_effect=connections):
            return monitor.fetch_once(URL, **kwargs)

    def test_full_body_hash(self):
        body = b"a" * 130000
        result = self.fetch([Response(body, headers={"Content-Length": str(len(body))})])
        self.assertEqual(result["sha256"], hashlib.sha256(body).hexdigest())
        self.assertEqual(result["bytes"], len(body))
        self.assertTrue(result["full_body_read"])

    def test_oversized_declared_and_streamed(self):
        for response in (Response(b"abc", headers={"Content-Length": "999"}), Response(b"123456")):
            with self.assertRaises(monitor.FetchError) as ctx:
                self.fetch([response], max_bytes=5)
            self.assertEqual(ctx.exception.kind, "oversized")

    def test_incomplete_and_empty_rejected(self):
        for response in (Response(b"abc", headers={"Content-Length": "6"}), Response(b"")):
            with self.assertRaises(monitor.FetchError) as ctx:
                self.fetch([response])
            self.assertEqual(ctx.exception.kind, "incomplete_body")

    def test_unsafe_redirect_rejected_before_connect(self):
        with self.assertRaises(monitor.FetchError):
            self.fetch([Response(status=302, headers={"Location": "http://127.0.0.1/secrets"})])

    def test_https_downgrade_rejected(self):
        with self.assertRaises(monitor.FetchError) as ctx:
            self.fetch([Response(status=302, headers={"Location": "http://www.govinfo.gov/test"})])
        self.assertEqual(ctx.exception.kind, "unsafe_redirect")

    def test_public_redirect_recorded(self):
        result = self.fetch([Response(status=302, headers={"Location": "/new.pdf"}), Response(b"new")])
        self.assertEqual(result["final_url"], "https://www.govinfo.gov/new.pdf")
        self.assertEqual(len(result["redirects"]), 1)

    def test_redirect_loop_rejected(self):
        with self.assertRaises(monitor.FetchError) as ctx:
            self.fetch([Response(status=302, headers={"Location": "/again"}) for _ in range(6)])
        self.assertEqual(ctx.exception.kind, "redirect_error")

    def test_non_200_is_failure(self):
        with self.assertRaises(monitor.FetchError) as ctx:
            self.fetch([Response(status=404)])
        self.assertEqual(ctx.exception.kind, "http_error")
        self.assertFalse(ctx.exception.retryable)

    @patch.object(monitor.time, "sleep")
    @patch.object(monitor, "fetch_once")
    def test_transient_failure_retried(self, fetch, sleep):
        fetch.side_effect = [monitor.FetchError("timeout", "timed out", True), evidence()]
        result = monitor.fetch_source(URL)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["previous_attempt_errors"][0]["kind"], "timeout")

    @patch.object(monitor, "fetch_once", side_effect=monitor.FetchError("unsafe_url", "rejected"))
    def test_unsafe_failure_not_retried(self, fetch):
        result = monitor.fetch_source(URL, retries=3)
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["error"]["kind"], "unsafe_url")


class ReportTests(unittest.TestCase):
    def test_deduplicates_url_preserving_identities(self):
        fetch = Mock(return_value=evidence())
        report, candidate = monitor.monitor([record(), record("SRC-SECOND")], {}, [], date(2026, 10, 2), fetch, 0)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(report["results"][0]["identities"]), 2)
        self.assertEqual(report["counts"], {"no_accepted_baseline": 1})
        self.assertEqual(candidate["kind"], "unaccepted_source_identity_candidates")
        self.assertFalse(report["legal_verification_performed"])

    def test_unchanged_and_changed(self):
        for body, expected in ((b"old", "unchanged_bytes"), (b"new", "identity_changed")):
            report, _ = monitor.monitor([record()], {URL: evidence(b"old")}, [], date(2026, 10, 2),
                                        lambda url: evidence(body), 0)
            self.assertEqual(report["results"][0]["status"], expected)

    def test_failure_does_not_stop_unaffected_source(self):
        fetch = Mock(side_effect=[{"error": {"kind": "redirect_error", "message": "bad redirect"}}, evidence()])
        report, candidate = monitor.monitor([record(url="https://www.govinfo.gov/bad"), record("SRC-GOOD")],
                                             {}, [], date(2026, 10, 2), fetch, 0)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(report["counts"], {"fetch_failed": 1, "no_accepted_baseline": 1})
        self.assertEqual(list(candidate["snapshots"]), [URL])

    def test_due_dates_missing_dates_and_future_dates(self):
        modules = [{"module_id": "A", "next_review_date": "2026-10-01"},
                   {"module_id": "B", "next_review_date": "2026-10-02"},
                   {"module_id": "C", "next_review_date": "2026-10-03"}, {"module_id": "D"}]
        queue = monitor.review_dates(modules, date(2026, 10, 2))
        self.assertEqual([r["module_id"] for r in queue], ["A", "B", "D"])

    def test_unaccepted_candidate_cannot_be_used_as_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.json"
            path.write_text(json.dumps({"kind": "unaccepted_source_identity_candidates", "snapshots": {URL: evidence()}}))
            with self.assertRaises(ValueError):
                monitor.load_baseline(path)
            path.write_text(json.dumps({"kind": "manually_accepted_source_identity_baseline",
                                       "reviewed_by": "Maintainer", "reviewed_at": "2026-10-02",
                                       "snapshots": {URL: evidence()}}))
            self.assertEqual(monitor.load_baseline(path)[URL]["sha256"], evidence()["sha256"])

    def test_changed_redirect_destination_requires_review_even_if_bytes_match(self):
        changed = evidence()
        changed["final_url"] = "https://www.govinfo.gov/other.pdf"
        report, _ = monitor.monitor([record()], {URL: evidence()}, [], date(2026, 10, 2),
                                    lambda url: changed, 0)
        self.assertEqual(report["counts"], {"identity_changed": 1})

    def test_missing_url_is_reported_without_request(self):
        fetch = Mock()
        report, _ = monitor.monitor([record(url=None)], {}, [], date(2026, 10, 2), fetch, 0)
        fetch.assert_not_called()
        self.assertEqual(report["results"][0]["evidence"]["error"]["kind"], "missing_url")


class InventoryAndCLITests(unittest.TestCase):
    def fixture(self, root):
        (root / "data").mkdir()
        (root / "sources").mkdir()
        (root / "sources/source_registry.yaml").write_text(json.dumps({"sources": [
            {"source_id": "SRC-ONE", "official_url": URL, "authority_id": "AUTH-ONE"},
            {"source_id": "SRC-MIRROR", "official_url": None, "mirror_url": "https://law.justia.com/test"}
        ]}), encoding="utf-8")
        (root / "data/authorities.jsonl").write_text(json.dumps({"source_id": "SRC-ONE", "authority_id": "AUTH-ONE",
            "linked_claim_ids": ["CLM-LINK"], "linked_module_ids": ["MOD-LINK"]}) + "\n", encoding="utf-8")
        (root / "data/claims.jsonl").write_text(json.dumps({"claim_id": "CLM-ONE", "module_id": "MOD-ONE",
            "authority_ids": ["AUTH-ONE"]}) + "\n", encoding="utf-8")
        (root / "data/modules.json").write_text("[]", encoding="utf-8")
        (root / "data/federal_districts.yaml").write_text(json.dumps({"courts": [
            {"court_id": "USDC-ONE", "rules_landing_url": URL}]}), encoding="utf-8")
        (root / "data/district_rule_catalog.json").write_text(json.dumps({"courts": [
            {"court_id": "USDC-ONE", "documents": [{"url": URL}]}]}), encoding="utf-8")

    def test_inventory_dependencies_and_district_identity_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            records = monitor.collect_sources(root, True)
            self.assertEqual(len(records), 4)
            self.assertEqual(records[0]["claim_ids"], ["CLM-LINK", "CLM-ONE"])
            self.assertEqual(records[0]["module_ids"], ["MOD-LINK", "MOD-ONE"])
            self.assertEqual(records[1]["source_role"], "mirror_not_official")
            self.assertEqual(records[2]["court_id"], "USDC-ONE")

    @patch.object(monitor, "fetch_source", return_value=evidence())
    def test_cli_writes_only_review_outputs_and_preserves_inputs(self, fetch):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            result = monitor.main(["--root", str(root), "--source-id", "SRC-ONE", "--delay", "0"])
            self.assertEqual(result, 1)
            report_path = next((root / ".review").glob("*/report.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["selection"]["is_partial_selection"])
            for path, content in before.items():
                self.assertEqual((root / path).read_bytes(), content)
            self.assertEqual(len(list((root / ".review").rglob("*.json"))), 2)

    @patch.object(monitor, "fetch_source")
    def test_cli_unknown_source_fails_before_network(self, fetch):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.assertEqual(monitor.main(["--root", str(root), "--source-id", "UNKNOWN"]), 3)
            fetch.assert_not_called()

    @patch.object(monitor, "fetch_source", return_value={"error": {"kind": "http_error", "message": "HTTP 403"}})
    def test_cli_failure_still_writes_evidence(self, fetch):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.fixture(root)
            self.assertEqual(monitor.main(["--root", str(root), "--source-id", "SRC-ONE"]), 2)
            self.assertTrue(list((root / ".review").glob("*/report.json")))


if __name__ == "__main__":
    unittest.main()
