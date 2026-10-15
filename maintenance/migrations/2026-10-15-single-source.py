"""One-time migration: make the data files the only home for record metadata.

Run once from the repository root. Kept in the repository so the change can be
audited and re-derived. Rules applied, in order:

Authority cards (authorities/**/AUTH-*.md)
  * The data record wins for every field, with two exceptions.
  * citation: when the card's citation is the data citation with the case or act
    name in front (for example "Brady v. Maryland, 373 U.S. 83 (1963)" against
    "373 U.S. 83 (1963)"), the fuller card citation is kept. The BOP Good Conduct
    Time FAQ keeps its fuller card title for the same reason.
  * last_verified: when card and data disagree, the earlier date is kept, so no
    record claims a later review than both sources support.
  * jurisdiction is normalized to the controlled list: "federal" becomes
    "federal_nationwide"; "third_circuit" and "ninth_circuit" gain the
    "federal_" prefix used by every other circuit value.
  * The card header is reduced to authority_id. The "Linked records" section is
    removed from the card body; the page lists linked modules from the data.

Module documents (docs/**/*.md)
  * Header fields that exist only in the header (module_type, jurisdiction,
    geographic_scope, procedural_stage, effective_through, related_modules, tags)
    move into data/modules.json unchanged.
  * For fields in both places the data record wins, except last_verified, where
    the earlier date is kept. Three index titles are shortened.
  * The header is reduced to module_id.

Links
  * authority.linked_claim_ids becomes exactly the claims whose authority_ids
    cite that authority; authority.linked_module_ids becomes exactly the modules
    whose authority_ids list it. Claim records are not changed.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import yaml

ROOT = Path.cwd()
HEADER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
JURISDICTION = {"federal": "federal_nationwide", "third_circuit": "federal_third_circuit",
                "ninth_circuit": "federal_ninth_circuit"}
TITLES = {"MOD-CHECKLISTS-INDEX": "Practical Checklists", "MOD-GLOSSARIES-INDEX": "Glossary",
          "MOD-DECISION-TREES-INDEX": "Decision Trees"}
FULLER_CITATION = {"AUTH-BOP-FSA-GCT-FAQ"}
MODULE_ONLY_FIELDS = ("module_type", "jurisdiction", "geographic_scope", "procedural_stage",
                      "effective_through", "related_modules", "tags")
log = []


def split(path: Path):
    text = path.read_text(encoding="utf-8")
    match = HEADER.match(text)
    if not match:
        raise ValueError(f"no header: {path}")
    return yaml.safe_load(match.group(1)) or {}, text[match.end():]


def earlier(a, b):
    return min(str(a), str(b))


def plain(value):
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value.isoformat() if hasattr(value, "isoformat") else value


def main() -> int:
    auth_path = ROOT / "data/authorities.jsonl"
    authorities = [json.loads(line) for line in auth_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_auth = {a["authority_id"]: a for a in authorities}
    modules = json.loads((ROOT / "data/modules.json").read_text(encoding="utf-8"))
    by_mod = {m["module_id"]: m for m in modules}
    claims = [json.loads(line) for line in (ROOT / "data/claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    for card in sorted((ROOT / "authorities").rglob("AUTH-*.md")):
        front, body = split(card)
        aid = front["authority_id"]
        a = by_auth[aid]
        cite = front.get("citation")
        if cite and cite != a["citation"] and (aid in FULLER_CITATION or (str(cite).endswith(", " + a["citation"]))):
            log.append(f"{aid} citation: {a['citation']!r} -> {cite!r}")
            a["citation"] = cite
        if "last_verified" in front and str(front["last_verified"]) != a["last_verified"]:
            new = earlier(front["last_verified"], a["last_verified"])
            if new != a["last_verified"]:
                log.append(f"{aid} last_verified: {a['last_verified']} -> {new}")
                a["last_verified"] = new
        body = re.sub(r"\n## Linked records\n.*?(?=\n## |\Z)", "\n", body, flags=re.S).rstrip() + "\n"
        card.write_text(f"---\nauthority_id: {aid}\n---\n" + body, encoding="utf-8")

    for a in authorities:
        if a["jurisdiction"] in JURISDICTION:
            a["jurisdiction"] = JURISDICTION[a["jurisdiction"]]

    for doc in sorted((ROOT / "docs").rglob("*.md")):
        front, body = split(doc)
        mid = front.get("module_id")
        if not mid:
            continue
        m = by_mod[mid]
        for key in MODULE_ONLY_FIELDS:
            if key in front:
                m[key] = plain(front[key])
        if "last_verified" in front and str(front["last_verified"]) != m["last_verified"]:
            new = earlier(front["last_verified"], m["last_verified"])
            if new != m["last_verified"]:
                log.append(f"{mid} last_verified: {m['last_verified']} -> {new}")
                m["last_verified"] = new
        if mid in TITLES and m["title"] != TITLES[mid]:
            log.append(f"{mid} title: {m['title']!r} -> {TITLES[mid]!r}")
            m["title"] = TITLES[mid]
        doc.write_text(f"---\nmodule_id: {mid}\n---\n" + body, encoding="utf-8")

    for m in modules:
        if m.get("jurisdiction") in JURISDICTION:
            m["jurisdiction"] = JURISDICTION[m["jurisdiction"]]

    cited_by = {aid: [] for aid in by_auth}
    for c in claims:
        for aid in c["authority_ids"]:
            cited_by[aid].append(c["claim_id"])
    listed_by = {aid: [] for aid in by_auth}
    for m in modules:
        for aid in m["authority_ids"]:
            listed_by[aid].append(m["module_id"])
    for a in authorities:
        for field, wanted in (("linked_claim_ids", cited_by[a["authority_id"]]), ("linked_module_ids", listed_by[a["authority_id"]])):
            if set(a[field]) != set(wanted):
                log.append(f"{a['authority_id']} {field}: +{sorted(set(wanted) - set(a[field]))} -{sorted(set(a[field]) - set(wanted))}")
            # Keep the existing order, then append newly derived links.
            a[field] = [x for x in a[field] if x in wanted] + [x for x in wanted if x not in a[field]]

    auth_path.write_text("".join(json.dumps(a, ensure_ascii=False, separators=(",", ":")) + "\n" for a in authorities), encoding="utf-8")
    (ROOT / "data/modules.json").write_text(json.dumps(modules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(log))
    print(f"{len(log)} recorded changes", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
