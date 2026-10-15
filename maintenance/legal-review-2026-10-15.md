# Legal review drafts: October 15, 2026

Four claims were marked superseded because a source they rely on changed after the August 2026 review. **Status: approved by the owner on October 15, 2026 and applied** to the claim records and modules, with new authority records for PS 5160.06, 91 FR 55740 and *Miles v. Bowers*. Each edit is recorded in `manifest/revisions.json`.

Every source quoted below was read in full on October 15, 2026, from the official publisher, through the repository's probe workflow or the CourtListener API.

## Sources read

**BOP Program Statement 5160.06**, *Designation of State Institutions for Service of Federal Sentence* (Sept. 3, 2026). <https://www.bop.gov/policy/progstat/5160_006.pdf>, all 13 pages. Rescinds PS 5160.05 (Jan. 16, 2003). Key passages:

- § 1(a): designation is made "either determining that such a designation is based on the Order, recommendation, or expressed intention of the federal court for the federal sentence to run concurrently with a state sentence, or by determining that a designation is appropriate after reviewing the five factors under 18 U.S.C. § 3621(b)."
- § 2(b): "Following the United States Supreme Court's decision in Setser v. United States, 566 U.S. 231 (2012), the Bureau does not have the authority to independently determine whether an inmate's sentence should run consecutively or concurrently with another sentence under 18 U.S.C. § 3621(b)."
- § 5(d): "the Bureau considers an inmate's request for credit toward a federal sentence for time spent in state custody and credited to a state sentence, as a request for a nunc pro tunc designation."
- § 5(d)(1): "there is no obligation under Barden for the Bureau to grant the request by designating a state institution retroactively as the place to serve the federal sentence."
- § 5(d)(5): the designation decision "effectively determines when the federal sentence commences pursuant to 18 U.S.C. § 3585(a)."
- § 5(d)(8): "The Bureau will not allow a concurrent designation if the federal sentencing court has already made a determination regarding the order of service of sentence."
- § 8(b): a nunc pro tunc designation "allows the federal sentence to commence under 18 U.S.C. § 3585(a)."

**18 U.S.C. § 3585** (United States Code, 2024 edition, GovInfo). <https://www.govinfo.gov/content/pkg/USCODE-2024-title18/pdf/USCODE-2024-title18-partII-chap227-subchapD-sec3585.pdf>

- (a): "A sentence to a term of imprisonment commences on the date the defendant is received in custody awaiting transportation to, or arrives voluntarily to commence service of sentence at, the official detention facility at which the sentence is to be served."
- (b): credit for prior official detention is given for time "that has not been credited against another sentence."

**First Step Act Time Credits—Revisions**, 91 FR 55740 (Aug. 31, 2026), interim final rule, effective Sept. 30, 2026. <https://www.federalregister.gov/documents/full_text/text/2026/08/31/2026-17752.txt>; PDF <https://www.govinfo.gov/content/pkg/FR-2026-08-31/pdf/2026-17752.pdf>

- Amended § 523.42(a): "An eligible inmate begins earning FSA Time Credits after the inmate's term of imprisonment commences."
- Removed clause: commencement on "the date the inmate arrives or voluntarily surrenders at the designated Bureau facility where the sentence will be served."
- From the preamble: "this change does not mean that every eligible inmate will automatically begin earning Time Credits immediately after their sentence is imposed ... the inmate must still complete evidence-based recidivism reduction (EBRR) programming or productive activities assigned to them."

***Miles v. Bowers***, No. 25-1291 (1st Cir. Apr. 27, 2026), CourtListener opinion 11316033. The rule cites it as 173 F.4th 372; CourtListener does not yet carry the reporter citation, so cite by docket number until the reporter citation is confirmed. Verified quote: "the view expressed in the regulation of when a sentence commences plainly conflicts with the text of the FSA."

**BOP Federal Time Credit Application Guide** (announcement updated Oct. 16, 2025). Live on bop.gov at least through 2026-08-25. The Wayback Machine recorded HTTP 404 on 2026-10-01. Last good capture: <https://web.archive.org/web/20260619204331/https://www.bop.gov/news/20251016-federal-time-credit-application-guide.jsp>. No withdrawal notice was found. The capture is the announcement page; the guide document itself was not captured.

## Drafts

### CLM-BOPSC-009 (module: BOP designation and sentence computation)

Current (superseded):

> Program Statement 5160.05 recognizes Bureau authority to designate a state institution for concurrent service when consistent with the federal sentencing court's intent or criminal-justice goals, but it describes a discretionary § 3621(b) determination rather than automatic retroactive credit.

Proposed:

> Program Statement 5160.06 provides for designating a state institution for concurrent service of a federal sentence when the federal sentencing court has ordered, recommended, or expressed that intent, or when the Bureau finds designation appropriate after reviewing the five factors in 18 U.S.C. § 3621(b). The Bureau must consider an inmate's nunc pro tunc request but is not obliged to grant it, and it will not designate concurrently where the sentencing court has already determined the order of service. [BOP PS 5160.06 §§ 1(a), 5(d)(1), 5(d)(8)](https://www.bop.gov/policy/progstat/5160_006.pdf)

Authorities: replace AUTH-BOP-PS-5160-05 with a new AUTH-BOP-PS-5160-06; keep AUTH-USC-18-3621.

### CLM-BOPSC-023 (same module)

Current (superseded):

> A retroactive or nunc pro tunc state-facility designation is a § 3621(b) placement determination under Bureau policy, not a second award of the same custody days under § 3585(b).

Proposed:

> Under Program Statement 5160.06, the Bureau treats a request for federal credit for time spent in state custody and already credited to a state sentence as a request for a nunc pro tunc designation: a placement decision that sets when the federal sentence commences under 18 U.S.C. § 3585(a). It is not credit for prior custody, which § 3585(b) allows only for time not credited against another sentence. [BOP PS 5160.06 §§ 5(d), 5(d)(5), 8(b)](https://www.bop.gov/policy/progstat/5160_006.pdf); [18 U.S.C. § 3585](https://www.govinfo.gov/content/pkg/USCODE-2024-title18/pdf/USCODE-2024-title18-partII-chap227-subchapD-sec3585.pdf)

Authorities: AUTH-BOP-PS-5160-06 (new), AUTH-USC-18-3585.

### CLM-FTC-008 (module: First Step Act time credits)

Current (superseded):

> For the current regulatory period, an eligible inmate begins earning only after the term of imprisonment commences, which the regulation identifies as arrival or voluntary surrender at the designated Bureau facility.

Proposed:

> Since September 30, 2026, 28 C.F.R. § 523.42(a) provides that an eligible inmate begins earning FSA Time Credits after the term of imprisonment commences. The amendment removed the earlier clause that tied commencement to arrival or voluntary surrender at the designated Bureau facility, which courts had held conflicts with the First Step Act. A sentence commences under 18 U.S.C. § 3585(a) when the defendant is received in custody awaiting transportation to, or arrives voluntarily at, the official detention facility. Earning still requires successful participation in assigned programs or productive activities. [91 FR 55740 (Aug. 31, 2026)](https://www.govinfo.gov/content/pkg/FR-2026-08-31/pdf/2026-17752.pdf); [Miles v. Bowers, No. 25-1291 (1st Cir. Apr. 27, 2026)](https://www.courtlistener.com/opinion/10848657/miles-v-bowers/); [18 U.S.C. § 3585(a)](https://www.govinfo.gov/content/pkg/USCODE-2024-title18/pdf/USCODE-2024-title18-partII-chap227-subchapD-sec3585.pdf)

Authorities: AUTH-CFR-28-523-SUBPART-E (update its source to the amended text), a new AUTH-FR-91-55740, a new AUTH-CA1-MILES-BOWERS-2026, and AUTH-USC-18-3585.

### CLM-BOPPRE-018 (module: prerelease custody and home confinement)

Current (superseded):

> The Bureau's October 16, 2025 Federal Time Credit Application Guide describes its current public operational framework for maximizing lawful application of credits, but it cannot enlarge or narrow the governing statute and regulation.

Proposed:

> The Bureau's Federal Time Credit Application Guide, announced October 16, 2025, was an informational explanation of how time credits are earned, calculated, and applied. The Bureau removed it from bop.gov in 2026 without a published notice, and an archived copy of the announcement remains. Guidance of this kind cannot enlarge or narrow the governing statute and regulation. [BOP announcement, archived June 19, 2026](https://web.archive.org/web/20260619204331/https://www.bop.gov/news/20251016-federal-time-credit-application-guide.jsp)

Authorities: AUTH-BOP-FTC-APPLICATION-GUIDE-2025 (now archived guidance), AUTH-USC-18-3624.

## Not changed

- **Carmona v. BOP, 243 F.3d 629 (2d Cir.)**: decided March 20, 2001, Docket No. 00-2316, per the Caselaw Access Project reporter data (<https://static.case.law/f3d/243/cases/0629-01.json>). The record already says 2001-03-20. CourtListener's 2001-10-25 date is its own error.
- **Other claims citing 28 C.F.R. part 523, subpart E** (CLM-FTC-010, CLM-FTC-013, CLM-BOPDDR-004, CLM-BOPDDR-028, CLM-BOPPRE-017): they rest on §§ 523.43, 523.44(a)(2) and 523.44(c), which the rule did not change. They stay as they are; the authority's source should still move to the amended text.
