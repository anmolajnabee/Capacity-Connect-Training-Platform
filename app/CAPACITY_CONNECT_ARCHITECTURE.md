# CAPACITY CONNECT — Functional design overview

Document path: `app/CAPACITY_CONNECT_ARCHITECTURE.md`. This document is under `app/`, the supported artifact location for this documentation-only update.

## Scope

This is a concise, non-sensitive conceptual overview of the product and its trust boundaries, not a disclosure of internal system architecture, internal structures or deployment configuration. It contains no secrets, connection information or deployment internals. Application code is unchanged. Implementation evidence is bounded; production readiness is not claimed.

## Competency-driven business flow

Organizational need → required competencies → evidence-bound gap → affected trainees → explainable Trainer Fit → eligible trainer or complementary team → training → learning resources → formative practice → official assessment → verified competency evidence → updated current competency and gap → competency passport → observed training effectiveness.

Requirements and demonstrated proficiency are distinct. A required level states the organizational target; current level requires qualifying evidence. An unmeasured baseline must remain unmeasured rather than being treated as zero. Self-reported skills, course attendance, resource completion and practice alone do not establish official mastery.

Trainer Fit is an explainable recommendation, not authorization or guaranteed availability. Availability and capacity must be revalidated before assignment. A team proposal describes coverage and remaining gaps; it is not proof of a completed allocation. Scoring weights are application policy defaults, not official SIH-mandated weights.

Learning paths describe ordered development activities. Their progress must reflect completed activities rather than a visual-only progress indicator. Official assessment is separate from formative practice and must derive scores and competency evidence from authorized submissions, never client-provided scores or AI judgments.

The passport summarizes evidence-backed competency and provenance. Effectiveness compares verified chronological observations and training activity; it reports observed improvement, not causal proof that training caused the change.

## Role boundaries

- **Trainee:** own professional record, eligible learning, own attempts, assignments, feedback, development gaps, paths, practice, evidence, passport, certificate requests and notices.
- **Trainer:** own professional expertise, authorized courses and cohorts, approved content/questionnaire work, assigned grading, availability and permitted feedback/performance views.
- **Administrator:** account decisions, roles, organizational requirements, training allocation, course/assessment/certification oversight, competency coverage and operational reports.
- **Public visitor:** public information and deliberately limited certificate verification, not private learner records or protected learning files.

Navigation visibility is not authorization. Each sensitive action must independently respect identity, current approval/activity, ownership and course scope. The positive handler checks supplied in this session do not establish complete negative-access coverage.

## Framework and persistence concepts

At the framework level, Reflex pages present the user interface, state events coordinate user actions, and service logic performs domain operations. Transient form/loading state is different from durable business records. Managed PostgreSQL is the persistent record store; a state field or a displayed value is not itself evidence of database persistence.

The supplied database checks establish the existence of selected persisted demonstration records, including the nine-step Velocity path. They do not establish every mutation, browser refresh, restart, concurrency or deployment behavior. Detailed internal topology, module relationships, schemas and operational configuration are intentionally outside this document.

## External assistance and messaging boundaries

### Gemini: advisory only

CAPACITY AI provides contextual learning assistance: explain a concept, summarize approved material, explain a mistake without disclosing protected official answers, draft practice questions, recommend a resource and suggest a next step. Context must be authorized and minimized before any provider request. Resource text and generated output remain untrusted.

Gemini must not decide access, issue certificates, write official grades or award verified competency. Generated formative drafts require trainer review before publication. An explicit database-grounded fallback is not represented as a successful model response. The supplied endpoint probe and authorized-course-context check succeeded; full contextual and adversarial browser behavior remains NOT_VERIFIED.

### Resend: notification delivery boundary

A durable outbox separates business notification intent from external transport. Sending is not the business transaction itself. Scoped recipients, deduplication and bounded retry behavior are required; uncertain provider acceptance must be reconciled rather than blindly resent.

A provider-accepted message is not proof of inbox delivery or a read receipt. In-app read receipts are separate from email outcomes. Recovery secrets are not part of the ordinary notification flow. Real email delivery remains NOT_VERIFIED; the prior audit's sender-authorization prerequisite has not been cleared by supplied evidence.

## Certificate verification concept

An issued certificate has a human-readable display identity and a separate unpredictable verification token. The verification link carries that token; the QR encodes the verification link. Verification must consult current status and expose only intended public certificate information, including revocation status and appropriate evidence context.

A certificate number alone must not be assumed to provide secure lookup authorization. A valid course certificate without linked normalized evidence is not proof of competency mastery. The supplied evidence confirms a 64-character token and distinct-token unit tests, not an end-to-end QR scan, new issuance or revoked-token browser test. No token values are included here.

## Current assurance limits

- INSECURE release blocker: client-managed non-HttpOnly session cookie.
- INSECURE release blocker: public upload URL authorization.
- PARTIALLY_IMPLEMENTED: secure recovery delivery and full session revocation remain gaps.
- NOT_VERIFIED: complete browser workflow, concurrency, real email delivery, protected upload persistence across deploy and production deployment.

The companion final audit, security audit and test report distinguish source-level implementation from executed evidence. This functional overview is not a release approval.
