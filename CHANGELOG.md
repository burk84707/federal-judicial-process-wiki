# Changelog

Release identity is the `version` in `release.json` plus the source digest printed in each page footer. Legal review dates are recorded per record and never change because of a release.

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
