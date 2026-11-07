"""Watch the publishers that change the law this reference relies on. Read-only.

Each watcher reads one official source, compares it with the state saved from
the last run (maintenance/watch_state.json), and reports what is new. Nothing
here edits a claim, an authority or a review date: every finding is for a
person to review.

Watchers
  bop_policies      BOP policy index: a cited program statement replaced,
                    reissued or given a new change notice.
  federal_register  Federal Register: rules and proposed rules affecting a
                    cited CFR part.
  supreme_court     Supreme Court opinions issued this term.
  rules_amendments  Federal courts' pending-amendments page: new documents,
                    and cited proposed rules near their December 1 date.
  uscode_edition    GovInfo: a new edition of a cited U.S. Code title.
  review_dates      Modules due for legal review within 21 days.

Usage: python scripts/watch_changes.py --state maintenance/watch_state.json
           --out .review/watch [--today YYYY-MM-DD] [--previous-link-check data/link_check.json
           --link-check .review/link_check.json]
Writes report.json, report.md and watch_state.json to --out. Exit code 0 means
the run completed (with or without findings); 3 means it could not run.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode, urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from monitor_sources import fetch_once  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SINCE = "2026-08-25"  # the research baseline: earlier changes are already reviewed
BOP_ROW = re.compile(r'<tr class="policy-item" data-url="(?P<url>[^"]+)">\s*<td[^>]*>\s*(?:&nbsp;)?\s*(?P<number>\d{4}\.\d{2})(?:\s*(?P<cn>CN-\d+))?\s*</td>'
                     r'\s*<td[^>]*>\s*<a[^>]*>\s*(?P<title>.*?)\s*</a>\s*</td>\s*<td[^>]*>(?P<date>\d{2}-\d{2}-\d{4})</td>', re.S)
CITED_PS = re.compile(r"\b(\d{4})\.(\d{2})\b(?:\s*,?\s*(?:CN|Change Notice)[\s-]*(\d+))?", re.I)
CFR_PART = re.compile(r"(\d+) C\.F\.R\. (?:§§?\s*|pts?\.\s*|parts?\s+)(\d+)")
SCOTUS_ROW = re.compile(r"<tr>\s*<td[^>]*>\s*(?P<r>\d+)\s*</td>\s*<td[^>]*>\s*(?P<date>\d{1,2}/\d{1,2}/\d{4})\s*</td>\s*<td[^>]*>\s*(?P<docket>[^<]+?)\s*</td>"
                        r"\s*<td[^>]*>\s*<a href='(?P<href>[^']+)'[^>]*>(?P<name>.*?)</a>", re.S)
GOVINFO_EDITION = re.compile(r"USCODE-(\d{4})-title(\d+)")
PDF_LINK = re.compile(r"""href=["']([^"']+\.pdf)["']""", re.I)


def text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def fetch(url: str, timeout: float) -> tuple[str, str]:
    evidence = fetch_once(url, timeout, keep_body=True)
    return evidence["body"].decode("utf-8", "replace"), evidence["final_url"]


def finding(watcher, kind, title, detail, url=None, affects=(), severity="review"):
    return {"watcher": watcher, "kind": kind, "severity": severity, "title": title, "detail": detail,
            "url": url, "affects": sorted(set(affects))}


# --- parsers (pure functions, tested offline) -------------------------------------------

def parse_bop_index(page: str) -> list[dict]:
    rows = []
    for m in BOP_ROW.finditer(page):
        if "_spn" in m.group("url").lower():
            continue  # Spanish translations duplicate the English entry
        mm, dd, yyyy = m.group("date").split("-")
        rows.append({"number": m.group("number"), "change_notice": m.group("cn"), "title": text(m.group("title")),
                     "date": f"{yyyy}-{mm}-{dd}", "url": urljoin("https://www.bop.gov/", m.group("url"))})
    return rows


def parse_scotus_term(page: str) -> list[dict]:
    rows = []
    for m in SCOTUS_ROW.finditer(page):
        mo, d, y = m.group("date").split("/")
        rows.append({"date": f"{y}-{int(mo):02d}-{int(d):02d}", "docket": text(m.group("docket")),
                     "name": text(m.group("name")), "url": urljoin("https://www.supremecourt.gov/", m.group("href"))})
    return rows


def term_year(today: date) -> int:
    return today.year if today.month >= 10 else today.year - 1


# --- watchers ---------------------------------------------------------------------------

def watch_bop(authorities, state, get, today):
    cited = []
    for a in authorities:
        if a["authority_type"] != "policy" or "BOP" not in a["citation"]:
            continue
        if any(w in a["publication_status"] for w in ("rescinded", "archived")):
            continue
        m = CITED_PS.search(a["citation"])
        if m:
            cn = f"CN-{m.group(3)}" if m.group(3) else None
            cited.append((a["authority_id"], m.group(1), f"{m.group(1)}.{m.group(2)}", cn, a["citation"]))
    findings, listing = [], {}
    for series in sorted({c[1][0] + "000" for c in cited}):
        page, _ = get(f"https://www.bop.gov/PublicInfo/execute/policysearch?todo=query&series={series}")
        for row in parse_bop_index(page):
            listing.setdefault(row["number"][:4], []).append(row)
    previous = state.get("listing", {})
    for aid, base, number, cn, citation in cited:
        entries = listing.get(base, [])
        same = [e for e in entries if e["number"] == number]
        if not same:
            newer = [e for e in entries if e["number"] > number]
            if newer:
                e = max(newer, key=lambda e: e["number"])
                findings.append(finding("bop_policies", "replaced", f"BOP PS {number} appears replaced by {e['number']}",
                    f"The policy index lists {e['number']} {e['change_notice'] or ''} '{e['title']}' dated {e['date']} and no longer lists {number}, cited as {citation}.".replace("  ", " "),
                    e["url"], [aid]))
            else:
                findings.append(finding("bop_policies", "not_listed", f"BOP PS {number} is not in the policy index",
                    f"{citation} is not listed in the BOP policy index, and no other version of {base} is listed.", None, [aid]))
            continue
        for e in same:
            if cn and e["change_notice"] and e["change_notice"] != cn:
                findings.append(finding("bop_policies", "change_notice", f"BOP PS {number} has {e['change_notice']}",
                    f"Cited as {citation}; the index now lists {e['change_notice']} dated {e['date']}.", e["url"], [aid]))
            old = [p for p in previous.get(base, []) if p["number"] == e["number"] and p.get("change_notice") == e["change_notice"]]
            if old and old[0]["date"] != e["date"]:
                findings.append(finding("bop_policies", "reissued", f"BOP PS {number} date changed",
                    f"The index date for {e['number']} changed from {old[0]['date']} to {e['date']}.", e["url"], [aid]))
    return findings, {"listing": {b: listing.get(b, []) for b in sorted({c[1] for c in cited})}}


def watch_federal_register(authorities, state, get, today):
    parts = {}
    for a in authorities:
        if a["authority_type"] != "regulation":
            continue
        for m in CFR_PART.finditer(a["citation"]):
            parts.setdefault((m.group(1), m.group(2)), []).append(a["authority_id"])
    since = state.get("checked_through", DEFAULT_SINCE)
    seen = set(state.get("seen", []))
    findings = []
    for (title, part), aids in sorted(parts.items()):
        query = urlencode([("conditions[cfr][title]", title), ("conditions[cfr][part]", part),
                           ("conditions[publication_date][gte]", since), ("conditions[type][]", "RULE"),
                           ("conditions[type][]", "PRORULE"), ("per_page", "50"), ("order", "oldest")]
                          + [("fields[]", f) for f in ("document_number", "title", "type", "publication_date", "effective_on", "html_url", "citation")])
        page, _ = get("https://www.federalregister.gov/api/v1/documents.json?" + query)
        for doc in json.loads(page).get("results", []):
            if doc["document_number"] in seen:
                continue
            seen.add(doc["document_number"])
            when = f", effective {doc['effective_on']}" if doc.get("effective_on") else ""
            findings.append(finding("federal_register", doc["type"].lower().replace(" ", "_"),
                f"{doc['type']} affecting {title} C.F.R. part {part}: {doc['title']}",
                f"{doc.get('citation') or doc['document_number']}, published {doc['publication_date']}{when}. Compare it with the cited text.",
                doc["html_url"], aids))
    return findings, {"checked_through": today.isoformat(), "seen": sorted(seen)}


def watch_supreme_court(authorities, state, get, today):
    term = term_year(today)
    page, url = get(f"https://www.supremecourt.gov/opinions/slipopinion/{term % 100:02d}")
    seen = set(state.get("seen", []))
    findings = []
    for row in parse_scotus_term(page):
        key = f"{row['docket']}|{row['date']}"
        if key in seen:
            continue
        seen.add(key)
        criminal = "United States" in row["name"]
        findings.append(finding("supreme_court", "new_opinion", f"Supreme Court opinion: {row['name']} ({row['docket']})",
            f"Issued {row['date']}. Check whether it affects any module." + (" The United States is a party." if criminal else ""),
            row["url"], severity="review" if criminal else "info"))
    return findings, {"term": term, "seen": sorted(seen)}


def watch_rules(authorities, state, get, today):
    page, url = get("https://www.uscourts.gov/forms-rules/pending-rules-and-forms-amendments")
    links = sorted({urljoin(url, h) for h in PDF_LINK.findall(page)})
    known = set(state.get("documents", []))
    findings = []
    if known:
        for link in links:
            if link not in known:
                findings.append(finding("rules_amendments", "new_document", "New document on the pending rules amendments page",
                    "Review it for amendments to the Criminal, Appellate or Evidence Rules, or the § 2254/§ 2255 Rules.", link))
    dec1 = date(today.year, 12, 1)
    if dec1 - timedelta(days=60) <= today <= dec1:
        for a in authorities:
            if a["authority_type"] == "rule" and a["citation"].lower().startswith("proposed"):
                findings.append(finding("rules_amendments", "effective_date_near", f"Check whether {a['citation']} takes effect December 1, {today.year}",
                    "Rule amendments the Supreme Court transmits by May 1 take effect December 1 unless Congress acts. Confirm the adopted text and date, then update the claims that cite the proposal.",
                    url, [a["authority_id"]]))
    return findings, {"documents": links}


def watch_uscode(authorities, state, get, today):
    titles = {}
    for a in authorities:
        m = re.search(r"govinfo\.gov/link/uscode/(\d+)/", a.get("official_url") or "")
        if m:
            titles.setdefault(m.group(1), []).append(a)
    editions, findings = dict(state.get("editions", {})), []
    for title, auths in sorted(titles.items()):
        _, final = get(auths[0]["official_url"])
        m = GOVINFO_EDITION.search(final)
        if not m:
            findings.append(finding("uscode_edition", "edition_unknown", f"GovInfo edition of title {title} could not be read",
                f"{auths[0]['official_url']} led to {final}.", final, [a["authority_id"] for a in auths]))
            continue
        year = m.group(1)
        if editions.get(title) and editions[title] != year:
            findings.append(finding("uscode_edition", "new_edition", f"GovInfo now serves the {year} edition of title {title}",
                f"The links for {len(auths)} cited sections now open the {year} edition instead of {editions[title]}. Compare each cited section for amendments.",
                final, [a["authority_id"] for a in auths]))
        editions[title] = year
    return findings, {"editions": editions}


def watch_review_dates(modules, today):
    soon = today + timedelta(days=21)
    due = [m for m in modules if str(m.get("next_review_date", ""))[:10] <= soon.isoformat()]
    if not due:
        return []
    overdue = [m for m in due if str(m["next_review_date"])[:10] < today.isoformat()]
    first = min(str(m["next_review_date"])[:10] for m in due)
    return [finding("review_dates", "review_due", f"{len(due)} modules are due for legal review by {soon.isoformat()}",
        f"{len(overdue)} overdue; the earliest date is {first}. Due: " + ", ".join(sorted(m["module_id"] for m in due)) + ".",
        None, [m["module_id"] for m in due])]


def link_changes(previous: dict | None, current: dict | None):
    if not previous or not current:
        return []
    findings = []
    for sid, now in current["sources"].items():
        before = previous["sources"].get(sid)
        if before and before["result"] == "opened" and now["result"] == "failed":
            findings.append(finding("link_check", "newly_failing", f"Source no longer opens: {sid}",
                f"{now.get('reason', 'failed')}: {now.get('detail', '')}".strip(": "), now["url"], [sid]))
        elif before and before["result"] == "failed" and now["result"] == "opened":
            findings.append(finding("link_check", "recovered", f"Source opens again: {sid}", "", now["url"], [sid], "info"))
    return findings


WATCHERS = {"bop_policies": watch_bop, "federal_register": watch_federal_register,
            "supreme_court": watch_supreme_court, "rules_amendments": watch_rules, "uscode_edition": watch_uscode}


def run(authorities, modules, state, get, today, previous_link=None, current_link=None):
    findings, errors, new_state = [], [], {"schema_version": 1, "kind": "watch_state", "checked_on": today.isoformat(), "watchers": {}}
    for name, watcher in WATCHERS.items():
        old = state.get("watchers", {}).get(name, {})
        try:
            found, saved = watcher(authorities, old, get, today)
            findings += found
            new_state["watchers"][name] = saved
        except Exception as exc:  # one broken watcher must not stop the others
            errors.append({"watcher": name, "error": f"{type(exc).__name__}: {exc}"[:300]})
            new_state["watchers"][name] = old  # keep the last good state; retry next run
    findings += watch_review_dates(modules, today)
    findings += link_changes(previous_link, current_link)
    report = {"schema_version": 1, "kind": "watch_report", "checked_on": today.isoformat(),
              "legal_review_performed": False, "findings": findings, "errors": errors}
    return report, new_state


def markdown(report: dict, link_check: dict | None) -> str:
    out = [f"## Source and law-change review: {report['checked_on']}", "",
           "Automated, read-only checks. Nothing in the reference was changed. Each finding needs a person to decide whether a claim, an authority or a date should change.", ""]
    if link_check:
        c = link_check["counts"]
        out += [f"**Link check:** {c['opened']} of {c['opened'] + c['failed']} sources opened ({c['failed']} did not; sources confirmed by hand or through CourtListener still count as available on the site).", ""]
    review = [f for f in report["findings"] if f["severity"] == "review"]
    info = [f for f in report["findings"] if f["severity"] != "review"]
    for label, group in (("Needs review", review), ("For information", info)):
        out += [f"### {label} ({len(group)})", ""]
        if not group:
            out += ["None.", ""]
        for f in group:
            link = f" ([source]({f['url']}))" if f.get("url") else ""
            affects = f" Affects: {', '.join(f['affects'][:12])}{' …' if len(f['affects']) > 12 else ''}." if f["affects"] else ""
            out.append(f"- **{f['title']}**{link}. {f['detail']}{affects}".rstrip())
        out.append("")
    if report["errors"]:
        out += [f"### Watchers that could not run ({len(report['errors'])})", ""] + [f"- {e['watcher']}: {e['error']}" for e in report["errors"]] + [""]
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state", type=Path, default=ROOT / "maintenance/watch_state.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--previous-link-check", type=Path)
    parser.add_argument("--link-check", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        today = date.fromisoformat(args.today)
        authorities = [json.loads(l) for l in (ROOT / "data/authorities.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        modules = json.loads((ROOT / "data/modules.json").read_text(encoding="utf-8"))
        state = json.loads(args.state.read_text(encoding="utf-8")) if args.state.is_file() else {}
        load = lambda p: json.loads(p.read_text(encoding="utf-8")) if p and p.is_file() else None
        report, new_state = run(authorities, modules, state, lambda u: fetch(u, args.timeout), today,
                                load(args.previous_link_check), load(args.link_check))
    except (OSError, ValueError) as exc:
        print(f"Watch error: {exc}", file=sys.stderr)
        return 3
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in (("report.json", report), ("watch_state.json", new_state)):
        with (args.out / name).open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(content, indent=2, ensure_ascii=False) + "\n")
    with (args.out / "report.md").open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(markdown(report, load(args.link_check)))
    print(json.dumps({"findings": len(report["findings"]), "needs_review": sum(f["severity"] == "review" for f in report["findings"]),
                      "errors": len(report["errors"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
