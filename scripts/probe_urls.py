"""Test candidate source URLs before a record is changed. Read-only.

Input: a text file with one URL per line, optionally followed by a space and a
regular expression. For an HTML page, links whose URL matches the expression
are listed, so a listing page can be searched for the current document link.
A line ending in " !text" (or " !fulltext" for the whole document) prints the opening text of the document instead
(PDF text needs the pypdf package), so its title, date and rescission notice
can be read without a browser.
Uses the same vetted fetcher as the source monitor. Prints one JSON line per URL.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor_sources import FetchError, fetch_once, validate_url  # noqa: E402

HREF = re.compile(rb"""href\s*=\s*["']([^"'#]+)["']""", re.I)


def document_text(body: bytes, content_type: str, pages: int = 4) -> str:
    if body[:5] == b"%PDF-":
        import io
        from pypdf import PdfReader
        return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(body)).pages[:pages])
    text = re.sub(r"(?s)<(script|style).*?</\1>", " ", body.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))


def probe(url: str, pattern: str | None, timeout: float) -> dict:
    out = {"url": url}
    try:
        validate_url(url)
        evidence = fetch_once(url, timeout, keep_body=bool(pattern))
    except FetchError as exc:
        out.update(result="failed", reason=exc.kind, detail=str(exc)[:160])
        return out
    body = evidence.pop("body", b"")
    if pattern == "!fulltext":
        out.update(result="opened", final_url=evidence["final_url"], content_type=evidence.get("content_type"),
                   bytes=evidence["bytes"], text=document_text(body, evidence.get("content_type") or "", pages=60)[:80000])
        return out
    if pattern == "!text":
        out.update(result="opened", final_url=evidence["final_url"], content_type=evidence.get("content_type"),
                   bytes=evidence["bytes"], text=document_text(body, evidence.get("content_type") or "")[:6000])
        return out
    out.update(result="opened", final_url=evidence["final_url"], content_type=evidence.get("content_type"),
               bytes=evidence["bytes"])
    if pattern:
        rx = re.compile(pattern)
        links = sorted({urljoin(evidence["final_url"], h.decode("utf-8", "replace"))
                        for h in HREF.findall(body)})
        out["matching_links"] = [l for l in links if rx.search(l)][:40]
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    for line in args.file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url, _, pattern = line.partition(" ")
        print(json.dumps(probe(url, pattern.strip() or None, args.timeout), ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
