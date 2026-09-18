# CAPACITY CONNECT — SIH eleven-step demo guide

Document path: `app/CAPACITY_CONNECT_DEMO_GUIDE.md`. All five documentation artifacts are under `app/`, the supported location for this update.

## Safety, actors and prerequisites

This is an exact eleven-step rehearsal sequence, not a claim that the full browser demo has been executed. The supplied database and handler checks verify selected prerequisites; browser interaction and the complete cross-role workflow remain NOT_VERIFIED. Use only an authorized isolated demonstration database containing synthetic records. Do not run a destructive reset, reseed or test against production.

Existing role email identifiers:

| Demo actor | Role | Existing email address |
|---|---|---|
| System Administrator | Administrator | admin@capacityconnect.gov |
| Dr. Raj Sharma | Trainer | trainer@capacityconnect.gov |
| Anmol Kumar | Trainee / Weather Forecaster | trainee@capacityconnect.gov |

Passwords are supplied only through deployment-managed `CAPACITY_CONNECT_DEMO_PASSWORD` and must be obtained from the authorized demo administrator. No password value is included here. Do not display passwords, session values, recovery links or verification token values on slides or in logs. Do not assume reseeding rotates an existing account's password; have the authorized administrator validate access beforehand.

Use separate browser profiles for each role to avoid confusing session state. Confirm current course dates, trainer availability, approval/activity, enrollment, assessment deadline and attempts before the rehearsal. A historical eligible fit evaluation does not guarantee current availability.

Verified prerequisites from supplied evidence: all three named actors exist and are approved/active; Anmol's Velocity Interpretation has **Required 4, Current 2, Gap 2**; the corresponding saved learning path has nine steps; Dr. Raj has an eligible stored fit record at 90.0; a non-revoked existing certificate has a 64-character token; and the Doppler assessment has three competency-linked questions. The existing certificate is not evidence that the new Doppler assessment has already been passed.

## The eleven steps

### 1. Administrator — organizational need and affected trainee

Sign in as **System Administrator** through `/login`. Open Organizational Competency Map at `/admin/competencies`. Filter Subject to **Doppler Radar** and Competency to **Velocity Interpretation**, then apply filters. Select the competency card to inspect evidence and affected trainees; locate **Anmol Kumar**.

Show the organizational target, current measurement, gap and affected-trainee detail. For Anmol, expect **Required 4, Current 2, Gap 2** before the assessment. The interface may label required as “Target” and display organization-wide averages on cards; use Anmol's detail rather than claiming an aggregate always equals his individual values. Unmeasured people must remain explicitly unmeasured.

Evidence: the exact individual baseline is database-verified in supplied results. Filter/click behavior remains NOT_VERIFIED.

### 2. Administrator and trainer — Trainer Fit, explanation and assignment

Use **Find trainers** to open `/admin/trainer-fit`. Select the Doppler-related course **CC-NOW-204**, choose a valid window compatible with the trainer's availability, and run **Save / execute** in the recalculation form. Inspect **Dr. Raj Sharma** and expand **Five-factor arithmetic, covered competencies and eligibility failures**.

Show Trainer Fit Score, coverage, domain alignment, experience, qualification, observed effectiveness, covered/missing competencies, availability, capacity and eligibility explanation. The supplied stored evaluation is **90.0 / 100, eligible**; a fresh evaluation may legitimately differ. Policy defaults are coverage 40%, domain 25%, experience 15%, qualification 10%, effectiveness 10%; these are not official SIH weights or AI confidence.

Use **Revalidate & assign individual** only if currently eligible. If coverage is insufficient, inspect `/admin/team-matches` for a complementary proposal; do not portray a proposal as an assignment. In Dr. Raj's separate session, confirm the course appears at `/trainer/courses`; inspect `/trainer/availability` and the Doppler questionnaire at `/trainer/assessments/create`. If blocked, stop and resolve authorized prerequisites rather than bypassing eligibility.

Evidence: fit arithmetic, stored eligibility and trainer studio loading are supplied. Fresh assignment and trainer confirmation remain NOT_VERIFIED.

### 3. Trainee — personal gap and persistent learning path

Sign in as **Anmol Kumar**. Open `/trainee/competencies`, inspect **Velocity Interpretation** under Doppler Radar and show **Required 4, Current 2, Gap 2** again. Open **Saved learning paths** at `/trainee/paths` and find **Velocity Interpretation: development pathway**.

Show the saved **nine-step** pathway. If no path exists in the isolated rehearsal database, return to the gap and use **Generate / start owned gap pathway**, then inspect the result; do not fabricate missing steps. Refresh and check that the same pathway remains. Confirm eligible step completion only after the underlying activity is done and prerequisites are satisfied.

Evidence: the nine-step record is database-verified. Browser refresh and complete progression remain NOT_VERIFIED.

### 4. Trainee — course, module and learning resources

Open `/trainee/learning`, select the assigned Doppler-related course and open the relevant module/resource. Review the available lesson, recorded lecture, presentation or study material and complete an actual learning activity. Use `/trainee/resources` as needed. Return to the pathway and use **Confirm eligible completion** where the activity satisfies the step.

Expected: progress reflects actual activity, not an invented percentage. Do not claim resource completion grants verified proficiency. Optional within this same learning step: open **CAPACITY AI · learning support**, select the enrolled course and demonstrate **Explain Concept** or **Summarize Resource**. Show the source register and model/fallback label; missing approved source text must remain explicit.

Evidence: AI endpoint and course context checks succeeded separately. Resource playback, deployed file persistence, browser AI output and path progression remain NOT_VERIFIED. Use non-sensitive approved demo content because public upload URL authorization is an INSECURE release blocker.

### 5. Trainee — formative adaptive practice

Open `/trainee/practice`, choose **Start / resume practice**, answer the available weak-competency questions and select **Submit formative answers**. Review explanations and any available difficulty/resource guidance. If no published question bank is available, show that limitation instead of presenting invented questions as database-backed practice.

Return to the competency view and confirm that practice alone has not changed verified mastery. Practice can guide development but cannot create an official result or award competency.

Evidence: formative isolation contracts passed. Complete adaptive difficulty transitions and browser persistence remain NOT_VERIFIED.

### 6. Trainee — official competency-linked assessment

Open `/trainee/assessments` and select **Doppler Radar competency assessment — SIH**. Review the deadline and remaining attempts, then take the assessment normally. Supplied database values are **15 minutes**, **maximum 3 attempts**, shuffled questions and **3 questions, all competency-linked**. Current deadline and remaining attempts must be checked live.

Submit within the server-enforced allowance. Open `/trainee/results` to show the score, pass/fail and saved result, then refresh to test persistence. Do not manipulate the timer or reveal protected answer keys during the demo. Do not claim displaying a timer proves server enforcement; adversarial timing, tampering and race tests belong in separate isolated tests.

Evidence: assessment configuration and authorized loading are verified by supplied checks. This attempt, result persistence and complete assessment security remain NOT_VERIFIED until executed.

### 7. Trainee — evidence, recalculation and changed gap

Return to `/trainee/competencies`, inspect Velocity Interpretation and review the evidence timeline after the valid official result. Look for the resulting competency-linked measurement, source reference, verification status and dates. Confirm that only qualifying verified evidence drives the updated measurement and gap.

**The post-assessment change depends on performance on competency-linked questions.** Passing the course overall does not guarantee Velocity Interpretation reaches 4. A qualifying measured level of 4 or greater can meet the required level; a lower result may leave a gap. Missing, pending or non-qualifying evidence must not be presented as mastery. Compare actual before/after values; do not promise a fixed jump from 2 to 4 or manually edit the level to make the demonstration look successful.

Evidence: baseline, qualifying-evidence and rubric contracts are supplied. A new official assessment-to-evidence transition remains NOT_VERIFIED.

### 8. Trainee — competency passport and provenance

Open `/trainee/passport`. Inspect the relevant competency, current verified level and its source/verification timeline. Cross-check against Step 7 and refresh. Show that a passport is an evidence-backed record, not a collection of self-reported skills or attendance badges.

Expected: the passport matches the actual qualifying result. If no new verified evidence exists, explain why the prior level remains rather than claiming an update. Evidence/source privacy must be preserved in screen sharing.

Evidence: passport UI and baseline records exist. New-result propagation and browser refresh remain NOT_VERIFIED.

### 9. Trainee and administrator — certificate request, issuance and QR

As Anmol, open `/trainee/certificates` and review readiness. **Only if current eligibility conditions are met**, request certification. As System Administrator, open `/admin/certifications`, review current eligibility and approve/issue using the applicable workflow. Return as Anmol to inspect the issued record and open its verification link/QR.

Use the application's generated verification link; do not construct one from a guessed certificate number. Open it in a separate public browser and scan the QR with a test device where available. Expect **VALID** only for a current non-revoked certificate. Any competency claims must be supported by linked evidence. An old course certificate must be clearly labeled as an existing record, not represented as newly earned Doppler certification.

If eligibility fails, demonstrate the truthful pending/ineligible state and explain the remaining requirement. Invalid/revoked verification tests must use separate isolated fixtures, not revoke a production certificate for presentation.

Evidence: distinct-token tests and one existing 64-character-token record are verified. New issuance, public lookup and physical QR scan remain NOT_VERIFIED.

### 10. Administrator — observed training effectiveness

As System Administrator, open `/admin/effectiveness`, select the course and use **Refresh observed effectiveness snapshot** via **Save / execute**. Review participants, completion, verified pre/post measurements, observed competency improvement, official assessment performance and learner feedback.

Explain that pre/post observations must be verified and chronological. Missing pairs or feedback must remain missing, not zero or fabricated impact. Show actual changed values only if Steps 6–8 produced qualifying evidence. State explicitly: **observed improvement is not proof of causal training impact**.

Evidence: verified-pairing contracts passed. A refreshed snapshot from this full rehearsal remains NOT_VERIFIED.

### 11. Administrator and trainer — effectiveness in subsequent Trainer Fit

Return to `/admin/trainer-fit`, recalculate for the appropriate course/window and inspect the observed-effectiveness factor under the configured policy. Compare the new evaluation with the prior saved evaluation without rewriting its history. As Dr. Raj, inspect permitted cohort performance/feedback at `/trainer/performance` and `/trainer/feedback` to close the cross-role narrative.

Explain how available observed effectiveness may inform a later fit evaluation, while evidence coverage, qualification, experience and availability/capacity still matter. Do not guarantee the total score increases; absent or unchanged qualifying observations may leave it unchanged. A recommendation remains advisory to the allocation decision.

Evidence: fit arithmetic and the stored eligible record exist. Full effectiveness-to-fit propagation and trainer browser confirmation remain NOT_VERIFIED.

## Rollback and reset guidance

Have the authorized demo administrator prepare a disposable, isolated demo database and preserve a clean baseline before rehearsal. Rerun the existing **idempotent seed** only in that isolated demo database to establish the demonstration prerequisites. Idempotent seeding avoids duplicate setup; it is **not** a general undo mechanism and must not be assumed to erase completed attempts, grades, evidence, allocations or certificates.

For a genuinely clean reset, restore the isolated pre-demo baseline or replace the disposable demo database through the authorized management process, then rerun the idempotent seed there. Recheck actor identity, **4/2/2**, the nine-step path, current dates/availability, enrollment and assessment attempts before restarting Step 1. Never manually falsify grades or verified evidence to restore a presentation value. Never alter production to replay the demo. This documentation update performs no reset or database writes.

## Rehearsal sign-off limits

Record actual observations per step, including blockers and deviations. Do not mark a step verified merely because its route exists. Browser interaction, concurrency, real email delivery, real upload persistence across deploy and production deployment remain NOT_VERIFIED in the supplied evidence. Do not send real notification emails during rehearsal without explicit authorization and a controlled recipient.

The client-managed non-HttpOnly session cookie and public upload URL authorization remain **INSECURE release blockers**. Recovery delivery and complete session revocation remain gaps. Successful rehearsal would not, by itself, establish production readiness.
