# Reporting errors

Anyone can report an error or a change in the law. Pull requests are not accepted: this is a single-owner reference, and every legal statement must stay tied to the authority that supports it. Reports are checked against their sources, and confirmed corrections are applied in the next release.

## Report an error

Open an issue with **Something is wrong**. Give the page link or the claim ID (for example `CLM-2255-001`), quote the statement, and explain what is wrong. Include a primary source if you have one: the statute, rule or decision, with a pinpoint.

## Report a change in the law

Open an issue with **The law changed**. Name the new or amended authority, its effective or decision date, and the pages it affects, if you know them. A changed web page is not, by itself, a change in the law; say what changed in the legal text or holding.

Do not put confidential case records or personal information in a public issue.

## Pull requests

Pull requests are closed without review. Open an issue instead. You are free to fork and reuse the project under its licenses.

## Maintainer workflow

How the owner makes a change:

1. Create a branch.
2. Edit the record where it lives. Metadata (citations, dates, jurisdiction, links between records) lives only in `data/`. Module and authority headers carry only their ID; the validator rejects anything else.
3. A claim's text in `data/claims.jsonl` must match its text in the module exactly, and its marker in the module must list the same authorities and status.
4. Links are stored both ways. If a claim cites a new authority, add the claim to that authority's `linked_claim_ids`, and make sure the module lists the authority.
5. Never move a `last_verified` date unless you re-checked the record against its sources. The "Links checked" date comes only from the automated source run.
6. Record each edit to a pinned file, with a reason a reviewer can read:

   ```sh
   python scripts/record_revisions.py --reason "What changed and why" data/claims.jsonl docs/20-pretrial/
   ```

7. Build, validate and test:

   ```sh
   python -m pip install -r requirements.txt
   python scripts/build_public.py
   python scripts/validate_public.py
   python -m unittest discover -s tests
   ```

## How review works

`main` takes changes only through pull requests. Continuous integration runs the build, the validator and the tests on each one; the weekly review pull request runs them inside its own workflow. Changes to legal statements or authorities need a source a reviewer can check; style and tooling changes do not.

## Licenses

Content and data are licensed under [CC BY 4.0](LICENSE-CONTENT.md), credited as "Federal Judicial Process by Jason93"; code is licensed under the [MIT License](LICENSE).
