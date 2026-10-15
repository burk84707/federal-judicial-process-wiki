"""Read-only source identity monitor. A byte change is not a change in law."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
import uuid

import yaml

MAX_BYTES = 16 * 1024 * 1024
REPUTABLE_HOSTS = {"www.courtlistener.com", "courtlistener.com", "storage.courtlistener.com", "law.justia.com",
                   "cases.justia.com", "openjurist.org", "www.openjurist.org",
                   "www.law.cornell.edu"}
REDIRECTS = {301, 302, 303, 307, 308}
ERROR_PAGE = re.compile(r"(^|/)(error|errors|404|not-?found)(/|\.|$)|pagenotfound", re.I)


class FetchError(Exception):
    """A classified, reportable source-access failure."""

    def __init__(self, kind: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


def validate_url(url: str) -> tuple[str, str, int]:
    """Only known source domains; no credentials, IP literals, or unusual ports."""
    try:
        if not isinstance(url, str) or any(ord(c) < 33 for c in url) or "\\" in url:
            raise ValueError("invalid URL characters")
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or not host:
            raise ValueError("only absolute HTTP(S) source URLs are permitted")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("credentials and fragments are not permitted")
        if not re.fullmatch(r"[a-z0-9.-]+", host) or host.endswith("."):
            raise ValueError("invalid hostname")
        if not (host.endswith(".gov") or host in REPUTABLE_HOSTS):
            raise ValueError("host is outside the reviewed source-domain allowlist")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port != (443 if parsed.scheme == "https" else 80):
            raise ValueError("nonstandard ports are not permitted")
        return parsed.scheme, host, port
    except ValueError as exc:
        raise FetchError("unsafe_url", str(exc)) from exc


def public_addresses(host: str, port: int) -> list[str]:
    """Reject a DNS answer if ANY answer is private, local, reserved, or invalid."""
    try:
        # IPv4 first: many runners have no IPv6 route. Every answer is still vetted.
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(
            host, port, type=socket.SOCK_STREAM)},
            key=lambda a: (ipaddress.ip_address(a).version, a))
    except socket.gaierror as exc:
        raise FetchError("dns_error", str(exc), True) from exc
    if not addresses:
        raise FetchError("dns_error", "DNS returned no addresses", True)
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip.is_multicast or ip.is_unspecified:
            raise FetchError("unsafe_address", "DNS resolved to a non-public address")
    return addresses


class PinnedConnection(http.client.HTTPConnection):
    """Connect to a vetted IP without a second hostname lookup (DNS rebinding)."""

    def __init__(self, host: str, port: int, addresses: list[str], timeout: float, tls: bool):
        super().__init__(host, port, timeout=timeout)
        self.addresses = addresses
        self.tls = tls

    def connect(self):
        # Try each vetted address in turn; only an unreachable address moves on.
        for index, address in enumerate(self.addresses):
            try:
                raw = socket.create_connection((address, self.port), self.timeout)
                break
            except OSError:
                if index == len(self.addresses) - 1:
                    raise
        try:
            self.sock = (ssl.create_default_context().wrap_socket(
                raw, server_hostname=self.host) if self.tls else raw)
        except Exception:
            raw.close()
            raise


def fetch_once(url: str, timeout: float = 20, max_bytes: int = MAX_BYTES, keep_body: bool = False) -> dict:
    """Follow at most five independently validated redirects; hash a full body.

    keep_body returns the bytes too; only the URL probe uses it, never the monitor."""
    current = url
    chain = []
    started = time.monotonic()
    for hop in range(6):
        scheme, host, port = validate_url(current)
        addresses = public_addresses(host, port)
        parsed = urlsplit(current)
        target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        # The vetted numeric address is pinned for the connection. No proxies,
        # cookies, authorization headers, or environment-derived credentials.
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise FetchError("timeout", "source attempt exceeded time budget", True)
        conn = PinnedConnection(host, port, addresses, remaining, scheme == "https")
        try:
            conn.request("GET", target, headers={
                "User-Agent": "FederalProcessSourceReview/1.0 (review-only)",
                "Accept-Encoding": "identity", "Accept": "*/*"})
            response = conn.getresponse()
            if response.status in REDIRECTS:
                location = response.getheader("Location")
                if not location:
                    raise FetchError("redirect_error", "redirect has no Location header")
                next_url = urljoin(current, location)
                validate_url(next_url)
                if scheme == "https" and urlsplit(next_url).scheme != "https":
                    raise FetchError("unsafe_redirect", "HTTPS downgrade rejected")
                chain.append({"url": current, "status": response.status, "to": next_url})
                if hop == 5:
                    raise FetchError("redirect_error", "more than five redirects")
                current = next_url
                continue
            if response.status != 200:
                raise FetchError("http_error", f"HTTP {response.status}",
                                 response.status == 429 or response.status >= 500)
            encoding = response.getheader("Content-Encoding", "identity").lower()
            if encoding not in {"identity", ""}:
                raise FetchError("unsupported_encoding", "server ignored identity encoding request")
            length = response.getheader("Content-Length")
            try:
                declared = int(length) if length is not None else None
            except ValueError as exc:
                raise FetchError("invalid_response", "invalid Content-Length") from exc
            if declared is not None and (declared < 0 or declared > max_bytes):
                raise FetchError("oversized" if declared > max_bytes else "invalid_response",
                                 "declared body length is outside permitted bounds")
            digest = hashlib.sha256()
            size = 0
            kept = []
            while True:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise FetchError("timeout", "source attempt exceeded time budget", True)
                if conn.sock is not None:
                    conn.sock.settimeout(remaining)
                chunk = response.read(min(65536, max_bytes + 1 - size))
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise FetchError("oversized", "body exceeded limit; no partial hash accepted")
                digest.update(chunk)
                if keep_body:
                    kept.append(chunk)
            if size == 0 or (declared is not None and size != declared):
                raise FetchError("incomplete_body", "empty or incomplete response body", True)
            # A redirect to an error page, or a web page where a PDF was asked for, is not the source.
            final_path = urlsplit(current).path.lower()
            if ERROR_PAGE.search(final_path):
                raise FetchError("error_page", f"redirected to an error page: {current}")
            content_type = (response.getheader("Content-Type") or "").lower()
            if urlsplit(url).path.lower().endswith(".pdf") and "html" in content_type:
                raise FetchError("unexpected_content", "a PDF was requested but a web page was returned")
            result = {"requested_url": url, "final_url": current, "http_status": 200,
                    "sha256": digest.hexdigest(), "bytes": size, "full_body_read": True,
                    "content_type": response.getheader("Content-Type"),
                    "etag": response.getheader("ETag"),
                    "last_modified": response.getheader("Last-Modified"), "redirects": chain}
            if keep_body:
                result["body"] = b"".join(kept)
            return result
        except FetchError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise FetchError("timeout", str(exc), True) from exc
        except ssl.SSLError as exc:
            raise FetchError("tls_error", str(exc)) from exc
        except (OSError, http.client.HTTPException) as exc:
            raise FetchError("network_error", str(exc), True) from exc
        finally:
            conn.close()
    raise FetchError("redirect_error", "redirect limit exceeded")


def fetch_source(url: str, timeout: float = 20, retries: int = 1,
                 max_bytes: int = MAX_BYTES) -> dict:
    failures = []
    for attempt in range(retries + 1):
        try:
            result = fetch_once(url, timeout, max_bytes)
            result["attempts"] = attempt + 1
            result["previous_attempt_errors"] = failures
            return result
        except FetchError as exc:
            failures.append({"kind": exc.kind, "message": str(exc)})
            if not exc.retryable or attempt == retries:
                return {"requested_url": url, "error": failures[-1],
                        "attempts": attempt + 1, "attempt_errors": failures}
            time.sleep(min(2 ** attempt, 4))
    raise AssertionError("unreachable")


def load_data(path: Path):
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) if path.suffix in {".yaml", ".yml"} else json.load(stream)


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def collect_sources(root: Path, include_districts: bool = False) -> list[dict]:
    registry = load_data(root / "sources/source_registry.yaml")
    authorities = load_jsonl(root / "data/authorities.jsonl")
    claims = load_jsonl(root / "data/claims.jsonl")
    records = []
    for source in registry["sources"]:
        sid = source["source_id"]
        authority_ids = set(source.get("additional_authority_ids", []))
        if source.get("authority_id"):
            authority_ids.add(source["authority_id"])
        authority_ids.update(a["authority_id"] for a in authorities if a.get("source_id") == sid)
        linked = [c for c in claims if authority_ids.intersection(c.get("authority_ids", []))]
        related = [a for a in authorities if a["authority_id"] in authority_ids]
        records.append({"source_id": sid,
                        "url": source.get("official_url") or source.get("mirror_url"),
                        "source_role": "official" if source.get("official_url") else "mirror_not_official",
                        "authority_ids": sorted(authority_ids),
                        "claim_ids": sorted({c["claim_id"] for c in linked} |
                                            {cid for a in related for cid in a.get("linked_claim_ids", [])}),
                        "module_ids": sorted({c["module_id"] for c in linked} |
                                             {mid for a in related for mid in a.get("linked_module_ids", [])})})
    if include_districts:
        district_data = load_data(root / "data/federal_districts.yaml")
        catalog = load_data(root / "data/district_rule_catalog.json")
        for court in district_data["courts"]:
            records.append({"source_id": f"DISTRICT-{court['court_id']}-LANDING",
                            "url": court["rules_landing_url"], "source_role": "official_district_location",
                            "court_id": court["court_id"], "authority_ids": [], "claim_ids": [], "module_ids": []})
        for court in catalog["courts"]:
            for doc in court["documents"]:
                suffix = hashlib.sha256(doc["url"].encode()).hexdigest()[:20]
                records.append({"source_id": f"DISTRICT-{court['court_id']}-{suffix}",
                                "url": doc["url"], "source_role": "district_catalog_candidate",
                                "court_id": court["court_id"], "authority_ids": [], "claim_ids": [], "module_ids": []})
    ids = [r["source_id"] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError("source inventory contains duplicate source IDs")
    return records


def review_dates(modules: list[dict], today: date) -> list[dict]:
    results = []
    for module in modules:
        raw = module.get("next_review_date")
        try:
            due = date.fromisoformat(str(raw))
        except ValueError:
            results.append({"module_id": module["module_id"], "status": "review_date_missing_or_invalid"})
            continue
        if due <= today:
            results.append({"module_id": module["module_id"], "status": "review_due",
                            "next_review_date": due.isoformat(), "days_overdue": (today - due).days})
    return results


def load_baseline(path: Path | None) -> dict:
    if path is None:
        return {}
    data = load_data(path)
    if data.get("kind") != "manually_accepted_source_identity_baseline" or not data.get("reviewed_by") or not data.get("reviewed_at"):
        raise ValueError("baseline must be explicitly manually accepted with reviewed_by and reviewed_at")
    snapshots = data["snapshots"]
    if not isinstance(snapshots, dict):
        raise ValueError("baseline snapshots must be a URL-keyed object")
    for url, snapshot in snapshots.items():
        validate_url(url)
        if not re.fullmatch(r"[0-9a-f]{64}", snapshot.get("sha256", "")):
            raise ValueError("baseline snapshot has no valid complete-body SHA-256")
        if snapshot.get("full_body_read") is not True:
            raise ValueError("baseline may not contain partial reads")
    return snapshots


def monitor(records: list[dict], baseline: dict, modules: list[dict], today: date,
            fetcher=fetch_source, delay: float = 0.25) -> tuple[dict, dict]:
    grouped = {}
    for record in records:
        grouped.setdefault(record.get("url"), []).append(record)
    results, candidates = [], {}
    for index, (url, identities) in enumerate(grouped.items()):
        if index and delay:
            time.sleep(delay)
        if not url:
            evidence = {"error": {"kind": "missing_url", "message": "No official or mirror URL recorded"}}
        else:
            evidence = fetcher(url)
        if evidence.get("error"):
            status = "fetch_failed"
        else:
            old = baseline.get(url)
            status = ("no_accepted_baseline" if old is None else
                      "unchanged_bytes" if old["sha256"] == evidence["sha256"] and
                      old.get("final_url") == evidence.get("final_url") else "identity_changed")
            candidates[url] = evidence
        results.append({"url": url, "status": status, "identities": identities, "evidence": evidence})
    counts = dict(Counter(r["status"] for r in results))
    report = {"schema_version": 1, "kind": "source_identity_review_report", "review_only": True,
              "legal_verification_performed": False, "canonical_files_changed": False,
              "automatic_promotion_enabled": False, "as_of": today.isoformat(),
              "source_identity_count": len(records), "unique_url_count": len(grouped),
              "counts": counts, "results": results, "module_review_queue": review_dates(modules, today),
              "limitations": ["Byte equality does not establish current law or valid legal conclusions.",
                              "This monitor does not discover newly issued authorities or new district documents.",
                              "A changed hash may reflect navigation, timestamps, or other nonlegal changes.",
                              "Mirror sources are not promoted to official authority."]}
    candidate = {"schema_version": 1, "kind": "unaccepted_source_identity_candidates",
                 "automatic_acceptance": False, "snapshots": candidates}
    return report, candidate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--include-districts", action="store_true")
    parser.add_argument("--limit", type=int, help="Explicit bounded subset of source identities; recorded in report")
    parser.add_argument("--inventory-only", action="store_true", help="Validate/list identities without any requests")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args(argv)
    if not (0 < args.timeout <= 120 and 0 <= args.retries <= 3 and 0 <= args.delay <= 60):
        parser.error("timeout must be 0–120 seconds, retries 0–3, delay 0–60 seconds")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    try:
        root = args.root.resolve()
        records = collect_sources(root, args.include_districts)
        total = len(records)
        if args.source_id:
            missing = set(args.source_id) - {r["source_id"] for r in records}
            if missing:
                raise ValueError("unknown source IDs: " + ", ".join(sorted(missing)))
            records = [r for r in records if r["source_id"] in args.source_id]
        if args.limit:
            records = records[:args.limit]
        if args.inventory_only:
            print(json.dumps({"inventory_count": total, "selected_count": len(records), "sources": records}, indent=2))
            return 0
        baseline = load_baseline(args.baseline)
        modules = load_data(root / "data/modules.json")
        started = datetime.now(timezone.utc)
        report, candidate = monitor(records, baseline, modules, started.date(),
                                    lambda url: fetch_source(url, args.timeout, args.retries), args.delay)
        report["started_at"] = started.isoformat()
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["selection"] = {"available_identity_count": total, "include_districts": args.include_districts,
                               "source_ids": args.source_id, "limit": args.limit,
                               "is_partial_selection": len(records) != total}
        # Fixed ignored destination; never permit output to canonical source paths.
        review_root = root / ".review"
        if review_root.is_symlink() or (review_root.exists() and review_root.resolve() != review_root):
            raise ValueError(".review must be a real directory inside the repository")
        destination = review_root / (started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
        destination.mkdir(parents=True, exist_ok=False)
        for name, content in (("report.json", report), ("candidate-baseline.json", candidate)):
            (destination / name).write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Review evidence: .review/{destination.name}/report.json")
        print(json.dumps(report["counts"], sort_keys=True))
        if report["counts"].get("fetch_failed"):
            return 2
        if (report["counts"].get("identity_changed") or report["counts"].get("no_accepted_baseline")
                or report["module_review_queue"]):
            return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, FetchError) as exc:
        print(f"Monitor input/output error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
