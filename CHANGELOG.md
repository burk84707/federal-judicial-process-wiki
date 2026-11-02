# Changelog

Release identity is the `version` in `release.json` plus the source digest printed in each page footer. Legal review dates are recorded per record and never change because of a release.

## 1.3.0 — 2026-11-02 (draft; not published)

Status: Owner approved; double legal review completed; licensed-attorney approval not recorded.

- Corrections from the October 30 – November 2, 2026 review of the research archive: two independent reviewers checked every claim against saved copies of its sources; Guidelines claims were rechecked for the amendments effective November 1, 2026 and now cite the 2026 Guidelines Manual; the November 1, 2026 double legal review was applied. 418 claims rewritten, 10 deleted, 2 added (CLM-3582-027, CLM-DISTRICT-MAP-003); 1,072 claims in all. Each claim keeps the date it was actually reviewed.
- 46 new authority records, including the 2026 Guidelines Manual provisions, the November 2026 Guidelines amendments (91 Fed. Reg. 24,088), *Fernandez v. United States* and *Rutherford v. United States*, the Rule 35 advisory committee notes, 19 U.S. Code sections, and the current 28 C.F.R. part 523 subpart E.
- Twelve circuit-overlay claims that rely on 18 U.S.C. § 3582 now cite the § 3582 record rather than the § 3583 page.
- Link targets: U.S. Code stays on GovInfo with the Law Revision Counsel's current page as mirror; Supreme Court opinions use the Court's preliminary prints. 101 of the 103 new URLs were confirmed; two Constitution Annotated pages refuse automated checks.
- Full change report, by module, with reasons and source quotations: `maintenance/correction-release-1.3.0/`.

## 1.2.1 — 2026-10-15

- Eight sources that refuse automated requests (four Third Circuit opinions, the Seventh Circuit rules, three Constitution Annotated pages) were checked by hand in a browser and recorded as available. 377 of 380 sources are now available.

## 1.2.0 — 2026-10-15

- Legal review of four claims whose sources changed after August 2026, approved by the owner: BOP PS 5160.05 was rescinded by PS 5160.06 (Sept. 3, 2026); 28 C.F.R. § 523.42(a) was amended by 91 FR 55740 (effective Sept. 30, 2026), following *Miles v. Bowers* (1st Cir. 2026); the BOP Federal Time Credit Application Guide was removed from bop.gov and is kept as archived guidance. New authority records for PS 5160.06, 91 FR 55740 and *Miles v. Bowers*.
- Source links: six Supreme Court PDFs and two public laws point to working official copies; every U.S. Code link points to GovInfo, with the Law Revision Counsel preliminary text kept as a mirror; 14 opinions republished on Justia, OpenJurist or CourtListener point to CourtListener and are confirmed through its API (`data/source_confirmations.json`).
- Link check of October 15: 369 of 380 sources available (354 opened, 15 confirmed through CourtListener). The rest are listed in `maintenance/link-review-2026-10-15.md`.
- Checker fixes: IPv4-first connections, a 60-second limit, and error pages or web pages returned for PDFs now count as failures. A read-only probe workflow tests candidate URLs before any record changes.
- Carmona v. BOP, 243 F.3d 629: decision date March 20, 2001 confirmed from Caselaw Access Project data.

## 1.1.0 — 2026-10-15

- Single source of truth: module and authority headers now carry only their ID; all metadata lives in `data/`. The migration and its rules are in `maintenance/migrations/2026-10-15-single-source.py`.
- Resolved every header-versus-data conflict: 306 field conflicts on authority cards, 7 on module headers, and header-only fields on 27 modules moved into the data. Claim and module links are now two-way.
- Jurisdiction values use one controlled list, enforced by schema.
- Pages show two dates: **Legal review** and **Links checked**, from the automated source run.
- Every page with a Markdown version shows a "View as Markdown" link.
- The validator rejects metadata in headers and one-way links. CI runs on every pull request.
- Added CONTRIBUTING, issue templates, this changelog, and `scripts/record_revisions.py`, which records edits to pinned files.

## 1.0.0 — 2026-10-15

- First public edition: reader-facing banner and footer, Scope & methodology page, stage menu, Markdown version of every page, `llms.txt`, MIT and CC BY 4.0 licenses.
