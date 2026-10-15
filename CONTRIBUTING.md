# Contributing

Anyone can report an error or propose a change. Every change is reviewed before it is merged, and every legal statement must stay tied to the authority that supports it.

## Report an error

Open an issue with **Something is wrong**. Give the page link or the claim ID (for example `CLM-2255-001`), quote the statement, and explain what is wrong. Include a primary source if you have one: the statute, rule or decision, with a pinpoint.

## Report a change in the law

Open an issue with **The law changed**. Name the new or amended authority, its effective or decision date, and the pages it affects, if you know them. A changed web page is not, by itself, a change in the law; say what changed in the legal text or holding.

Do not put confidential case records or personal information in a public issue.

## Propose a change

1. Fork the repository and create a branch.
2. Edit the record where it lives. Metadata (citations, dates, jurisdiction, links between records) lives only in `data/`. Module and authority headers carry only their ID; the validator rejects anything else.
3. A claim's text in `data/claims.jsonl` must match its text in the module exactly, and its marker in the module must list the same authorities and status.
4. Links are stored both ways. If a claim cites a new authority, add the claim to that authority's `linked_claim_ids`, and make sure the module lists the authority.
5. Never move a `last_verified` date unless you re-checked the record against its sources. The "Links checked" date comes only from the automated source run.
6. Record each edit to a pinned file, with a reason a reviewer can read:

   ```sh
   python scripts/record_revisions.py --reason "What changed and why" data/claims.jsonl docs/20-pretrial/
   ```

7. Build, validate and test before opening a pull request:

   ```sh
   python -m pip install -r requirements.txt
   python scripts/build_public.py
   python scripts/validate_public.py
   python -m unittest discover -s tests
   ```

## How review works

Continuous integration runs the build, the validator and the tests on every pull request. A pull request merges only when those checks pass and the owner has reviewed it. Changes to legal statements or authorities need a source a reviewer can check; style and tooling changes do not.

## Licenses

By contributing, you agree that your contribution is licensed under the same terms as the project: content and data under [CC BY 4.0](LICENSE-CONTENT.md), code under the [MIT License](LICENSE).
