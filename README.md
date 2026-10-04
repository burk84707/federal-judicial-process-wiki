# Federal Judicial Process

A personal, source-linked federal criminal-process reference by **Jason93**.

**Clean personal-source edition; repository publication authorized by the owner.** The intended website is `https://jason93.com/legal/federal-process/`. Repository publication is separate from website deployment; this README does not claim that route is live.

## What is here

- 66 canonical modules spanning investigation, pretrial, plea/trial, sentencing, review, post-conviction remedies, prison processes and reentry.
- 1,080 atomic claims and 377 structured authority records with source links and qualifications.
- An interactive, accessible process explorer over 81 nodes and 103 conditional relationships.
- A searchable directory of all 94 district-level courts and 1,466 cataloged source entries.
- Search, printable master compilation, portable source/data downloads, and all 468 unresolved review items.

These counts describe the inherited source set, **not a claim that every item is current or verified**. The research baseline is **2026-08-26**, with individual recorded dates preserved. Three canonical claims are partially verified and four are historical. All 94 district-rule text reviews remain unresolved. The build does not provide a fresh legal review or a citator guarantee.

## Run locally

Requires Python 3.12 or newer. Run from this repository:

```sh
python -m venv .venv
# Windows PowerShell:
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe scripts/build_public.py
.venv/Scripts/python.exe scripts/validate_public.py
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe scripts/serve_preview.py
```

On macOS/Linux use `.venv/bin/python` in place of `.venv/Scripts/python.exe`.
Open `http://127.0.0.1:8766/legal/federal-process/`. The preview is loopback-only; it does not publish anything. Press Ctrl+C to stop it.

For a repeatable dated build use `python scripts/build_public.py --as-of 2026-10-02` with the environment activated. The build date controls overdue-review warnings; it does not change recorded verification dates. Never backdate a legal review to match a build.

## Canonical vs generated

| Location | Role |
| --- | --- |
| `docs/` | Canonical module prose and claim markers |
| `authorities/` | Authority cards and source limitations |
| `data/` | Claims, authorities, structured controls, graph, court catalog and public uncertainty register |
| `sources/` | Recorded source registry, not bulk copyrighted snapshots |
| `manifest/import_receipt.json` | Original input hashes and disclosed provenance transformations |
| `web/` | Small framework-free reference-site assets |
| `scripts/`, `tests/` | Reproducible build, validation and review-only maintenance |
| `dist/site/` | Generated deployment payload; ignored by Git |
| `.review/` | Private local monitoring evidence; ignored by Git |

Generated pages do not control the legal content. Edit canonical source records together, preserve IDs and qualifications, then rebuild and validate. A verifier checks internal consistency and publication safety; it does not replace review of the actual law.

The Downloads page is retained but unlisted: no navigation entry, no sitemap entry, and a `noindex, nofollow` instruction. Its direct URL and files still work. This is not authentication or a paywall and does not prevent copying. No free-reuse license has been granted. The reference theme uses the personal site's near-black, warm-white, gold, glass-panel and monospace design language without adding its animated backdrop to reading pages.

## Integrate with the personal website

The separate `jason93-astro` site consumes the generated `dist/site/` payload, validates `manifest.json` and all file hashes, and mounts it under `/legal/federal-process/`. Do not copy this repository root or private archive into an Astro public folder.

The payload includes a source digest, exact inventory, byte counts, hashes and recorded research baseline. The Astro integration accepts a local artifact for preview or an explicitly pinned approved release for production. Its deployment instructions explain import, approval and rollback. No production deploy runs from this repository.

Build output belongs in deployment artifacts or versioned release downloads, not source commits. No Git submodule or nested archive checkout is needed. Use a new public history; never push the private research archive's old history into this repository.

## Update boundary

See [maintenance/README.md](maintenance/README.md). Monitoring reports source identity changes, errors and overdue records. It never revises claims, accepts baselines or advances verification dates. The GitHub workflow is **manual only** until the owner approves recurring operation and its baseline-review process.

## Rights, provenance and exclusions

Read [PUBLICATION_POLICY.md](PUBLICATION_POLICY.md) and [LICENSE_STATUS.md](LICENSE_STATUS.md). Licensing is an explicit pending owner decision; this preparation grants no open-source or Creative Commons permissions.

The original research archive is preserved separately. Private filenames use stable aliases in public issue records. Six company-specific legacy texts are explicitly withheld with original-text hashes. The other exact legacy formulations remain marked unverified, not endorsed as law. No raw migration ledger, execution log, local machine path, editor lock, original branded document, or historical Git archive is included.

## Before approving a first release

1. Review the pending licensing and attribution choices.
2. Inspect the website, source selection, six disclosed text omissions and remaining legal limitations.
3. Run build, validation and tests from a clean environment.
4. Inspect the prospective Git content and configure the desired public commit author/email.
5. Approve commits separately from pushes, repository visibility and production deployment.

The owner authorized the initial clean-source commit and push on October 3, 2026. Website deployment, recurring monitoring, and any reuse-license grant remain separate decisions. Future releases must retain the same review and validation boundaries.
