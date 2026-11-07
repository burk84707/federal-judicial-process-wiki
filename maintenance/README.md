# Source maintenance: detect, review, approve

The monitor is a **review queue**, not a legal updater. It never edits source
records, claims, modules, verification dates, or a previously accepted baseline.
A successful download and an unchanged hash do not establish current law.

## Present operating boundary

- The workflow **Weekly source and law-change review** (`.github/workflows/source-review.yml`)
  runs every Monday at 13:47 UTC and can also be started by hand. The owner approved
  recurring operation on 2026-11-07 (Phase 6).
- Each scheduled run checks every recorded source, runs the change watchers
  (`scripts/watch_changes.py`, below), rebuilds and validates the reference with the new
  records, and proposes them in **one pull request** from the branch
  `automation/weekly-review`. The pull request description is the week's report.
- The only files the automation writes are `data/link_check.json` and
  `maintenance/watch_state.json`, and only on that branch. It never edits a claim,
  authority, module, source record or review date, never accepts a baseline, and never
  merges. The owner reviews and merges, and acts on each finding in a separate change.
- If repository settings do not allow GitHub Actions to open pull requests, the run
  opens an issue labelled `source-review` with the same report and a link to the branch.
- Pull requests opened by GitHub Actions do not trigger other workflows, so the CI check
  does not run on them; the weekly job runs the full build and validator itself before it
  proposes anything.

## Change watchers

`scripts/watch_changes.py` reads the publishers that change the law this reference
relies on. Its state lives in `maintenance/watch_state.json`, so each run reports only
what is new. Every finding is for review; none is applied automatically.

| Watcher | Source | Finding |
| --- | --- | --- |
| `bop_policies` | BOP policy index, for each cited program statement's series | A cited statement replaced by a newer version, given a new change notice, reissued with a new date, or no longer listed |
| `federal_register` | Federal Register API, for each CFR part cited by a regulation authority | A rule or proposed rule published since the last run |
| `supreme_court` | Supreme Court opinions for the current term | Each new opinion; marked for review when the United States is a party |
| `rules_amendments` | Federal courts' pending rules and forms amendments page | A new document; and, from October 2 to December 1, each cited *proposed* rule, which may take effect December 1 |
| `uscode_edition` | GovInfo link service, one cited section per title | GovInfo serving a newer edition of a cited title |
| `review_dates` | `data/modules.json` | Modules due for legal review within 21 days |

The link-check comparison also reports sources that stopped opening since the last
recorded check, and sources that recovered. A watcher that cannot reach its source is
listed under "Watchers that could not run" and keeps its last state, so nothing is
skipped silently.

- Raw response bodies are read completely within a 16 MiB ceiling, then discarded.
  Reports retain SHA-256, byte count, response metadata, redirect chain, source
  identities, and known authority/claim/module dependencies. Oversized bodies are
  failures, never truncated fingerprints.
- Local output is confined to ignored `.review/<run>/`. Workflow evidence is an
  artifact, not published website content. Remote artifacts expire after 30 days.
- Only public HTTP(S) destinations under government domains or explicitly listed
  legal-source mirrors are accepted. DNS answers and every redirect are checked;
  the connection pins a vetted numeric address while preserving TLS hostname
  verification. No credentials, cookies, or proxy configuration are used.
- Mirror-only records remain identified as nonofficial. Rejected or failed sources
  are visible failures and do not stop unrelated source checks.

## Local commands

Install the repository requirements first, then run from the repository root:

```sh
python -m unittest discover -s tests -p test_monitor_sources.py -v
python scripts/monitor_sources.py --inventory-only
python scripts/monitor_sources.py --source-id SRC-USC-28-2255-OLRC-PRELIM
python scripts/monitor_sources.py
python scripts/monitor_sources.py --include-districts
```

The default checks each registry entry's official URL, or its recorded mirror
when no official URL is present. `--include-districts` adds known district landing
pages and catalog documents. Identical URLs are fetched once while retaining all
identities. District IDs are reported even when no canonical claim mapping exists.
The link monitor is **not** a crawler: it does not discover new documents, newly issued cases,
new amendments, or new adverse treatment. The change watchers above cover the main
publishers; adverse treatment of cited cases still needs a citator or a separate research task.

Use `--limit 5` for an explicitly partial sample. Reports record the selected
scope. An ordinary request defaults to a 20-second attempt timeout and one retry;
retries are bounded and only transient failures are retried. Full inventory runs
may take substantial time. Do not bypass server restrictions or repeatedly hammer
failed sites. A cancelled/timed-out workflow is not a completed source check.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Selected source bytes/locations match the supplied baseline and no module review is due; not legal verification |
| 1 | Human review required: changed identities, no accepted baseline, or due/missing module review dates |
| 2 | One or more source requests failed; inspect unaffected results too |
| 3 | Invalid input, data, baseline, or output error |

## First baseline and later comparisons

The initial run reports `no_accepted_baseline`. Historical registry status or
existing catalog hashes are **not** silently treated as an approved baseline.
Each run writes `report.json` and `candidate-baseline.json`. The latter is expressly
unaccepted and cannot be supplied directly to `--baseline`.

A human reviewer inspects the requested and final URLs, successful full-body
fingerprints, source identity, and errors. Save a separate JSON file using:

```json
{
  "kind": "manually_accepted_source_identity_baseline",
  "reviewed_by": "Actual reviewer identifier",
  "reviewed_at": "Actual review timestamp",
  "snapshots": {}
}
```

Populate `snapshots` only with the URL-keyed records that the reviewer has accepted
from the candidate file. Do not accept missing or failed records, blindly replace
unrelated baseline entries after a partial run, or invent a review timestamp.
Store this approved file in a maintainer-controlled location outside the canonical
legal data; its content is not proof of proposition-level legal review. Compare:

```sh
python scripts/monitor_sources.py --baseline path/to/accepted-baseline.json
```

The manual workflow currently makes baseline-free reports. Supplying a controlled
accepted baseline to hosted runs is intentionally deferred until the owner chooses
its storage and review process. No unattended baseline advancement is permitted.

## Legal review and publication

For a changed or overdue item, review the current authoritative text and effective
date, jurisdiction, posture, exceptions, and any relevant subsequent treatment.
Use the report's dependency IDs to identify claims and modules requiring review.
Distinguish a site-template change from an actual source change; unchanged source
bytes do not detect later contrary authority elsewhere.

Only after documented human review should canonical edits, verification dates,
and an updated accepted technical baseline be proposed. Run the publication tests,
inspect the diff and public output, and obtain owner approval before committing
or publishing. Website release automation may deploy an approved release; it must
not turn a monitor result into an automatic legal conclusion.
