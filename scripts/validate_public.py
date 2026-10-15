"""Offline structural/publication checks. Passing does not verify current law."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET
import zipfile

from jsonschema import Draft202012Validator, FormatChecker
import yaml

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTENSIONS = {".md", ".html", ".css", ".js", ".json", ".jsonl", ".yaml", ".yml", ".svg", ".xml", ".drawio", ".txt", ".py", ".toml"}
PRIVATE_PARTS = {".git", ".venv", "__pycache__", "logs", "migration", ".review", ".env", "WORK_STATE.yaml", "coverage_matrix.yaml", "PRIVATE_SOURCE_ALIASES.json"}
MARKER = re.compile(r"<!--\s*claim:(CLM-[A-Z0-9-]+)\s+authorities:([^ ]+)\s+status:([^ ]+)\s*-->")
HEADER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LEAK_PATTERNS = {
    "company reference": re.compile(r"zip" + r"law", re.I),
    "private absolute path": re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/](?:Users|GitHub_Repos)[\\/]|/(?:Users|home)/|file://)", re.I),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9]{30,})\b"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return yaml.safe_load(text) if path.suffix in {".yaml", ".yml"} else json.loads(text)


def safe_relative(name):
    decoded = unquote(name)
    parts = PurePosixPath(decoded).parts
    return bool(name) and not decoded.startswith(("/", "\\")) and "\\" not in decoded and ":" not in decoded and not any(p in {"..", "."} for p in parts) and not any(p in PRIVATE_PARTS or p.startswith(("~$", ".")) or p.endswith(".ppwritelock") for p in parts)


def privacy_errors(name, data):
    errors = []
    if not safe_relative(name):
        errors.append(f"unsafe/private artifact path: {name}")
    if PurePosixPath(name).suffix in TEXT_EXTENSIONS:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return errors + [f"non-UTF-8 public text: {name}"]
        if "\ufffd" in text:
            errors.append(f"replacement character: {name}")
        for label, pattern in LEAK_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{label}: {name}")
    return errors


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.text, self.canonical = [], [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(values.get("href"))

    def handle_data(self, data):
        self.text.append(data)


def route_for_source(path):
    stem = path.removeprefix("docs/").removesuffix(".md")
    return "modules/" + (stem.removesuffix("index") if stem.endswith("/index") else stem + "/")


def link_target(page_path, link, base, origin):
    """Return output path/fragment, None for permitted external/host links."""
    parsed = urlsplit(link)
    if parsed.scheme in {"mailto", "tel"}:
        return None
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsafe link scheme: {link}")
    if parsed.netloc and parsed.netloc != urlsplit(origin).netloc:
        return None
    current_url = origin + base + page_path.removesuffix("index.html")
    resolved = urlsplit(urljoin(current_url, link))
    path = unquote(resolved.path)
    if path == "/legal/":
        return None
    if not path.startswith(base):
        raise ValueError(f"link escapes public base: {link}")
    relative = path[len(base):]
    if not relative or relative.endswith("/"):
        relative += "index.html"
    if not safe_relative(relative):
        raise ValueError(f"unsafe link path: {link}")
    return relative, unquote(resolved.fragment)


def validate(root=ROOT, site=None):
    root = Path(root)
    site = Path(site) if site else root / "dist/site"
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    def schema(value, spec, label):
        for err in Draft202012Validator(spec, format_checker=FormatChecker()).iter_errors(value):
            errors.append(f"schema {label} {list(err.path)}: {err.message}")
    def unique(records, key, label):
        ids = [r[key] for r in records]
        check(len(ids) == len(set(ids)), f"duplicate {label} IDs")
        return {r[key]: r for r in records}
    def refs(values, index, label):
        for value in values:
            check(value in index, f"unresolved {label}: {value}")

    cfg = load(root / "release.json")
    check(cfg["legal_reverification_performed_for_publication"] is False, "publication falsely claims legal reverification")
    base, origin = cfg["base_path"], cfg["site_origin"]
    datasets = {p.name: load(p) for p in (root / "data").iterdir() if p.suffix in {".json", ".jsonl", ".yaml", ".yml"}}
    index = {}
    for filename, key, schema_name in (("modules.json", "module_id", "module"), ("claims.jsonl", "claim_id", "claim"), ("authorities.jsonl", "authority_id", "authority"), ("process_nodes.json", "node_id", "node"), ("process_edges.json", "edge_id", "edge")):
        records = datasets[filename]
        schema(records, {"type": "array", "minItems": 1, "items": load(root / f"schemas/{schema_name}.schema.json")}, filename)
        index[schema_name] = unique(records, key, schema_name)
    sources = load(root / "sources/source_registry.yaml")["sources"]
    source_index = unique(sources, "source_id", "source")
    for source in sources:
        schema(source, {"type":"object", "required":["source_id", "title", "retrieval_date"], "properties":{"source_id":{"type":"string"}, "title":{"type":"string","minLength":1}}}, "source")
        url = source.get("official_url") or source.get("mirror_url")
        check(bool(url) and urlsplit(url).scheme in {"http", "https"} and bool(urlsplit(url).netloc), f"invalid source URL: {source['source_id']}")
        if source.get("authority_id"):
            refs([source["authority_id"]], index["authority"], "source authority")
        refs(source.get("additional_authority_ids", []), index["authority"], "source additional authority")
    for module in index["module"].values():
        path = root / module["path"]
        check(safe_relative(module["path"]) and path.is_file(), f"missing/unsafe module: {module['path']}")
        refs(module["claim_ids"], index["claim"], "module claim")
        refs(module["authority_ids"], index["authority"], "module authority")
        refs(module["sources_checked"], source_index, "module source")
        text = path.read_text(encoding="utf-8")
        marks = MARKER.findall(text)
        check(len(marks) == len({m[0] for m in marks}), f"duplicate claim marker in {module['path']}")
        check(set(module["claim_ids"]) == {m[0] for m in marks}, f"module claim-marker inventory mismatch: {module['module_id']}")
        for cid, auths, status in marks:
            refs([cid], index["claim"], "marker claim")
            if cid not in index["claim"]:
                continue
            c = index["claim"][cid]
            check(c["text"] in text, f"exact claim text absent: {cid}")
            check(c["module_id"] == module["module_id"] and c["document_path"] == module["path"], f"claim source routing mismatch: {cid}")
            check(set(auths.split(",")) == set(c["authority_ids"]) and status == c["verification_status"], f"claim marker qualification mismatch: {cid}")
    for c in index["claim"].values():
        refs([c["module_id"]], index["module"], "claim module")
        refs(c["authority_ids"] + c["conflicting_authority_ids"], index["authority"], "claim authority")
    for a in index["authority"].values():
        refs([a["source_id"]], source_index, "authority source")
        refs(a["linked_claim_ids"], index["claim"], "authority claim")
        refs(a["linked_module_ids"], index["module"], "authority module")
        cards = list((root / "authorities").rglob(a["authority_id"] + ".md"))
        check(len(cards) == 1, f"missing/duplicate authority card: {a['authority_id']}")
    # Single source of truth: headers carry only their ID; metadata lives in data/.
    for doc in sorted((root / "docs").rglob("*.md")):
        header = HEADER.match(doc.read_text(encoding="utf-8"))
        keys = set((yaml.safe_load(header.group(1)) or {}).keys()) if header else set()
        if "module_id" in keys:
            check(keys == {"module_id"}, f"module header must carry only module_id: {doc.relative_to(root).as_posix()}")
    for card in sorted((root / "authorities").rglob("AUTH-*.md")):
        header = HEADER.match(card.read_text(encoding="utf-8"))
        front = (yaml.safe_load(header.group(1)) or {}) if header else {}
        check(front == {"authority_id": card.stem}, f"authority card header must be only its authority_id: {card.relative_to(root).as_posix()}")
    # Links are stored both ways; both sides must agree exactly.
    cited_by, listed_by = defaultdict(set), defaultdict(set)
    for c in index["claim"].values():
        for aid in c["authority_ids"]:
            cited_by[aid].add(c["claim_id"])
    for m in index["module"].values():
        for aid in m["authority_ids"]:
            listed_by[aid].add(m["module_id"])
        cited = {aid for cid in m["claim_ids"] if cid in index["claim"] for aid in index["claim"][cid]["authority_ids"]}
        check(cited <= set(m["authority_ids"]), f"module omits authorities its claims cite: {m['module_id']}")
        refs(m.get("related_modules", []), index["module"], "related module")
    for aid, a in index["authority"].items():
        check(set(a["linked_claim_ids"]) == cited_by[aid], f"authority claim links not two-way: {aid}")
        check(set(a["linked_module_ids"]) == listed_by[aid], f"authority module links not two-way: {aid}")
    citations = [a["citation"] for a in index["authority"].values()]
    check(len(citations) == len(set(citations)), "duplicate authority citation")
    link_path = root / "data/link_check.json"
    if link_path.is_file():
        lc = load(link_path)
        schema(lc, {"type":"object","required":["schema_version","kind","checked_on","method","counts","authorities","sources"],"properties":{"kind":{"const":"link_check"},"checked_on":{"type":"string","format":"date"},"authorities":{"type":"object","additionalProperties":{"enum":["opened","failed"]}},"sources":{"type":"object","additionalProperties":{"type":"object","required":["url","result"],"properties":{"result":{"enum":["opened","failed"]}}}}}}, "link_check")
        refs(lc.get("authorities", {}), index["authority"], "link-check authority")
        refs(lc.get("sources", {}), source_index, "link-check source")
    conf_path = root / "data/source_confirmations.json"
    if conf_path.is_file():
        conf = load(conf_path)
        schema(conf, {"type":"object","required":["schema_version","kind","method","sources"],"properties":{"kind":{"const":"source_confirmations"},"sources":{"type":"object","additionalProperties":{"type":"object","required":["checked_on","result","url","citation","citation_match"],"properties":{"checked_on":{"type":"string","format":"date"},"result":{"enum":["confirmed","not_found"]},"method":{"enum":["courtlistener_api","browser"]},"citation_match":{"type":"boolean"}}}}}}, "source_confirmations")
        refs(conf.get("sources", {}), source_index, "confirmed source")
        for sid, c in conf.get("sources", {}).items():
            if sid in source_index:
                src = source_index[sid]
                check(c["url"] in (src.get("official_url"), src.get("mirror_url")), f"confirmed URL is not the recorded source URL: {sid}")
                check(c["result"] != "confirmed" or c["citation_match"], f"confirmation without a citation match: {sid}")
    for n in index["node"].values():
        refs([n["module_id"]], index["module"], "node module")
        refs(n.get("claim_ids", []), index["claim"], "node claim")
    for e in index["edge"].values():
        refs([e["from_node"], e["to_node"]], index["node"], "edge endpoint")
        refs(e.get("claim_ids", []), index["claim"], "edge claim")
    refs(datasets["nested_process.json"]["roots"], index["node"], "nested root")
    for filename, collection, idkey in (("deadlines.yaml","deadlines","deadline_id"),("jurisdiction_matrix.yaml","rules","rule_id"),("standards_of_review.yaml","standards","standard_id"),("remedies.yaml","remedies","remedy_id")):
        data = datasets[filename]
        schema(data, {"type":"object","required":["schema_version",collection],"properties":{collection:{"type":"array","minItems":1,"items":{"type":"object","required":[idkey,"authority_ids","claim_ids","last_verified"]}}}}, filename)
        unique(data[collection],idkey,collection)
        for record in data[collection]:
            refs(record["authority_ids"],index["authority"],filename+" authority")
            refs(record["claim_ids"],index["claim"],filename+" claim")
            if collection == "deadlines":
                for key in ("triggering_event","time_period","calendar_computation_rule","tolling_or_extensions","known_exceptions","legal_characterization"):
                    check(bool(record.get(key)), f"deadline missing {key}: {record[idkey]}")
    for filename, required in (("nested_process.json",["schema_version","roots"]),("circuit_splits.yaml",["schema_version","splits"]),("federal_districts.yaml",["schema_version","courts","counts"]),("district_rule_catalog.json",["schema_version","courts","document_count"]),("open_questions.json",["schema_version","items","counts"]),("coverage_summary.json",["schema_version","archive_coverage_counts","canonical_text_transformed"])):
        schema(datasets[filename], {"type":"object","required":required}, filename)
    string={"type":"string","minLength":1}
    string_list={"type":"array","items":string,"uniqueItems":True}
    schema(datasets["nested_process.json"]["roots"],string_list,"nested roots")
    split_schema={"type":"object","required":["issue_id","issue","supreme_court_or_nationwide_rule","circuit_rules"],"properties":{"issue_id":string,"issue":string,"supreme_court_or_nationwide_rule":string,"circuit_rules":{"type":"object","minProperties":1,"additionalProperties":{"type":"object","required":["status","rule","publication_status","last_checked"],"properties":{"status":string,"rule":string,"publication_status":string,"last_checked":{"type":"string","format":"date"}}}}}}
    unique(datasets["circuit_splits.yaml"]["splits"],"issue_id","circuit issue")
    for split in datasets["circuit_splits.yaml"]["splits"]:
        schema(split,split_schema,"circuit split")
    schema(datasets["coverage_summary.json"]["archive_coverage_counts"],{"type":"object","required":["total_items","not_verified"],"additionalProperties":{"type":"integer","minimum":0}},"coverage counts")
    check(datasets["coverage_summary.json"]["canonical_text_transformed"] is False,"coverage summary claims transformed legal text")
    questions = datasets["open_questions.json"]
    qindex = unique(questions["items"],"coverage_id","open question")
    categories = Counter(i["category"] for i in questions["items"])
    check(questions["counts"]["total"] == len(qindex), "open-question count mismatch")
    for category, count in categories.items():
        check(questions["counts"][category] == count, f"open-question category count mismatch: {category}")
    withheld = []
    for q in qindex.values():
        schema(q,{"type":"object","required":["coverage_id","description","status","responsible_module","disposition","dependency","last_updated","category"],"properties":{key:string for key in ("coverage_id","description","status","responsible_module","disposition","dependency","last_updated","category")}},"open question")
        check(q["status"] == "not_verified", f"unresolved issue promoted: {q['coverage_id']}")
        check(bool(q.get("dependency")), f"issue dependency missing: {q['coverage_id']}")
        check((root / q["responsible_module"]).is_file(), f"issue module missing: {q['coverage_id']}")
        if q.get("original_text_withheld"):
            withheld.append(q)
            check(q.get("legacy_claim_text") is None and bool(q.get("withholding_reason")) and bool(re.fullmatch(r"[0-9a-f]{64}",q.get("original_text_sha256",""))), f"invalid withheld-text disclosure: {q['coverage_id']}")
    receipt = load(root / "manifest/import_receipt.json")
    # Approved post-import edits chain from the receipt hash to the file's current hash.
    revisions = defaultdict(list)
    revisions_path = root / "manifest/revisions.json"
    if revisions_path.is_file():
        for rev in load(revisions_path)["revisions"]:
            schema(rev,{"type":"object","required":["path","previous_sha256","sha256","date","reason"],"properties":{"path":string,"previous_sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},"sha256":{"type":"string","pattern":"^[0-9a-f]{64}$"},"date":string,"reason":{"type":"string","minLength":10}}},"revision")
            revisions[rev["path"]].append(rev)
    for record in receipt["files"]:
        p = root / record["path"]
        receipt_safe=safe_relative(record["path"]) or (p.name==".gitkeep" and safe_relative(PurePosixPath(record["path"]).parent.as_posix()))
        check(receipt_safe and p.is_file(),f"receipt file missing/unsafe: {record['path']}")
        if p.is_file():
            expected = record["sha256"]
            for rev in revisions.get(record["path"], []):
                check(rev["previous_sha256"] == expected,f"revision chain broken: {record['path']}")
                expected = rev["sha256"]
            check(digest(p.read_bytes()) == expected,f"import preservation hash mismatch: {record['path']}")
        if record["path"] == "data/open_questions.json":
            check(record.get("withheld_original_texts") == len(withheld),"withholding receipt count mismatch")
    courts = datasets["federal_districts.yaml"]["courts"]
    catalog = datasets["district_rule_catalog.json"]
    cindex = unique(courts,"court_id","court")
    catalog_index = unique(catalog["courts"],"court_id","catalog court")
    check(set(cindex) == set(catalog_index),"district catalog court coverage mismatch")
    check(catalog["document_count"] == sum(len(c["documents"]) for c in catalog["courts"]),"district catalog document count mismatch")
    court_fields=("court_id","name","circuit_id","court_type","state_or_territory","official_homepage_url","rules_landing_url","rule_text_status","last_location_checked")
    for court in courts:
        schema(court,{"type":"object","required":list(court_fields),"properties":{key:string for key in court_fields}},"district court")
        check(court["rule_text_status"]=="not_verified",f"district semantic review silently promoted: {court['court_id']}")
    for court in catalog["courts"]:
        schema(court,{"type":"object","required":["court_id","documents","document_count"],"properties":{"documents":{"type":"array","items":{"type":"object","required":["url","title","kind","fetch_status"],"properties":{key:string for key in ("url","title","kind","fetch_status")}}}}},"catalog court")
        check(court["document_count"]==len(court["documents"]),f"catalog per-court document count: {court['court_id']}")
        for document in court["documents"]:
            parsed=urlsplit(document["url"])
            check(parsed.scheme in {"http","https"} and bool(parsed.netloc),f"invalid catalog URL: {court['court_id']}")
    order = load(root / "manifest/module_order.yaml")["modules"]
    check({m["module_id"] for m in order} == set(index["module"]) and len(order)==len(index["module"]),"master module order mismatch")

    manifest = load(site / "manifest.json")
    declared = unique(manifest["files"],"path","manifest path")
    actual = {p.relative_to(site).as_posix():p for p in site.rglob("*") if p.is_file()}
    check(set(actual) == set(declared) | {"manifest.json"},"manifest inventory: missing or unlisted output files")
    for p in site.rglob("*"):
        check(not p.is_symlink(),f"output symlink: {p.relative_to(site)}")
    for name, p in actual.items():
        errors.extend(privacy_errors(name,p.read_bytes()))
        if name in declared:
            check(declared[name]["sha256"] == digest(p.read_bytes()) and declared[name]["size"] == p.stat().st_size,f"manifest hash/size mismatch: {name}")
    # Independently reproduce the documented input digest, without importing builder code.
    roots=("docs","authorities","data","sources","manifest","schemas","diagrams","web","scripts","maintenance")
    inputs=[p for folder in roots for p in (root/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    inputs += [root/p for p in ("release.json","requirements.txt","PUBLICATION_POLICY.md","LICENSE_STATUS.md","LICENSE","LICENSE-CONTENT.md") if (root/p).exists()]
    for p in inputs:
        check(not p.is_symlink(),f"input symlink: {p.relative_to(root)}")
    expected_digest=digest("\n".join(p.relative_to(root).as_posix()+":"+digest(p.read_bytes()) for p in sorted(inputs)).encode())
    check(manifest["source_digest"] == expected_digest,"stale build: source_digest differs")
    check(manifest["legal_reverification_performed"] is False,"manifest falsely claims legal reverification")
    expected_counts={"modules":len(index["module"]),"claims":len(index["claim"]),"authorities":len(index["authority"]),"nodes":len(index["node"]),"edges":len(index["edge"]),"districts":len(courts),"catalog_sources":catalog["document_count"],"unresolved_items":len(qindex)}
    for key,count in expected_counts.items():
        check(manifest["counts"][key] == count,f"release count mismatch: {key}")
    pages={name:Page(p.read_text(encoding="utf-8")) for name,p in actual.items() if name.endswith(".html")}
    check(manifest["counts"]["pages"] == len(pages),"page count mismatch")
    for name,page in pages.items():
        check(len(page.ids)==len(set(page.ids)),f"duplicate HTML ID: {name}")
        check(page.canonical == [origin+base+name.removesuffix("index.html")],f"canonical URL mismatch: {name}")
        for link in page.links:
            try:
                target=link_target(name,link,base,origin)
                if target:
                    path,fragment=target
                    check(path in actual,f"broken link: {name} -> {link}")
                    if fragment and path in pages:
                        check(fragment in pages[path].ids,f"broken fragment: {name} -> {link}")
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
    for c in index["claim"].values():
        page=pages.get(route_for_source(c["document_path"])+"index.html")
        check(page is not None and "record-"+c["claim_id"] in page.ids,f"rendered claim record absent: {c['claim_id']}")
        if page:
            check(c["text"] in "".join(page.text),f"rendered exact claim absent: {c['claim_id']}")
            check(c["anchor"] in page.ids,f"canonical claim anchor absent: {c['claim_id']}")
    for module in index["module"].values():
        page=pages.get(route_for_source(module["path"])+"index.html")
        if page:
            plain="".join(page.text)
            shown = date.fromisoformat(module["last_verified"])
            check(f"Legal review {shown:%B} {shown.day}, {shown.year}" in plain,f"module legal review date absent: {module['module_id']}")
            source=(root/module["path"]).read_text(encoding="utf-8")
            if "coverage_matrix.yaml" in source:
                check("Archive reference note" in plain,f"private archive reference lacks explanation: {module['module_id']}")
    # Every module and authority page has a Markdown twin, and llms.txt lists only real pages.
    twins = {route_for_source(m["path"]).rstrip("/")+".md" for m in index["module"].values()}
    twins |= {"authorities/"+aid+".md" for aid in index["authority"]} | {"modules.md","authorities.md"}
    for twin in sorted(twins):
        check(twin in actual,f"Markdown twin missing: {twin}")
    check("llms.txt" in actual,"llms.txt missing")
    if "llms.txt" in actual:
        for url in re.findall(r"\]\(([^)\s]+)\)",actual["llms.txt"].read_text(encoding="utf-8")):
            rel = url[len(origin+base):].split("#")[0] if url.startswith(origin+base) else None
            check(rel is not None and (rel if not rel.endswith("/") else rel+"index.html") in actual,f"llms.txt link does not resolve: {url}")
    limits=pages.get("limitations/index.html")
    check(limits is not None and set(qindex).issubset(limits.ids),"rendered uncertainty inventory incomplete")
    search=load(site/"assets/search-index.json")
    expected_search={base+route_for_source(p.relative_to(root).as_posix()) for p in (root/"docs").rglob("*.md")}
    expected_search |= {base+"authorities/"+aid+"/" for aid in index["authority"]}
    expected_search |= {base+"districts/"+cid.lower()+"/" for cid in cindex}
    check(len(search)==len({r["url"] for r in search}) and {r["url"] for r in search}==expected_search,"search coverage/duplicates mismatch")
    sitemap=ET.fromstring((site/"sitemap.xml").read_text(encoding="utf-8"))
    urls=[n.text for n in sitemap.findall("{*}url/{*}loc")]
    unlisted = {"downloads/index.html"} if load(root / "release.json").get("downloads_visibility") == "unlisted" else set()
    check(len(urls)==len(set(urls)) and set(urls)=={origin+base+n.removesuffix("index.html") for n in pages if n not in unlisted},"sitemap coverage or URLs mismatch")
    with zipfile.ZipFile(site/"downloads/reference-data.zip") as archive:
        names=archive.namelist()
        check(len(names)==len(set(names)),"ZIP duplicate entries")
        expected_zip={p.relative_to(root).as_posix() for folder in ("docs","authorities","data","sources","schemas","manifest","diagrams") for p in (root/folder).rglob("*") if p.is_file() and p.name!=".gitkeep"}
        expected_zip |= {"PUBLICATION_POLICY.md","LICENSE_STATUS.md","LICENSE","LICENSE-CONTENT.md","release.json"}
        check(set(names)==expected_zip,"ZIP content scope mismatch")
        for entry in archive.infolist():
            errors.extend(privacy_errors(entry.filename,archive.read(entry)))
            check((entry.external_attr>>16)&0o170000 != 0o120000,f"ZIP symlink: {entry.filename}")
            if entry.filename in expected_zip:
                check(archive.read(entry)==(root/entry.filename).read_bytes(),f"ZIP source mismatch: {entry.filename}")
    return errors, expected_counts


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--site",type=Path)
    args=parser.parse_args()
    try:
        failures, counts=validate(site=args.site)
        print(json.dumps({"status":"failed" if failures else "passed_structural_not_legal_verification","counts":counts,"errors":failures},indent=2))
        raise SystemExit(bool(failures))
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,ET.ParseError) as exc:
        print(json.dumps({"status":"failed","errors":[f"validation could not complete: {exc}"]}))
        raise SystemExit(1)
