"""Negative controls plus full-publication checks; never a substantive-law test."""
import sys
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from validate_public import ROOT, Page, link_target, privacy_errors, safe_relative, validate


class PublicationTests(unittest.TestCase):
    def test_downloads_unlisted_but_retained(self):
        site = ROOT / "dist/site"
        downloads = (site / "downloads/index.html").read_text(encoding="utf-8")
        self.assertIn('<meta name="robots" content="noindex, nofollow">', downloads)
        self.assertTrue((site / "downloads/reference-data.zip").is_file())
        self.assertNotIn('/legal/federal-process/downloads/', (site / "sitemap.xml").read_text(encoding="utf-8"))
        for page in site.rglob("index.html"):
            html = page.read_text(encoding="utf-8")
            navigation = html.split('<nav aria-label="Reference navigation">', 1)[1].split('</nav>', 1)[0]
            self.assertNotIn('/downloads/', navigation, str(page))

    def test_complete_publication(self):
        errors,_=validate()
        self.assertEqual([],errors,"\n".join(errors[:30]))

    def test_reject_unsafe_archive_paths(self):
        for path in ("../private.txt","%2e%2e/private.txt","/secret.txt","C:/secret.txt","folder\\secret.txt",".git/config","logs/run.jsonl","x/~$file.pdf","x/a.ppwritelock","data/coverage_matrix.yaml"):
            with self.subTest(path=path):
                self.assertFalse(safe_relative(path))
        self.assertTrue(safe_relative("data/claims.jsonl"))

    def test_privacy_negative_controls(self):
        for text in ("Zip"+"Law","C:/Users/Somebody/Documents/test","file:///private","-----BEGIN PRIVATE KEY-----","ghp_"+"a"*35):
            with self.subTest(text=text[:16]):
                self.assertTrue(privacy_errors("test.txt",text.encode()))
        self.assertFalse(privacy_errors("test.txt",b"https://www.govinfo.gov Rule 6 secret indictment"))

    def test_internal_link_resolution(self):
        base="/legal/federal-process/"
        origin="https://jason93.com"
        self.assertEqual(("modules/a/index.html","record-1"),link_target("modules/a/index.html","#record-1",base,origin))
        self.assertEqual(("modules/b/index.html",""),link_target("modules/a/index.html","../b/",base,origin))
        self.assertIsNone(link_target("index.html","/legal/",base,origin))
        self.assertIsNone(link_target("index.html","https://www.govinfo.gov/",base,origin))
        for bad in ("javascript:alert(1)","/admin/","../../private/"):
            with self.subTest(link=bad),self.assertRaises(ValueError):
                link_target("index.html",bad,base,origin)

    def test_duplicate_id_detection_input(self):
        page=Page('<h1 id="same">A</h1><p id="same">B</p>')
        self.assertNotEqual(len(page.ids),len(set(page.ids)))

    def test_tampered_release_is_rejected(self):
        # Mutate only an isolated temporary COPY. The reviewed source/site is untouched.
        with tempfile.TemporaryDirectory(prefix="federal-publication-negative-") as temporary:
            site=Path(temporary)/"site"
            shutil.copytree(ROOT/"dist/site",site)
            home=site/"index.html"
            home.write_text(home.read_text(encoding="utf-8")+'<i id="main"></i><a href="missing/">broken</a><a href="#missing-anchor">bad anchor</a>',encoding="utf-8")
            (site/"unexpected.txt").write_text("unlisted generated file",encoding="utf-8")
            with zipfile.ZipFile(site/"downloads/reference-data.zip","a") as archive:
                archive.writestr("../private.txt","must not publish")
            errors,_=validate(site=site)
            combined="\n".join(errors)
            for required in ("manifest inventory", "manifest hash/size mismatch: index.html", "duplicate HTML ID: index.html", "broken link: index.html", "broken fragment: index.html", "ZIP content scope mismatch", "unsafe/private artifact path: ../private.txt"):
                with self.subTest(check=required):
                    self.assertIn(required,combined)

    def test_metadata_conflicts_and_one_way_links_are_rejected(self):
        # Mutate an isolated temporary COPY of the sources; the repository is untouched.
        with tempfile.TemporaryDirectory(prefix="federal-source-negative-") as temporary:
            root=Path(temporary)/"repo"
            shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns(".git","dist",".venv","__pycache__",".review"))
            card=next((root/"authorities").rglob("AUTH-USC-28-2255.md"))
            card.write_text(card.read_text(encoding="utf-8").replace("authority_id: AUTH-USC-28-2255\n","authority_id: AUTH-USC-28-2255\njurisdiction: federal\n",1),encoding="utf-8")
            data=root/"data/authorities.jsonl"
            lines=data.read_text(encoding="utf-8").splitlines()
            lines=[l.replace('"linked_claim_ids":["','"linked_claim_ids":["CLM-NOT-REAL-001","',1) if '"authority_id":"AUTH-USC-28-2255"' in l else l for l in lines]
            data.write_text("\n".join(lines)+"\n",encoding="utf-8")
            errors,_=validate(root=root,site=ROOT/"dist/site")
            combined="\n".join(errors)
            for required in ("authority card header must be only its authority_id","authority claim links not two-way: AUTH-USC-28-2255"):
                with self.subTest(check=required):
                    self.assertIn(required,combined)

    def test_link_check_record_never_claims_a_legal_review(self):
        from record_link_check import condense
        report={"kind":"source_identity_review_report","as_of":"2026-10-15","selection":{"is_partial_selection":False},"results":[
            {"url":"https://www.govinfo.gov/a","status":"no_accepted_baseline","evidence":{},"identities":[{"source_id":"SRC-A","authority_ids":["AUTH-A"]}]},
            {"url":"https://www.govinfo.gov/b","status":"fetch_failed","evidence":{"error":{"kind":"http_error","message":"HTTP 403"}},"identities":[{"source_id":"SRC-B","authority_ids":["AUTH-A","AUTH-B"]}]}]}
        record=condense(report)
        self.assertEqual({"opened":1,"failed":1},record["counts"])
        self.assertEqual({"AUTH-A":"opened","AUTH-B":"failed"},record["authorities"])
        self.assertIn("not a legal review",record["method"])
        report["selection"]["is_partial_selection"]=True
        with self.assertRaises(ValueError):
            condense(report)


if __name__ == "__main__":
    unittest.main()
