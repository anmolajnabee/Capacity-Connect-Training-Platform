# CAPACITY CONNECT — Test report

Document path: `app/CAPACITY_CONNECT_TEST_REPORT.md`. This artifact is placed under `app/` because repository-root writing is not supported for this update.

## Provenance

This report records actual execution evidence supplied in this session, including prior repair runs. No commands, tests, provider calls, database checks or browser actions were newly executed during this documentation-only update. Source inspection and test existence are not substitutes for execution. Timings below are historical runner observations, not performance benchmarks. No production readiness is claimed.

## Automated suite results

| Run | Total discovered/run | Passed | Skipped | Failures | Errors | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| Baseline | 24 | 23 | 1 | 0 | 0 | Successful baseline; skipped test included in total |
| Intermediate demo-catalog run | 35 | 33 | 1 | 1 | 0 | Historical failed run: one test was skipped and one demo-catalog assertion failed because account metadata still exposed a password field; repaired before final suite |
| Final post-repair | 47 | 46 | 1 | 0 | 0 | Successful final suite; disposable-database email test still skipped |

The baseline runner reported approximately 0.090 seconds. Historical intermediate runs reported approximately 0.090–0.091 seconds. The final supplied run reported 47 total, 46 passed, 1 skipped, 0 failures and 0 errors. These short unit/contract runs do not establish end-to-end application speed.

The historical 35-test run comprised **33 passed, 1 skipped, 1 failure and 0 errors**. The failure was the demo-catalog assertion because account metadata still exposed a password field; the skipped test was not run and is not counted as passed. After repair, the same assertion passed, and the final supplied 47-test suite had **46 passed, 1 skipped, 0 failures and 0 errors**. Thus, “no failures” applies to the baseline and final successful runs, not every historical experiment.

### Final supplied suite result

The final suite is **47 total: 46 passed, 1 skipped, 0 failures, 0 errors**. The skipped disposable-database email scope/duplicates/deadlines/admin-guards test remains historical and is not counted as passed. The final repair coverage additionally verifies private resource storage round trips, bounded filenames and paths, 50 MB read/write limits, fresh role-scoped download authorization, no frontend stored filenames, removal of direct `rx.get_upload_url`, and separation of resource completion from certificate issuance.

Resource completion now recalculates progress/completion only. Certification proceeds through trainee readiness/request and administrator approve/issue with live eligibility revalidation.

### Coverage evidenced by the passing suite

- Evidence-bound gaps: current measurement must match verified evidence; unmeasured is not silently converted to zero.
- Registry reads: source contracts guard read-only behavior and scoped parameters.
- Practice separation: formative data does not expose official question keys or write official results/verified competency.
- Effectiveness: verified chronological pre/post pairing, with practice excluded.
- Trainer Fit: weighted arithmetic; team greedy coverage and no empty members.
- Notifications: ownership binding, deterministic event identities, recipient rules and email validation.
- Announcements/email: bounded escaped names, fixed destinations, future-publication checks, retry classification and login timestamp order.
- Session checks: tampered, expired, future and legacy tokens; fresh-role checks rather than cached identity trust.
- Upload validation: text, format mismatches, size boundaries, Office structure and macro rejection, external URL policy.
- Certificates/evidence: distinct 64-character verification tokens and score-to-level rubric boundaries.
- AI: explicit bounded database-grounded fallback and missing-key behavior without network access.
- Worker behavior: normal cancellation propagates without inappropriate error logging or provider/database work; no authorized sender produces a blocked outcome in mocked testing.
- Final credential-exposure and security regression contracts: demo-password data cannot enter frontend portal options; server-side assessment locking, expiry, enrollment, persisted-option scoring and competency linkage; draft-only mutation; and token-only certificate lookup.

Many checks inspect source or use mocked dependencies. They do not prove all authorization, persistence, scoring or transport behavior in a deployed application.

### Skipped test

The disposable-database email scope/duplicates/deadlines/admin-guards test remains skipped because it requires a migrated disposable database and must never run against production. A skip is not a pass.

The earlier audit additionally records a narrower, rolled-back managed-database transaction check: the first assignment notice enqueue selected one eligible recipient, and repeating the same logical event inserted zero duplicate deliveries. That check does not replace the skipped test or demonstrate concurrent deduplication.

## Subsequent live protected-download handler check

With valid trainer and trainee sessions bound to the handlers, requests for a nonexistent resource ID were denied for both roles with the same generic message: **“That resource file is unavailable.”** The response did not disclose a path, stored filename or other file-location detail.

This is a bounded negative handler check for one nonexistent ID and two valid session contexts. It is not exhaustive IDOR coverage, and it does not validate deployed-download behavior, durable storage across deployment, browser delivery or production authorization.

## Live Gemini evidence

Status: PARTIALLY_IMPLEMENTED for overall CAPACITY AI verification.

The supplied live `gemini-3.6-flash` endpoint probe succeeded after using a realistic output token budget:

- A 20-token attempt produced empty text and failed its assertion.
- A 40-token attempt truncated output and reported a maximum-token finish.
- A 200-token attempt returned the expected `CAPACITY_AI_OK` response and a normal stop finish.

This is a real successful endpoint call, not a mocked transport test. Earlier low-budget failures are retained as diagnostic history. It does not verify all six contextual actions, factual correctness, source fidelity, privacy defenses, sustained availability or the browser AI experience. Web research about model availability is not additional runtime evidence.

## Managed-database observations

These checks followed the supplied demo normalization run. Earlier probes did not find the required named actors and showed older demonstration identities; they must not be confused with the final state. Later checks confirmed:

| Check | Actual observed result | What it does not prove |
|---|---|---|
| Required actors | System Administrator, Dr. Raj Sharma and Anmol Kumar present, approved and active in their respective roles | Interactive login or privilege isolation |
| Initial competency measurements | Anmol: Radar Fundamentals 4, Velocity Interpretation 2, Data Interpretation 2; verified baseline records | Independent real-world evaluation of demo actors |
| Velocity gap | Required 4, current/baseline 2, gap 2; recorded as in progress | Post-assessment browser transition |
| Learning path | Velocity Interpretation development pathway exists with 9 persisted steps | Full step progression or browser refresh behavior; other listed paths had different step counts |
| Trainer Fit | Dr. Raj Sharma has an eligible stored evaluation for the Doppler-related course, score 90.0 | Current eligibility for arbitrary dates or successful assignment |
| Certificate | Anmol has a non-revoked existing certificate with a 64-character verification token | New Doppler issuance, token secrecy in every surface, browser verification or camera scan |
| Official Doppler assessment | Open “Doppler Radar competency assessment — SIH”; 15 minutes; maximum 3 attempts; shuffle enabled; 3 questions, all competency-linked | Successful attempt submission, scoring tamper resistance or evidence award |
| Attempt expiry | Database observation confirms an expiry requirement | Complete deadline/race correctness |

These are real reads of persistent synthetic demo records, not claims of real operational outcomes. No actual verification token or certificate credential is reproduced. Database read success is narrower than write/reload durability, restart durability or production migration acceptance. Historical diagnostic warnings are not deployment certification.

## Role-gated handler evidence

The supplied authorized-identity checks succeeded for:

| Role / handler area | Observed result | Boundary |
|---|---|---|
| Trainee assessments | Assessments loaded with no reported application error; 3 returned | Not an assessment attempt or browser login |
| Trainer studio | Assessments loaded with no reported application error; 2 returned | Not author/edit/publish verification |
| Admin analytics | Handler completed without reported application error | Not chart-rendering or aggregate-accuracy acceptance |
| AI course context | Authorized courses loaded without reported application error; 3 returned | Not all contextual generation actions |

These positive checks used bound test identities. They do not prove every unauthorized role, foreign record ID or changed membership is rejected.

## Explicitly outstanding validation

| Area | Status | Required evidence |
|---|---|---|
| Browser interaction | NOT_VERIFIED | Complete eleven-step demo, form actions, navigation, negative flows and refresh checks |
| Concurrency | NOT_VERIFIED | Duplicate attempts/submissions, enrollment capacity, trainer allocation, issuance and email dispatch races |
| Real email delivery | NOT_VERIFIED | Authorized sender, controlled recipient, provider acceptance and independently confirmed receipt; acceptance alone is insufficient |
| Private storage persistence across deploy | NOT_VERIFIED | Protected download before and after restart/deploy, ownership and membership changes; local private round-trip and 50 MB bounds are already covered |
| Production deployment | NOT_VERIFIED | Authorized production acceptance, startup/restart and operational validation; imports and handler tests are insufficient |
| Accessibility and responsiveness | NOT_VERIFIED | Keyboard, screen reader, contrast, reduced motion and 360/390/768/1024/1440-pixel checks |
| Full assessment security | NOT_VERIFIED | Server deadline/timer/attempt enforcement, answer-key isolation, foreign-option and client-score tampering |
| Certificate round trip | NOT_VERIFIED | Eligibility, request/review/issue, invalid/revoked verification and QR scan |
| AI adversarial privacy | NOT_VERIFIED | Cross-course leakage and prompt-injection tests; factual review of every action |
| Complete regression/build acceptance | NOT_VERIFIED | Full browser/build acceptance and all scoped integration tests; no build/deployment claim follows from test discovery |

## Conclusion

Bounded tests and live checks provide useful evidence, but the client-managed non-HttpOnly session cookie remains the explicit INSECURE release blocker. Protected resource downloads are authorization-scoped by fresh server events, while deployment durability, large-file delivery, malicious-content scanning and post-deploy persistence remain NOT_VERIFIED. Password recovery delivery and full session revocation remain gaps. No production-readiness or complete end-to-end security claim is justified.
