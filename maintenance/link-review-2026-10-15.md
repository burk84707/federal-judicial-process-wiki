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

- **BOP Program Statement 5160.05** (Jan. 16, 2003) returns 404. The BOP policy index now lists **5160.06** at `https://www.bop.gov/policy/progstat/5160_006.pdf`. This looks like a superseded policy, which is a change in the source, not a broken link. The claims that cite 5160.05 need a legal review against 5160.06 before the record changes.
- **BOP FTC Application Guide** (Oct. 16, 2025) returns 404, and no link to it was found on the BOP First Step Act pages. Find the current location or a replacement before the record changes.

## Open: the site refuses automated requests (27)

These links are believed to work in a browser; the publisher blocks or drops automated requests. They need a manual check, or an official replacement where one exists.

- Republications that answer 403 or 202: Justia (6), OpenJurist (4), CourtListener opinion pages (3). The Barrett and Rogers official First Circuit links recorded by CourtListener no longer exist.
- constitution.congress.gov (3): 403.
- uscode.house.gov (6): HTTP 500 for these six sections, while 32 other sections opened. GovInfo's copy of the code opened as an alternative, but it is the annual edition, not the current preliminary text.
- Third Circuit opinion archive (4) and Seventh Circuit rules PDF (1): the server closes the connection.

## Also found

- **Carmona v. BOP, 243 F.3d 629 (2d Cir.)**: CourtListener dates the decision 2001-10-25; this record says 2001-03-20. Check the reporter.
- A redirect to an error page used to count as "opened". The checker now treats it, and a web page returned for a PDF request, as a failure. The next full run may therefore report a few more failures than before.
