---
module_id: MOD-EXAMPLES-INDEX
title: Worked Classification Examples
stage: auxiliary/examples
status: verified_with_limitations
last_verified: 2026-08-25
---

# Worked Classification Examples

These examples demonstrate record selection and route classification. They do not decide a real case, predict relief, or replace current circuit and local-law research. Expected IDs are retrieval controls, not canned answers.

## Example 1: What are the Rule 33 filing periods and what event starts them?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-RULE-33-NEW-TRIAL`
- Expected claims: `CLM-R33-003`, `CLM-R33-005`, `CLM-R33-006`, `CLM-R33-007`
- Expected authorities: `AUTH-FRCRIM-P-33`, `AUTH-FRCRIM-P-45`
- Facts still required: verdict or finding date, ground asserted, filing date, court closure or electronic-filing facts.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 2: When does a later § 2255 filing require court-of-appeals authorization?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-2255-LATER-FILINGS-CLASSIFICATION-AUTHORIZATION`, `MOD-2244-2255-SUCCESSIVE-GATEKEEPING`
- Expected claims: `CLM-SOS-001`, `CLM-SOS-025`
- Expected authorities: `AUTH-USC-28-2244`, `AUTH-USC-28-2255`, `AUTH-SCOTUS-MAGWOOD-561-US-320`
- Facts still required: judgment attacked, all prior applications and dispositions, claim ripeness, new judgment or resentencing history.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 3: Who is the proper respondent and what district is ordinarily proper for a core federal § 2241 custody challenge?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-2241-FILING-JURISDICTION-RESPONDENT-EXHAUSTION`
- Expected claims: `CLM-2241F-011`, `CLM-2241F-012`, `CLM-2241F-015`
- Expected authorities: `AUTH-SCOTUS-RUMSFELD-PADILLA-542-US-426`, `AUTH-USC-28-2241`
- Facts still required: custody challenged, physical location at filing, custodian, transfer history, whether custody is core or noncore.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 4: Does a federal prisoner need a certificate of appealability for an ordinary federal-process § 2241 appeal?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-2241-APPEAL-AND-RELIEF`
- Expected claims: `CLM-2241-001`, `CLM-2241-003`, `CLM-2241-004`
- Expected authorities: `AUTH-USC-28-2253`, `AUTH-CA3-BRUCE-868-F3D-170`
- Facts still required: source of detention, actual proceeding, whether the appeal is from a § 2255 proceeding or state-process detention.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 5: How is current federal good-conduct time different from time served and when can it be earned?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-GOOD-CONDUCT-TIME`
- Expected claims: `CLM-GCT-001`, `CLM-GCT-002`, `CLM-GCT-003`, `CLM-GCT-005`
- Expected authorities: `AUTH-USC-18-3624`, `AUTH-CFR-28-523-20`
- Facts still required: sentence and aggregation record, offense and sentence dates, disciplinary compliance, BOP computation.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 6: What is the difference between earning First Step Act time credits and applying them to prerelease custody or supervised release?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-FIRST-STEP-ACT-TIME-CREDITS`
- Expected claims: `CLM-FTC-004`, `CLM-FTC-005`, `CLM-FTC-009`
- Expected authorities: `AUTH-USC-18-3632`, `AUTH-USC-18-3624`, `AUTH-CFR-28-523-SUBPART-E`
- Facts still required: conviction statutes, risk assessments, program history, earned balance, application eligibility and projected release record.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 7: What is the defendant-motion gate for compassionate release under § 3582(c)(1)(A)?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-SECTION-3582-REMEDY-ROUTER`
- Expected claims: `CLM-3582-008`
- Expected authorities: `AUTH-USC-18-3582`
- Facts still required: warden receipt date, request contents, administrative appeals, motion grounds, controlling circuit issue-presentation law.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 8: What must be established before a sentence can be reduced under § 3582(c)(2)?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-SECTION-3582-REMEDY-ROUTER`
- Expected claims: `CLM-3582-018`, `CLM-3582-019`
- Expected authorities: `AUTH-USC-18-3582`, `AUTH-USSG-2025-1B1-10`, `AUTH-SCOTUS-DILLON-560-US-817`
- Facts still required: original guideline calculation, amendment, § 1B1.10(d) listing, amended range, applicable statutory minimum.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 9: How is First Step Act § 404 eligibility classified without promising plenary resentencing?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-FIRST-STEP-ACT-SECTION-404`
- Expected claims: `CLM-FSA404-001`, `CLM-FSA404-004`, `CLM-FSA404-007`
- Expected authorities: `AUTH-PL-115-391-SEC-404`, `AUTH-SCOTUS-CONCEPCION-597-US-481`, `AUTH-SCOTUS-TERRY-593-US-486`
- Facts still required: offense statute and date, penalty subsection, prior § 404 ruling, sentence package, controlling circuit procedure.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 10: What must be checked before characterizing an internet or social-media supervised-release condition as valid or invalid?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-SUPERVISED-RELEASE-CONDITIONS-REENTRY`
- Expected claims: `CLM-SRCOND-003`, `CLM-SRCOND-004`
- Expected authorities: `AUTH-SCOTUS-PACKINGHAM-582-US-98`, `AUTH-USC-18-3582-3583`
- Facts still required: condition text, record support, offense relationship, duration, approval mechanism, controlling circuit law.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Example 11: What are the ordinary BOP administrative-remedy steps and why does completion not answer every § 2241 exhaustion question?

**Classification task.** Retrieve the expected modules, then read the complete atomic claims and their authority limitations together.

- Expected modules: `MOD-BOP-ADMINISTRATIVE-REMEDIES-REVIEW`
- Expected claims: `CLM-BOPAR-003`, `CLM-BOPAR-007`, `CLM-BOPAR-016`
- Expected authorities: `AUTH-CFR-28-542`, `AUTH-USC-28-2241`
- Facts still required: event and response dates, every submission and rejection, same issue at every level, controlling circuit exhaustion rule, requested relief.
- Safe output: identify the controlling source and route, state the missing facts and circuit limits, and avoid an individual outcome until the full record is verified.

## Anti-example: attractive shorthand

A flowchart label such as “file § 2241,” “use compassionate release,” “second petition,” or “credits apply” is never a complete conclusion. The correct response identifies the judgment or agency action, custody and district, vehicle, statutory gate, deadline, record, controlling circuit, local rule, proof, remedy, appeal route, and every unverified dependency.
