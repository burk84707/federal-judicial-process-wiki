# Federal Judicial Process

A source-linked guide to the U.S. federal criminal process, from investigation and charging through trial, sentencing, appeal, post-conviction remedies, prison and reentry. By **Jason93**.

**Read it at [jason93.com/legal/federal-process](https://jason93.com/legal/federal-process/).**

> **General legal information, not legal advice.** This reference does not create an attorney-client relationship and cannot account for the facts of a particular case. Laws, rules and local practice change: check the current text of any authority before relying on it, and consult a licensed attorney about a specific case.

## What is here

- 66 modules covering investigation, pretrial, plea and trial, sentencing, review, post-conviction remedies, prison processes and reentry.
- 1,072 legal statements ("claims"), each tied to the authorities that support it, and 426 authority records with citations and official source links.
- An interactive process explorer: 81 steps and 103 conditional paths between them.
- A directory of all 94 district-level courts, with 1,466 cataloged local-rule and filing-procedure sources.
- Search, a printable compilation, and a Markdown version of every page.

## Currency and limits

Pages read **Current through November 2, 2026**. Release 1.3.0 applies corrections from an owner-approved double legal review (October 30 – November 2, 2026), including the Sentencing Guidelines amendments effective November 1, 2026; licensed-attorney approval is not recorded. Each record keeps the date it was actually reviewed, and the original research baseline is August 26, 2026.

One claim is partially verified and four are historical. The text of the 94 district courts' local rules has not been reviewed. The 468 open research items are questions the research has not resolved yet, such as a circuit that has not addressed an issue; they are listed on the site's Scope & methodology page so they can be checked and closed. Nothing here is a citator: check later history and treatment before relying on a decision.

A weekly automated review checks every source link and watches the publishers that change this law (BOP policies, the Federal Register, the Supreme Court, the federal rules committees and the U.S. Code). It reports findings to the owner; it never changes a legal statement.

## Report an error

Open an issue: **Something is wrong** for an incorrect statement, citation, link or date, or **The law changed** for a new or amended authority. Include the page link or claim ID and, if you have one, the primary source with a pinpoint. Do not post confidential case records or personal information.

Pull requests are not accepted. This is a single-owner reference, and every change to a legal statement is checked against its sources before it is published. Confirmed corrections from issues are applied in the next release. See [CONTRIBUTING.md](CONTRIBUTING.md).

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

Builds are repeatable: without `--as-of`, the build date is taken from `build_as_of` in `release.json`. The build date controls overdue-review warnings; it does not change recorded verification dates. Never backdate a legal review to match a build.

## Canonical vs generated

| Location | Role |
| --- | --- |
| `docs/` | Canonical module prose and claim markers; the header carries only the module ID |
| `authorities/` | Authority card prose; the header carries only the authority ID |
| `data/` | The only home for record metadata: claims, authorities, modules, structured controls, graph, court catalog, link-check record and public uncertainty register |
| `sources/` | Recorded source registry, not bulk copyrighted snapshots |
| `manifest/import_receipt.json`, `manifest/revisions.json` | Original input hashes, and the chain of approved edits since import |
| `web/` | Small framework-free reference-site assets |
| `scripts/`, `tests/` | Reproducible build, validation and review-only maintenance |
| `dist/site/` | Generated deployment payload; ignored by Git |
| `.review/` | Private local monitoring evidence; ignored by Git |

Generated pages do not control the legal content. Edit the data record, not a page header; record each edit to a pinned file with `scripts/record_revisions.py`; then rebuild and validate. The maintainer workflow is in [CONTRIBUTING.md](CONTRIBUTING.md). A verifier checks internal consistency and publication safety; it does not replace review of the actual law.

The Downloads page is retained but unlisted: no navigation entry, no sitemap entry, and a `noindex, nofollow` instruction. Its direct URL and files still work. This is not authentication or a paywall and does not prevent copying. The reference theme uses the personal site's near-black, warm-white, gold, glass-panel and monospace design language without adding its animated backdrop to reading pages.

## Integrate with the personal website

The separate `jason93-astro` site consumes the generated `dist/site/` payload, validates `manifest.json` and all file hashes, and mounts it under `/legal/federal-process/`. Do not copy this repository root or private archive into an Astro public folder.

The payload includes a source digest, exact inventory, byte counts, hashes and recorded research baseline. The Astro integration accepts a local artifact for preview or an explicitly pinned approved release for production. Its deployment instructions explain import, approval and rollback. No production deploy runs from this repository.

Build output belongs in deployment artifacts or versioned release downloads, not source commits. No Git submodule or nested archive checkout is needed. Use a new public history; never push the private research archive's old history into this repository.

## Update boundary

See [maintenance/README.md](maintenance/README.md). A weekly workflow checks every recorded source and watches the BOP policy index, the Federal Register, the Supreme Court, the federal rules committees and GovInfo for changes. It proposes its results in one pull request for the owner. It never revises claims, accepts baselines or advances verification dates.

## Rights, provenance and exclusions

Content and data are licensed under [CC BY 4.0](LICENSE-CONTENT.md); code is licensed under the [MIT License](LICENSE). Credit content as "Federal Judicial Process by Jason93". See also [PUBLICATION_POLICY.md](PUBLICATION_POLICY.md).

The original research archive is preserved separately. Private filenames use stable aliases in public issue records. Six company-specific legacy texts are explicitly withheld with original-text hashes. The other exact legacy formulations remain marked unverified, not endorsed as law. No raw migration ledger, execution log, local machine path, editor lock, original branded document, or historical Git archive is included.
