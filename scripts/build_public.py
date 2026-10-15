"""Build a deterministic, portable static reference from canonical public sources."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
from urllib.parse import quote, unquote, urlsplit
import zipfile

import markdown
import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "00-system-overview": "Start here", "10-investigation-and-charging": "Investigation & charging",
    "20-pretrial": "Pretrial", "30-plea-and-trial": "Plea & trial", "40-sentencing": "Sentencing",
    "50-direct-review": "Direct review", "60-post-conviction": "Post-conviction",
    "70-sentence-modification": "Sentence modification", "80-sentence-execution-and-bop": "Prison & sentence execution",
    "90-supervised-release-and-reentry": "Supervision & reentry", "95-circuit-overlays": "Circuit overlays",
    "96-district-courts": "District courts", "checklists": "Checklists", "decision-trees": "Decision trees",
    "glossaries": "Glossary", "examples": "Worked examples",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def frontmatter(text):
    if text.startswith("---\n"):
        _, front, body = text.split("---\n", 2)
        return yaml.safe_load(front) or {}, body
    return {}, text


def sha(data):
    return hashlib.sha256(data).hexdigest()


def human_date(value):
    """2026-08-26 -> August 26, 2026; anything else is returned unchanged."""
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    return f"{d:%B} {d.day}, {d.year}"


def md_route(route):
    """Markdown twin of a page route: modules/40-sentencing/ -> modules/40-sentencing.md."""
    return route.rstrip("/") + ".md"


def public_inputs():
    roots = ("docs", "authorities", "data", "sources", "manifest", "schemas", "diagrams", "web", "scripts", "maintenance")
    paths = [p for folder in roots for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT / p for p in ("release.json", "requirements.txt", "PUBLICATION_POLICY.md", "LICENSE_STATUS.md", "LICENSE", "LICENSE-CONTENT.md") if (ROOT / p).exists()]
    return sorted(paths)


def input_digest():
    return sha("\n".join(p.relative_to(ROOT).as_posix() + ":" + sha(p.read_bytes()) for p in public_inputs()).encode())


class Rewriter(HTMLParser):
    """Translate actual rendered links, not regex fragments of Markdown syntax."""
    def __init__(self, source, resolve):
        super().__init__(convert_charrefs=False)
        self.source, self.resolve, self.out = source, resolve, []

    def handle_starttag(self, tag, attrs):
        new = []
        for key, value in attrs:
            if key in {"href", "src"} and value:
                value = self.resolve(self.source, value)
            new.append(key if value is None else f'{key}="{escape(value, quote=True)}"')
        self.out.append("<" + tag + (" " + " ".join(new) if new else "") + ">")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag): self.out.append(f"</{tag}>")
    def handle_data(self, data): self.out.append(data)
    def handle_entityref(self, name): self.out.append(f"&{name};")
    def handle_charref(self, name): self.out.append(f"&#{name};")
    def handle_comment(self, data): pass


class Builder:
    def __init__(self, as_of):
        self.as_of = date.fromisoformat(as_of)
        self.cfg = read_json(ROOT / "release.json")
        self.base = self.cfg["base_path"]
        if not re.fullmatch(r"/(?:[a-z0-9-]+/)+", self.base):
            raise ValueError("Unsafe base_path")
        self.out = ROOT / "dist/site"
        self.digest = input_digest()
        self.modules = read_json(ROOT / "data/modules.json")
        self.by_module = {m["module_id"]: m for m in self.modules}
        self.claims = read_jsonl(ROOT / "data/claims.jsonl")
        self.by_claim = {c["claim_id"]: c for c in self.claims}
        self.authorities = read_jsonl(ROOT / "data/authorities.jsonl")
        self.by_auth = {a["authority_id"]: a for a in self.authorities}
        self.questions = read_json(ROOT / "data/open_questions.json")
        self.districts = yaml.safe_load((ROOT / "data/federal_districts.yaml").read_text(encoding="utf-8"))["courts"]
        self.catalog = read_json(ROOT / "data/district_rule_catalog.json")
        self.sources = yaml.safe_load((ROOT / "sources/source_registry.yaml").read_text(encoding="utf-8"))["sources"]
        self.nodes = read_json(ROOT / "data/process_nodes.json")
        self.edges = read_json(ROOT / "data/process_edges.json")
        # Optional: written from a full source-review run. Absent means no link check is shown.
        link_path = ROOT / "data/link_check.json"
        self.link_check = read_json(link_path) if link_path.is_file() else None
        self.route_map, self.auth_paths, self.search = {}, {}, []
        self.pages = []
        self.unlisted_routes = {"downloads/"} if self.cfg.get("downloads_visibility") == "unlisted" else set()
        for p in sorted((ROOT / "docs").rglob("*.md")):
            rel = p.relative_to(ROOT).as_posix()
            path = rel.removeprefix("docs/").removesuffix(".md")
            self.route_map[rel] = "modules/" + (path.removesuffix("index") if path.endswith("/index") else path + "/")
        for p in sorted((ROOT / "authorities").rglob("AUTH-*.md")):
            rel = p.relative_to(ROOT).as_posix()
            self.route_map[rel] = "authorities/" + p.stem + "/"
            self.auth_paths[p.stem] = rel
        # Every module and authority page also has a Markdown twin at the same URL plus ".md".
        self.md_routes = {md_route(r) for r in self.route_map.values()} | {"modules.md", "authorities.md"}

    def url(self, route=""):
        return self.base + route

    def anchor(self, route, text, cls=""):
        return f'<a class="{cls}" href="{escape(self.url(route))}">{escape(str(text))}</a>'

    def resolve(self, source, href):
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or href.startswith(("#", "/")):
            return href
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))
        if target in self.route_map:
            return self.url(self.route_map[target]) + ("#" + parsed.fragment if parsed.fragment else "")
        if target.startswith(("data/", "sources/", "diagrams/")) and (ROOT / target).is_file():
            return self.url("downloads/" + target) + ("#" + parsed.fragment if parsed.fragment else "")
        # Original archive references remain identifiable, with a public explanatory destination.
        if target in {"data/coverage_matrix.yaml", "updates/not_verified_register.md", "updates/not_verified_register.json"}:
            return self.url("limitations/")
        return href

    def write(self, route, content):
        path = self.out / route
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def page(self, route, title, content, section="Reference", toc=""):
        nav = [("", "Overview"), ("process/", "Process explorer"), ("modules/", "All modules"), ("districts/", "Courts & rules"), ("authorities/", "Authorities"), ("sources/", "Source registry"), ("limitations/", "Scope & methodology"), ("downloads/", "Downloads"), ("about/", "About & license")]
        links = "".join(self.anchor(r, label, "active" if r == route else "") for r, label in nav if r not in self.unlisted_routes)
        current_stage = next((slug for slug in STAGES if route.startswith("modules/" + slug + "/")), None)
        stage_links = "".join(self.anchor("modules/" + slug + "/", label, "active" if slug == current_stage else "") for slug, label in STAGES.items() if "docs/" + slug + "/index.md" in self.route_map)
        stage_open = " open" if current_stage else ""
        alternate = f'<link rel="alternate" type="text/markdown" href="{escape(self.url(md_route(route)))}">' if md_route(route) in self.md_routes else ""
        md_link = f'<a class="md-link" href="{escape(self.url(md_route(route)))}" type="text/markdown">View as Markdown</a>' if md_route(route) in self.md_routes else ""
        current = human_date(self.cfg["research_baseline"])
        body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · Federal Judicial Process</title><meta name="description" content="A source-linked guide to the federal criminal process: each stage, its time limits, the courts, and the authority behind every rule."><link rel="canonical" href="{escape(self.cfg['site_origin'] + self.url(route))}"><link rel="stylesheet" href="{self.url('assets/site.css')}"><script defer src="{self.url('assets/site.js')}"></script>{alternate}</head><body data-base="{self.base}"><a class="skip" href="#main">Skip to content</a><header class="topbar"><a class="brand" href="/legal/">JASON93 <span>/ LEGAL TECH</span></a><a class="search-link" href="{self.url('search/')}">Search the reference <span aria-hidden="true">↗</span></a></header><div class="shell"><aside class="sidebar"><a class="site-title" href="{self.url()}">Federal <br>Judicial Process<span>PRACTICE REFERENCE</span></a><nav aria-label="Reference navigation">{links}</nav><details class="stage-nav"{stage_open}><summary>Browse by stage</summary><nav aria-label="Process stages">{stage_links}</nav></details></aside><main id="main" tabindex="-1"><div class="page-meta"><span>{escape(section)}</span><span>Current through {current}</span>{md_link}</div>{content}<footer><p>General legal information, not legal advice. Not affiliated with any court or government agency. Current through {current}.</p><p>{self.anchor('limitations/', 'Scope & methodology')} · {self.anchor('about/', 'About & license')} · <a href="{self.cfg['repository_url']}">Source on GitHub</a></p><p class="quiet">By {escape(self.cfg['owner_display_name'])} · Release {self.digest[:12]}</p></footer></main>{f'<aside class="toc" aria-label="On this page">{toc}</aside>' if toc else ''}</div></body></html>'''
        if route in self.unlisted_routes:
            body = body.replace('</head>', '<meta name="robots" content="noindex, nofollow"></head>', 1)
        self.write((route + "index.html") if not route.endswith(".html") else route, body)
        self.pages.append(route)

    def render(self, source, text, claims=False):
        _, body = frontmatter(text)
        if claims:
            def badge(match):
                cid = match.group(1)
                return f'<div class="claim-marker"><a href="#record-{cid}">{cid} · claim record</a></div>'
            body = re.sub(r"<!--\s*claim:([A-Z0-9-]+).*?-->", badge, body)
        md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"], extension_configs={"toc": {"permalink": False}})
        html = md.convert(body)
        if claims:
            present_ids = set(re.findall(r'\bid="([^"]+)"',html))
            for claim in self.claims:
                if claim['document_path'] != source or claim['anchor'] in present_ids:
                    continue
                anchor = claim['anchor']
                marker = '<div class="claim-marker"><a href="#record-' + claim['claim_id'] + '">'
                if marker not in html:
                    raise ValueError('Claim anchor cannot be placed at exact claim: ' + claim['claim_id'])
                html = html.replace(marker,'<span class="anchor-alias" id="'+escape(anchor,quote=True)+'"></span>'+marker,1)
                present_ids.add(anchor)
        rewrite = Rewriter(source, self.resolve)
        rewrite.feed(html)
        return "".join(rewrite.out), md.toc

    MD_LINK = re.compile(r'(\]\()([^)\s]+)((?:\s+"[^"]*")?\))')

    def abs_url(self, route):
        return self.cfg["site_origin"] + self.url(route)

    def md_resolve(self, source, href):
        """Point a relative Markdown link at the Markdown twin of its target page."""
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or href.startswith(("#", "/")):
            return href
        target = posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))
        frag = "#" + parsed.fragment if parsed.fragment else ""
        if target in self.route_map:
            return self.abs_url(md_route(self.route_map[target])) + frag
        resolved = self.resolve(source, href)
        return self.cfg["site_origin"] + resolved if resolved.startswith("/") else resolved

    def write_md(self, route, fields, body):
        header = "---\n" + "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in fields.items() if v not in (None, "", [])) + "---\n\n"
        self.write(md_route(route), header + body.strip() + "\n")

    @staticmethod
    def cite(a):
        """Case citations read better with the case name: Preiser v. Rodriguez, 411 U.S. 475 (1973)."""
        return f"{a['title']}, {a['citation']}" if a["authority_type"] == "case" and a["title"] not in a["citation"] else a["citation"]

    def markdown_twins(self):
        """Machine-readable twins of every module and authority page, plus llms.txt."""
        current = self.cfg["research_baseline"]
        for source, route in self.route_map.items():
            front, body = frontmatter((ROOT / source).read_text(encoding="utf-8"))
            body = self.MD_LINK.sub(lambda m: m.group(1) + self.md_resolve(source, m.group(2)) + m.group(3), body)
            if source.startswith("docs/"):
                meta = self.by_module.get(front.get("module_id"), {})
                auths = [self.by_auth[a] for a in meta.get("authority_ids", []) if a in self.by_auth]
                if auths:
                    body += "\n\n## Authorities\n\n" + "".join(f"- [{self.cite(a)}]({self.abs_url(md_route('authorities/' + a['authority_id'] + '/'))})" + (f" · official source: {a['official_url']}" if a.get("official_url") else "") + "\n" for a in auths)
                self.write_md(route, {"title": meta.get("title"), "module_id": front.get("module_id"), "url": self.abs_url(route), "current_through": current, "legal_review": str(meta.get("last_verified", "")), **self.link_fields(meta.get("authority_ids", [])), "license": "CC BY 4.0"}, body)
            else:
                a = self.by_auth[PurePosixPath(source).stem]
                used = [self.by_module[m] for m in a["linked_module_ids"] if m in self.by_module]
                if used:
                    body += "\n\n## Used in\n\n" + "".join(f"- [{m['title']}]({self.abs_url(md_route(self.route_map[m['path']]))})\n" for m in used)
                self.write_md(route, {"title": a["title"], "citation": a["citation"], "authority_id": a["authority_id"], "authority_type": a["authority_type"], "jurisdiction": a.get("jurisdiction"), "precedential_status": a.get("precedential_status"), "official_url": a.get("official_url"), "url": self.abs_url(route), "legal_review": a.get("last_verified"), **self.link_fields([a["authority_id"]]), "license": "CC BY 4.0"}, body)
        groups = defaultdict(list)
        for m in self.modules: groups[PurePosixPath(m["path"]).parts[1]].append(m)
        def module_line(m): return f"- [{m['title']}]({self.abs_url(md_route(self.route_map[m['path']]))})\n"
        modules_md = "# All modules\n\n" + "".join(f"## {label}\n\n" + "".join(module_line(m) for m in groups[slug]) + "\n" for slug, label in STAGES.items() if groups[slug])
        self.write_md("modules/", {"title": "All modules", "url": self.abs_url("modules/"), "current_through": current}, modules_md)
        authorities_md = "# Authorities\n\n" + "".join(f"- [{self.cite(a)}]({self.abs_url(md_route('authorities/' + a['authority_id'] + '/'))})" + ("" if a["authority_type"] == "case" else f": {a['title']}") + "\n" for a in sorted(self.authorities, key=lambda a: a["citation"]))
        self.write_md("authorities/", {"title": "Authorities", "url": self.abs_url("authorities/"), "current_through": current}, authorities_md)
        overview = next(m for m in self.modules if m["path"] == "docs/00-system-overview/index.md")
        llms = [f"# {self.cfg['title']}", "",
                f"> A source-linked guide to the U.S. federal criminal process, from investigation and charging through trial, sentencing, appeal, post-conviction remedies, custody and supervised release. Current through {human_date(current)}. General legal information, not legal advice. Content licensed CC BY 4.0.", "",
                "Every page listed here is Markdown. Each module states the law as separate claims; a claim is marked in the text with an HTML comment such as `<!-- claim:CLM-2255-001 authorities:AUTH-USC-28-2255 status:verified_current -->`, and the module ends with links to its authorities. Each authority page gives the citation, weight and official source. Start with the overview, pick the stage that matches the case, and cite the authority behind each step. Report the `legal_review` date with any answer. `links_checked` only records that the sources still opened on that date; it is not a legal review.", "",
                "## Start here", "",
                module_line(overview).rstrip("\n") + ": what the reference covers and what to know before using it",
                f"- [All modules]({self.abs_url('modules.md')}): every topic, grouped by stage",
                f"- [Authorities]({self.abs_url('authorities.md')}): every statute, rule and decision cited", ""]
        for slug, label in STAGES.items():
            if slug == "00-system-overview" or not groups[slug]: continue
            llms += [f"## {label}", ""] + [module_line(m).rstrip("\n") for m in groups[slug]] + [""]
        llms += ["## Optional", "", f"- [Process graph]({self.abs_url('assets/process-index.json')}): steps and the conditions connecting them, as JSON", f"- [Scope & methodology]({self.abs_url('limitations/')}): coverage, sourcing, currency and open research questions", ""]
        self.write("llms.txt", "\n".join(llms))

    def module_link(self, mid):
        m = self.by_module[mid]
        return self.anchor(self.route_map[m["path"]], m["title"])

    def authority_link(self, aid):
        a = self.by_auth[aid]
        return self.anchor("authorities/" + aid + "/", a["citation"])

    def link_status(self, authority_ids):
        """(opened, checked) counts for these authorities in the link-check record."""
        if not self.link_check:
            return None
        results = [self.link_check["authorities"][a] for a in authority_ids if a in self.link_check["authorities"]]
        return sum(r == "opened" for r in results), len(results)

    def dates_line(self, legal_review, authority_ids, single=False):
        """Two dates, each true on its own: the legal review and the automated link check."""
        line = f'Legal review <time datetime="{escape(str(legal_review))}">{human_date(legal_review)}</time>'
        status = self.link_status(authority_ids)
        if status and status[1]:
            opened, checked = status
            when = self.link_check["checked_on"]
            if single:
                result = "the source opened" if opened else "the source could not be reached"
            else:
                result = f"all {checked} sources opened" if opened == checked else f"{opened} of {checked} sources opened"
            line += f' · Links checked <time datetime="{escape(when)}">{human_date(when)}</time>: {result}'
        return line

    def link_fields(self, authority_ids):
        status = self.link_status(authority_ids)
        if not status or not status[1]:
            return {}
        return {"links_checked": self.link_check["checked_on"], "links_opened": status[0], "links_checked_count": status[1]}

    def record_fields(self, fields):
        return '<dl class="record">' + "".join(f'<dt>{escape(k.replace("_", " "))}</dt><dd>{escape(str(v))}</dd>' for k, v in fields.items() if v is not None) + '</dl>'

    def module_pages(self):
        claims_by_module = defaultdict(list)
        for c in self.claims: claims_by_module[c["module_id"]].append(c)
        for source, route in list(self.route_map.items()):
            if not source.startswith("docs/"): continue
            text = (ROOT / source).read_text(encoding="utf-8")
            front, body = frontmatter(text)
            meta = self.by_module.get(front.get("module_id"), {})
            title = meta.get("title") or re.search(r"^# (.+)", body, re.M).group(1)
            rendered, toc = self.render(source, text, claims=True)
            verified = str(meta.get("last_verified", self.cfg["research_baseline"]))
            due = str(meta.get("next_review_date", "Not individually scheduled"))
            overdue = due[:4].isdigit() and date.fromisoformat(due[:10]) < self.as_of
            notice = f'<p class="currency">{self.dates_line(verified, meta.get("authority_ids", []))} · {self.anchor("limitations/", "Scope & methodology")}</p>'
            if overdue:
                notice += '<p class="currency due">This topic is due for review. Confirm the current rule before relying on it.</p>'
            if "coverage_matrix.yaml" in body or "not_started" in body:
                notice += '<p class="currency">Archive reference note: parts of this topic refer to earlier research records, now listed under ' + self.anchor("limitations/", "open research questions") + '.</p>'
            records = '<section class="claim-records"><h2 id="claim-records">Claim-level source records</h2>'
            for c in claims_by_module[front.get("module_id")]:
                records += f'<details id="record-{c["claim_id"]}"><summary>{escape(c["claim_id"])} · {escape(c["verification_status"])}</summary><p>{escape(c["text"])}</p>{self.record_fields({k:c.get(k) for k in ("jurisdiction", "procedural_posture", "classification", "last_verified", "known_limitations", "researcher_notes")})}<p>Authorities: ' + "; ".join(self.authority_link(aid) for aid in c["authority_ids"]) + '</p></details>'
            records += '</section>'
            authorities = meta.get("authority_ids", [])
            if authorities: records += '<section><h2>Linked authorities</h2><ul>' + ''.join('<li>' + self.authority_link(a) + '</li>' for a in authorities if a in self.by_auth) + '</ul></section>'
            self.page(route, title, notice + '<article class="prose">' + rendered + '</article>' + records, "Module", toc)
            self.search.append({"title": title, "url": self.url(route), "kind": "Module", "text": re.sub(r"<[^>]*>", " ", rendered), "status": meta.get("status", "catalog"), "last_verified": verified})

    def authority_pages(self):
        for a in self.authorities:
            aid = a["authority_id"]
            source = self.auth_paths[aid]
            body, toc = self.render(source, (ROOT / source).read_text(encoding="utf-8"))
            record = '<p class="currency">' + self.dates_line(a["last_verified"], [aid], single=True) + ' · ' + self.anchor("limitations/", "Scope & methodology") + '</p>'
            record += '<p class="currency">This record is not a citator check. Confirm later history and treatment before relying on it.</p>'
            record += self.record_fields({k:a.get(k) for k in ("authority_type", "jurisdiction", "publication_status", "precedential_status", "decision_or_issuance_date", "subsequent_history", "negative_treatment_status", "material_limitations")})
            source_url = a.get("official_url") or a.get("mirror_url")
            if source_url:
                source_label = "Open official source" if a.get("official_url") else "Open recorded mirror (not the official host)"
                record += '<p><a rel="noopener" href="' + escape(source_url, quote=True) + '">' + source_label + ' ↗</a></p>'
            else:
                record += '<p class="notice">No accessible source URL is recorded. This source requires review.</p>'
            record += '<h2>Linked modules</h2><ul>' + ''.join('<li>' + self.module_link(m) + '</li>' for m in a["linked_module_ids"] if m in self.by_module) + '</ul>'
            self.page("authorities/" + aid + "/", a["citation"], record + '<article class="prose">' + body + '</article>', "Authority", toc)
            self.search.append({"title": a["citation"], "url": self.url("authorities/" + aid + "/"), "kind": "Authority", "text": a["title"] + " " + " ".join(a["citeable_propositions"]), "status": a["verification_status"], "last_verified": a["last_verified"]})
        rows = ''.join(f'<li data-filter-text="{escape((a["citation"] + " " + a["title"] + " " + a["authority_type"]).lower(), quote=True)}">{self.authority_link(a["authority_id"])}<span>{escape(a["authority_type"])} · {escape(a["last_verified"])}</span></li>' for a in sorted(self.authorities, key=lambda a:a["citation"]))
        self.page("authorities/", "Authority library", f'<h1>Follow the authority.</h1><p class="lede">{len(self.authorities)} structured authority records. Binding status, jurisdiction, source links, and treatment limits stay attached.</p><label for="library-filter">Filter authorities</label><input id="library-filter" data-filter="authority-list" type="search" placeholder="Citation, title, or type"><p data-filter-count="authority-list" aria-live="polite"></p><ul id="authority-list" class="directory">{rows}</ul>')

    def home(self):
        stats = [(len(self.modules), "modules"), (len(self.claims), "source-linked claims"), (len(self.authorities), "authority records"), (len(self.districts), "district-level courts")]
        cards = [("process/", "01 / FIND THE ROUTE", "Explore the process", "Move through each procedural stage and the conditions that lead from one step to the next."), ("districts/", "02 / FIND THE COURT", "Courts & local rules", "All 94 district-level courts, each linked to its official local rules and standing orders."), ("authorities/", "03 / CHECK THE SOURCE", "Read the authority", "Open the source, see its jurisdiction and weight, and follow the claims that depend on it."), ("limitations/", "04 / HOW IT WORKS", "Scope & methodology", "What the reference covers, how each statement is tied to its source, and how it is kept current.")]
        content = '<section class="hero"><p class="eyebrow">FEDERAL CRIMINAL PROCESS</p><h1>Understand the route.<br><em>Check the source.</em></h1><p class="lede">A source-linked guide to the federal criminal process, from investigation through appeal, custody and reentry. Every statement links to the statute, rule or decision behind it.</p><div class="actions">' + self.anchor('process/', 'Explore the process →', 'button') + self.anchor('modules/', 'Browse the reference', 'button secondary') + '</div></section>'
        content += '<div class="stats">' + ''.join(f'<div><strong>{n:,}</strong><span>{label}</span></div>' for n,label in stats) + '</div>'
        content += '<p class="currency">Current through ' + human_date(self.cfg['research_baseline']) + '. General legal information, not legal advice. ' + self.anchor('limitations/', 'Scope & methodology') + '</p>'
        content += '<section class="cards">' + ''.join(f'<a class="card" href="{self.url(r)}"><span class="eyebrow">{k}</span><h2>{title}</h2><p>{desc}</p><span class="card-arrow" aria-hidden="true">↗</span></a>' for r,k,title,desc in cards) + '</section>'
        content += '<section><h2>Follow the stages</h2><div class="stage-strip">' + ''.join(self.anchor('modules/' + slug + '/', label) for slug,label in STAGES.items() if slug[0].isdigit() and slug not in {'00-system-overview','95-circuit-overlays','96-district-courts'}) + '</div></section>'
        self.page('', self.cfg['title'], content, 'Practice reference')
        groups = defaultdict(list)
        for m in self.modules: groups[PurePosixPath(m['path']).parts[1]].append(m)
        body = '<h1>The complete reference.</h1><p class="lede">Browse by stage, then check the jurisdiction and verification boundary within each module.</p>'
        for slug,label in STAGES.items():
            body += f'<section><h2>{label}</h2><ul class="directory">' + ''.join('<li>' + self.module_link(m['module_id']) + '<span>' + escape(m['last_verified']) + '</span></li>' for m in groups[slug]) + '</ul></section>'
        self.page('modules/', 'All modules', body)

    def district_pages(self):
        catalogs = {c['court_id']:c for c in self.catalog['courts']}
        rows = []
        for c in sorted(self.districts, key=lambda c:(c['state_or_territory'],c['name'])):
            route = 'districts/' + c['court_id'].lower() + '/'
            docs = catalogs[c['court_id']]['documents']
            content = f'<p class="eyebrow">{escape(c["circuit_id"])} / {escape(c["state_or_territory"])}</p><h1>{escape(c["name"])}</h1><div class="notice"><strong>Rule text: not verified.</strong><p>The official location was recorded on {c["last_location_checked"]}. The catalog is a discovery aid; check current rule text, amendments, standing orders, and judge-specific requirements before use.</p></div><p><a href="{escape(c["official_homepage_url"],quote=True)}">Official court website ↗</a> · <a href="{escape(c["rules_landing_url"],quote=True)}">Official rules location ↗</a></p><h2>{len(docs)} cataloged sources</h2><ul class="directory">'
            for d in docs:
                content += f'<li><a href="{escape(d["url"], quote=True)}">{escape(d["title"])}</a><span>{escape(d["kind"].replace("_", " "))} · recorded technical fetch: {escape(d["fetch_status"])}</span></li>'
            self.page(route, c['name'], content + '</ul>', 'Court source directory')
            rows.append(f'<li data-filter-text="{escape((c["name"] + " " + c["state_or_territory"] + " " + c["circuit_id"]).lower(),quote=True)}">{self.anchor(route,c["name"])}<span>{c["state_or_territory"]} · {c["circuit_id"]} · {len(docs)} sources · rule text not verified</span></li>')
            self.search.append({'title':c['name'],'url':self.url(route),'kind':'Court','text':c['state_or_territory'] + ' ' + c['circuit_id'],'status':'rule text not verified','last_verified':c['last_location_checked']})
        content = f'<h1>Find the court.<br><em>Then check its rules.</em></h1><p class="lede">All {len(self.districts)} district-level courts: 91 Article III districts and three territorial courts. {self.catalog["document_count"]:,} cataloged rule, order, and filing-procedure sources.</p><div class="notice"><strong>A source map, not a geographic boundary map.</strong><p>All 94 local-rule text reviews remain unresolved. This directory does not determine venue or jurisdiction and does not guarantee discovery of every amendment or judge-specific order. Catalog baseline: {self.cfg["research_baseline"]}.</p></div><label for="court-filter">Find by court, state abbreviation, or circuit (for example CA11)</label><input id="court-filter" data-filter="court-list" type="search" placeholder="Florida, TX, CA11…"><p data-filter-count="court-list" aria-live="polite"></p><ul id="court-list" class="directory">' + ''.join(rows) + '</ul>'
        self.page('districts/', 'District courts and rules', content, 'Court source directory')

    def process(self):
        outgoing = defaultdict(list)
        for e in self.edges: outgoing[e['from_node']].append(e)
        by_node = {n['node_id']:n for n in self.nodes}
        body = '<h1>A process, not a promise.</h1><p class="lede">Explore the recorded paths and the conditions connecting them. Branches are not automatic entitlements, and not every case follows a single sequence.</p><div class="notice"><strong>Read the conditions before following an arrow.</strong><p>Each connection preserves its canonical condition and claim references. The linked module controls over a diagram label.</p></div><label for="node-filter">Filter process nodes</label><input id="node-filter" type="search" data-filter="node-list" placeholder="Appeal, custody, sentencing…"><p data-filter-count="node-list" aria-live="polite"></p><div id="node-list" class="process-grid">'
        selector = '<section class="route-explorer"><p class="eyebrow">FOLLOW ONE CONDITIONAL PATH</p><label for="process-node">Choose a process node</label><select id="process-node">' + ''.join(f'<option value="{n["node_id"]}" {"selected" if n["node_id"]=="NODE-FEDERAL-SCOPE" else ""}>{escape(n["label"])}</option>' for n in sorted(self.nodes,key=lambda n:n['label'])) + '</select><p id="route-status" role="status">The complete relationship list below also works without JavaScript.</p><div id="route-view" class="route-view"></div></section>'
        body = body.replace('<label for="node-filter">', selector + '<h2>Complete relationship register</h2><label for="node-filter">')
        self.write('assets/process-index.json',json.dumps({'nodes':[{**n,'url':self.url(self.route_map[self.by_module[n['module_id']]['path']])} for n in self.nodes],'edges':[{**e,'claims':[{'id':c,'url':self.url(self.route_map[self.by_claim[c]['document_path']])+'#record-'+c} for c in e.get('claim_ids',[]) if c in self.by_claim]} for e in self.edges]},ensure_ascii=False))
        for n in self.nodes:
            body += f'<section class="node" id="{n["node_id"]}" data-filter-text="{escape((n["label"]+" "+n["node_type"]).lower(),quote=True)}"><span class="eyebrow">{escape(n["node_type"])}</span><h2>{escape(n["label"])}</h2><p>{self.module_link(n["module_id"])}</p><details><summary>{len(outgoing[n["node_id"]])} outgoing relationships</summary><ul>'
            for e in outgoing[n['node_id']]:
                body += f'<li><a class="node-jump" href="#{e["to_node"]}">{escape(by_node[e["to_node"]]["label"])}</a><p><strong>{escape(e["relationship"].replace("_"," "))}</strong>: {escape(e.get("condition", "No additional condition recorded"))}</p><p class="quiet">Claims: ' + ', '.join(self.anchor(self.route_map[self.by_claim[c]['document_path']] + '#record-' + c, c) for c in e.get('claim_ids',[]) if c in self.by_claim) + '</p></li>'
            body += '</ul></details></section>'
        self.page('process/', 'Process explorer', body + '</div>', f'{len(self.nodes)} nodes / {len(self.edges)} conditional relationships')

    def limitations(self):
        counts = Counter(i['category'] for i in self.questions['items'])
        body = '<h1>Scope &amp; methodology</h1><p class="lede">How the reference is built, what it covers, and how to use it well.</p><div class="prose"><h2>What it covers</h2><p>The federal criminal process, from investigation and charging through trial, sentencing, appeal, post-conviction remedies, custody and supervised release. Circuit notes record where a circuit departs from or adds to the nationwide rules. The court directory links each district court to its official local rules.</p><h2>How statements are sourced</h2><p>Each legal statement is a separate record tied to the statutes, rules or decisions that support it, and links to that authority. Each authority record shows its citation, issuing body, weight and official source.</p><h2>Currency</h2><p>The reference is current through ' + human_date(self.cfg['research_baseline']) + '. Each topic and authority shows two dates. <strong>Legal review</strong> is the date its statements were last checked against the sources, including later history and treatment where recorded. <strong>Links checked</strong> is the date an automated check last confirmed that each recorded source still opens; it does not show that the law is unchanged, and it never moves the legal review date. Laws, rules and local practice change; confirm the current text of any rule before relying on it, and check local rules and standing orders for the court involved.</p><h2>Not legal advice</h2><p>This is general legal information. It does not create an attorney-client relationship, and it cannot account for the facts of a particular case. For advice about a specific case, consult a licensed attorney.</p><h2>Open research questions</h2><p>The items below are questions the research has not yet resolved, such as a circuit that has not addressed an issue or a local rule whose text has not been reviewed. They are listed so they can be checked and closed.</p></div><div class="stats">' + ''.join(f'<div><strong>{n}</strong><span>{escape(k.replace("_"," "))}</span></div>' for k,n in counts.items()) + '</div><h2>Open research register</h2><p>Earlier draft wording listed here is shown for review only and is not a statement of law.</p><label for="issue-filter">Filter by issue, jurisdiction, or ID</label><input id="issue-filter" type="search" data-filter="issue-list" placeholder="CA4, Rule 33, district…"><p data-filter-count="issue-list" aria-live="polite"></p><div id="issue-list">'
        for item in self.questions['items']:
            cid = item['coverage_id']
            module_path = item.get('responsible_module')
            detail = self.record_fields({k:item.get(k) for k in ('status','category','disposition','dependency','stop_condition','last_updated')})
            if item.get('legacy_claim_text'):
                detail += '<h3>Unverified legacy wording — not a statement of law</h3><blockquote>' + escape(item['legacy_claim_text']) + '</blockquote>'
            if item.get('original_text_withheld'):
                detail += '<p>' + escape(item['withholding_reason']) + '</p><p class="quiet">Original text SHA-256: ' + item['original_text_sha256'] + '</p>'
            if module_path in self.route_map: detail += '<p>' + self.anchor(self.route_map[module_path], 'Read the replacement module') + '</p>'
            body += f'<details id="{cid}" data-filter-text="{escape((cid+" "+item["description"]+" "+item["category"]).lower(),quote=True)}"><summary>{escape(item["description"])}</summary><p class="quiet">{cid}</p>{detail}</details>'
        self.page('limitations/', 'Scope & methodology', body + '</div>', 'Reference')

    def sources_page(self):
        body = '<h1>Go to the source.</h1><p class="lede">Recorded primary-source locations and historical retrieval dates. The linked authority record explains the proposition and its limitations.</p><label for="source-filter">Filter source registry</label><input id="source-filter" type="search" data-filter="source-list" placeholder="Statute, court, agency…"><p data-filter-count="source-list" aria-live="polite"></p><ul id="source-list" class="directory">'
        for s in self.sources:
            href = s.get('official_url') or s.get('mirror_url')
            body += f'<li id="{s["source_id"]}" data-filter-text="{escape((s["title"]+" "+s["source_id"]).lower(),quote=True)}"><a href="{escape(href,quote=True)}">{escape(s["title"])}</a><span>{escape(s["source_id"])} · recorded retrieval {escape(str(s.get("retrieval_date")))}</span><p>{escape(str(s.get("source_currency", "Read source version and authority card")))}</p></li>'
        self.page('sources/', 'Source registry', body + '</ul>')

    def master_and_downloads(self):
        order = yaml.safe_load((ROOT / 'manifest/module_order.yaml').read_text(encoding='utf-8'))['modules']
        body = '<h1>Federal Judicial Process</h1><p class="lede">Complete printable reference. Use your browser’s Print command to print or save as PDF.</p><div class="notice"><strong>Research baseline: ' + self.cfg['research_baseline'] + '</strong><p>This is a generated compilation, not a new legal verification. ' + self.anchor('limitations/', 'Read the full limitations register') + '</p></div><ol>'
        master_md = ['# Federal Judicial Process\n\nGenerated compilation. Research baseline: '+self.cfg['research_baseline']+'. Not newly reverified.\n']
        for m in order:
            body += f'<li><a href="#{m["module_id"]}">{escape(self.by_module[m["module_id"]]["title"])}</a></li>'
        body += '</ol>'
        for m in order:
            src = m['path']
            raw = (ROOT / src).read_text(encoding='utf-8')
            _, text = frontmatter(raw)
            rendered, _ = self.render(src, raw)
            # Prefix every local heading ID/reference to avoid duplicate IDs across modules.
            prefix = m['module_id'] + '-'
            rendered = re.sub(r'id="([^"]+)"', lambda x:'id="'+prefix+x.group(1)+'"', rendered)
            rendered = re.sub(r'href="#([^"]+)"', lambda x:'href="#'+prefix+x.group(1)+'"', rendered)
            body += f'<article class="prose master-module" id="{m["module_id"]}"><p>{self.module_link(m["module_id"])}</p>{rendered}</article>'
            master_md.append(self.MD_LINK.sub(lambda x: x.group(1) + self.md_resolve(src, x.group(2)) + x.group(3), text))
        self.page('master/', 'Printable master reference', body)
        self.write('downloads/MASTER_FEDERAL_JUDICIAL_PROCESS.md', '\n\n---\n\n'.join(master_md))
        for folder in ('data','sources','diagrams'):
            for src in sorted((ROOT / folder).rglob('*')):
                if src.is_file() and not src.name.startswith('.'):
                    dst = self.out / 'downloads' / src.relative_to(ROOT)
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(src,dst)
        # Deterministic zip: portable source content only, no build/runtime/private data.
        bundle = self.out / 'downloads/reference-data.zip'
        with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for folder in ('docs','authorities','data','sources','schemas','manifest','diagrams'):
                for src in sorted((ROOT / folder).rglob('*')):
                    if not src.is_file() or src.name.startswith('.'): continue
                    info = zipfile.ZipInfo(src.relative_to(ROOT).as_posix(), (2026,8,26,0,0,0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info,src.read_bytes())
            for name in ('PUBLICATION_POLICY.md','LICENSE_STATUS.md','LICENSE','LICENSE-CONTENT.md','release.json'):
                info = zipfile.ZipInfo(name,(2026,8,26,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info,(ROOT/name).read_bytes())
        body = '<h1>Take the reference with you.</h1><p class="lede">Portable records and a printable master, generated from the same canonical content. Verification limits travel with the data.</p><div class="cards">' + self.anchor('master/','Open printable master / Save as PDF →','card') + self.anchor('downloads/MASTER_FEDERAL_JUDICIAL_PROCESS.md','Download master Markdown →','card') + self.anchor('downloads/reference-data.zip','Download complete public reference data →','card') + '</div><h2>Structured data</h2><ul class="directory">'
        for path in sorted((self.out / 'downloads/data').glob('*')):
            body += '<li>' + self.anchor('downloads/data/'+path.name,path.name) + '</li>'
        self.page('downloads/', 'Downloads', body + '</ul><p class="currency">Content and data: <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Code: MIT. ' + self.anchor('about/', 'Attribution and license details') + '</p>')

    def build(self):
        if self.out.is_symlink() or (self.out.exists() and self.out.resolve() != ROOT / 'dist/site'):
            raise ValueError('Public output must be a real directory inside this repository')
        self.out.mkdir(parents=True,exist_ok=True)
        # Delete only files belonging to the previous generated manifest, never an arbitrary tree.
        prior = self.out / 'manifest.json'
        if prior.exists():
            for entry in read_json(prior)['files']:
                candidate = (self.out / entry['path']).resolve()
                if not candidate.is_relative_to(self.out.resolve()): raise ValueError('Unsafe previous manifest path')
                if candidate.is_file(): candidate.unlink()
            prior.unlink()
        self.home(); self.module_pages(); self.authority_pages(); self.markdown_twins(); self.district_pages()
        self.process(); self.limitations(); self.sources_page(); self.master_and_downloads()
        about = (ROOT / 'PUBLICATION_POLICY.md').read_text(encoding='utf-8') + '\n\n' + (ROOT / 'LICENSE_STATUS.md').read_text(encoding='utf-8')
        body, _ = self.render('PUBLICATION_POLICY.md',about)
        self.page('about/','About this personal project','<article class="prose">'+body+'</article>')
        self.page('search/','Search the reference','<h1>Find a starting point.</h1><p class="lede">Search modules, authorities, and courts. Search results are navigation, not legal answers.</p><form id="search-form" role="search"><label for="query">Search the reference</label><div class="search-row"><input id="query" name="q" type="search" placeholder="Section 2255, compassionate release, Texas…"><button type="submit">Search</button></div></form><p id="search-status" role="status">Enter a term to search the local reference index.</p><ol id="search-results" class="directory"></ol><noscript><p>Search requires JavaScript. All content remains available through the module, authority, and court directories.</p></noscript>')
        self.write('assets/search-index.json',json.dumps(self.search,ensure_ascii=False))
        for path in (ROOT/'web').glob('*'):
            if path.is_file(): shutil.copyfile(path,self.out/'assets'/path.name)
        urls = ''.join('<url><loc>'+escape(self.cfg['site_origin']+self.url(route))+'</loc></url>' for route in sorted(set(self.pages) - self.unlisted_routes))
        self.write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+'</urlset>')
        for directory in sorted((p for p in self.out.rglob('*') if p.is_dir()), key=lambda p:len(p.parts), reverse=True):
            if directory.is_symlink(): raise ValueError('Symlink in public output')
            if not any(directory.iterdir()): directory.rmdir()
        files = [{'path':p.relative_to(self.out).as_posix(),'sha256':sha(p.read_bytes()),'size':p.stat().st_size} for p in sorted(self.out.rglob('*')) if p.is_file() and p.name!='manifest.json']
        manifest = {'schema_version':1,'base_path':self.base,'source_digest':self.digest,'research_baseline':self.cfg['research_baseline'],'build_as_of':self.as_of.isoformat(),'legal_reverification_performed':False,'counts':{'modules':len(self.modules),'claims':len(self.claims),'authorities':len(self.authorities),'nodes':len(self.nodes),'edges':len(self.edges),'districts':len(self.districts),'catalog_sources':self.catalog['document_count'],'unresolved_items':len(self.questions['items']),'pages':len(self.pages)},'files':files}
        self.write('manifest.json',json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'status':'built_not_published','counts':manifest['counts'],'files':len(files),'source_digest':self.digest}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Default to the release record's date so the same commit always builds the same site.
    parser.add_argument('--as-of',default=read_json(ROOT / 'release.json')['build_as_of'])
    args = parser.parse_args()
    Builder(args.as_of).build()
