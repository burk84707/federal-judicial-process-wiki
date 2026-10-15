# Link review: the 52 sources that failed on October 15, 2026

Source run [38761386067](https://github.com/burk84707/federal-judicial-process-wiki/actions/runs/38761386067) opened 325 of 377 recorded sources. Each failure was retested, and candidate replacements were tested, with the same fetcher in probe run [38770992566](https://github.com/burk84707/federal-judicial-process-wiki/actions/runs/38770992566). A replacement was made only when it opened and identified the same decision. No wording, citation or legal review date changed. Old URLs are kept in `sources/source_registry.yaml` (`previous_url`).

## Fixed: link replaced (10)

| Source | Problem | Replacement |
| --- | --- | --- |
| Lagos, 584 U.S. 577 | Court PDF returned 404 | GovInfo, United States Reports |
| Chavez-Meza, 585 U.S. 109 | Court PDF returned 404 | GovInfo, United States Reports |
| Rosales-Mireles, 585 U.S. 129 | Court PDF returned 404 | GovInfo, United States Reports |
| Haymond, 588 U.S. 634 | Court PDF returned 404 | Supreme Court slip opinion, No. 17-1672 |
| Banister, 590 U.S. 504 | Court PDF returned 404 | Supreme Court slip opinion, No. 18-6943 |
| Jones v. Hendrix, 599 U.S. 465 | Court PDF returned 404 | Supreme Court preliminary print |
| Rogers, 180 F.3d 349 (1st Cir.) | Host outside the approved source domains | CourtListener opinion page |
| Torres, 282 F.3d 1241 (10th Cir.) | Republication refuses automated requests | CourtListener copy of the court PDF |
| Saladino, 7 F.4th 120 (2d Cir.) | Republication refuses automated requests | CourtListener copy of the court PDF |
| Sanford, 986 F.3d 779 (7th Cir.) | Republication refuses automated requests | CourtListener copy of the court PDF |

## Fixed: checker error (13)

Seven Ninth Circuit opinions and the Second Circuit rules page failed only because the checker connected over IPv6, which the runner cannot reach; they open after the fix. Five D.C. Circuit files timed out; the limit is now 60 seconds per source. The next full run shows whether the D.C. Circuit server answers within that limit.

## Needs a decision (2)

- **BOP Program Statement 5160.05** (Jan. 16, 2003) is **rescinded**. BOP Program Statement 5160.06, *Designation of State Institutions for Service of Federal Sentence*, dated September 3, 2026 and approved by Director William K. Marshall III, lists under "Program Statement Rescinded": "5160.05, Designation of State Institution for Service of Federal Sentence (1/16/2003)". Read from `https://www.bop.gov/policy/progstat/5160_006.pdf` in probe run [38789802937](https://github.com/burk84707/federal-judicial-process-wiki/actions/runs/38789802937); the BOP policy index lists 5160.06 with the same date. Per its Summary of Changes, 5160.06 gives the DSCC Sentence Computation Section Chief final designation authority, adds the five § 3621(b) factors, adds *Setser v. United States*, 566 U.S. 231 (2012), *Mangum v. Hallembaek*, 910 F.3d 770 (4th Cir. 2018) and *Dotson v. Kizziah*, 966 F.3d 443 (6th Cir. 2020), removes the Regional Offices and Regional Director from the process, and updates nunc pro tunc procedures. The authority is now marked rescinded, claims CLM-BOPSC-009 and CLM-BOPSC-023 are marked superseded, and the module shows a notice. **Decision needed:** a legal review of those two claims against 5160.06, then a new authority record for 5160.06.
- **BOP FTC Application Guide** (Oct. 16, 2025) returns 404, and the BOP's own First Step Act policies page (`https://www.bop.gov/inmates/fsa/policies.jsp`) still links to that dead address. The same page links `https://www.bop.gov/resources/docs/fsa_time_credit_handout.pdf`, which also returns 404 (probe run [38790216182](https://github.com/burk84707/federal-judicial-process-wiki/actions/runs/38790216182)). No current copy was found on bop.gov. **Decision needed:** keep the record as a historical source with this note, find an archived copy, or drop the guide and rely on PS 5410.01 CN-2 and 28 C.F.R. part 523.

## Fixed after the second run (3)

The stricter checker found that the House Law Revision Counsel PDF links for Pub. L. 111-220 and Pub. L. 115-391 return a web page. They now point to the enrolled public laws on GovInfo, which opened in probe run 38789802937.

## Open: the site refuses automated requests (27)

These links are believed to work in a browser; the publisher blocks or drops automated requests. They need a manual check, or an official replacement where one exists.

- ~~Republications that answer 403 or 202: Justia (6), OpenJurist (4), CourtListener opinion pages (3).~~ **Resolved.** All 14 cases now point to their CourtListener opinion pages, and each was confirmed through CourtListener's API on 2026-10-15: the record exists, the reporter citation matches, and the full opinion text is present. Results are in `data/source_confirmations.json`, and pages count these sources as available. (The Barrett and Rogers First Circuit links recorded by CourtListener no longer exist on the court's site.)
- constitution.congress.gov (3): 403.
- uscode.house.gov (6): HTTP 500 for these six sections, while 32 other sections opened. GovInfo's copy of the code opened as an alternative, but it is the annual edition, not the current preliminary text.
- Third Circuit opinion archive (4) and Seventh Circuit rules PDF (1): the server closes the connection.

## Also found

- **Carmona v. BOP, 243 F.3d 629**: CourtListener's only record for this citation is dated 2001-10-25 and has no separate March 2001 record; the tools do not show whether the October record is an amended opinion. This reference keeps 2001-03-20 until the reporter is checked.

- **BOP PS 5880.28** (Sentence Computation Manual) is still listed in the BOP policy index and opens; no change.

- A redirect to an error page used to count as "opened". The checker now treats it, and a web page returned for a PDF request, as a failure. The next full run may therefore report a few more failures than before.

## Decisions after the final run (owner, October 15, 2026)

- **uscode.house.gov (27 server errors in the last run):** switched to GovInfo. All 35 sources and every inline link now point to the United States Code 2024 main edition on GovInfo; each target was verified to open on the right section in probe run [38792673966](https://github.com/burk84707/federal-judicial-process-wiki/actions/runs/38792673966). The Law Revision Counsel preliminary text stays as each source's `mirror_url`, with an edition note, because the 2024 edition does not include later amendments.
- **BOP time-credit guide:** kept as archived guidance, with the 2026-06-19 Wayback capture as its mirror.
- **Legal review drafts:** approved and applied (see `maintenance/legal-review-2026-10-15.md`).

## Checked by hand (owner, October 15, 2026)

The owner opened these in a browser and reported each document heading; each matched the record (docket number, parties, filed date or edition date). They are recorded in `data/source_confirmations.json` with `method: "browser"` and count as available.

- Third Circuit: Bruce (No. 14-4284), Melvin (No. 20-1158, filed Oct. 16, 2020), Raia (No. 20-1033, filed Apr. 2, 2020), Shields (No. 19-2717, filed Sept. 1, 2022).
- Seventh Circuit rules PDF: current as of December 1, 2025.
- Constitution Annotated: Fifth Amendment text; Art. II, § 2, cl. 1; essay ArtII.S2.C1.3.7, Legal Effect of a Pardon.

Not checked by hand: United States v. Lawrence (D.C. Cir.), which timed out in the final run but opened in the run before. The two retired BOP pages remain recorded as rescinded and archived.
