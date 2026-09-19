# CAPACITY CONNECT — Architecture and operational boundaries

Document path: `app/CAPACITY_CONNECT_ARCHITECTURE.md`.

## Scope and assurance posture

This is a non-sensitive conceptual and operational guide. It intentionally omits credentials, database addresses, tokens, internal deployment topology and private implementation details. It records boundaries and evidence limits; it is not a production-readiness approval. Application code is unchanged by this documentation update, and this session did not boot the browser runtime.

## Conceptual system flow

```text
Frontend/UI
    ↓
Reflex State
    ↓
Domain Services
    ↓
Managed PostgreSQL
    ↓
Authentication
    ↓
Authorization
    ↓
External services
```

This is a conceptual dependency view, not a literal request pipeline. Authentication and authorization are cross-cutting controls: they protect UI routes, state events, services and data access rather than being downstream stages after the database. External services include advisory AI and notification transport; neither is authoritative for identity, access, grades, certificates or competency.

## Environment variables and secret handling

Names and purposes only are listed here; no values belong in this document.

- `REFLEX_DB_URL`, `REFLEX_ASYNC_DB_URL`, `DATABASE_URL`: managed database URL aliases used by the application/runtime.
- `CC_SESSION_SECRET`: optional dedicated server-side session-signing secret. When absent, the application derives a signing key from the managed-database configuration as a fallback; this does not resolve the client-managed cookie limitation.
- `GOOGLE_API_KEY`: provider credential for CAPACITY AI.
- `GEMINI_BASE_URL`: optional Gemini-compatible endpoint override.
- `RESEND_API_KEY`: provider credential for outbound notification transport.
- `RESEND_FROM_EMAIL`: optional authorized sender identity.
- `CC_PUBLIC_URL`: approved public base URL used for safe notification links and verification links.
- `REFLEX_ENV`: runtime environment classification.
- `CC_PRIVATE_UPLOAD_DIR`: private resource storage directory. Production must set this to durable non-public storage with least-privilege filesystem access; no resource bytes should be served through Reflex’s public upload directory.

Secrets belong in deployment or local secret settings, never in browser state, source control, logs, slides or documentation. This document contains no secret values.

## Database setup and migrations

Managed PostgreSQL is provisioned by the hosting/project workflow. ORM models in `app/models.py` define the desired application schema. Migration history is held under the protected `db_migrations` directory. Migrations are applied by the managed migration workflow; do not perform ad-hoc `CREATE` or `ALTER` operations, manually initialize tables, or treat application startup as a migration mechanism. A successful model read or seeded record does not prove that every mutation, constraint, transaction race or deployment connection has been verified.

## Seed and repair process

The seed process is idempotent. The three exact demonstration actors use the fixed demonstration-only shared password `Demo@1234`: `admin@capacityconnect.gov`, `trainer@capacityconnect.gov` and `trainee@capacityconnect.gov`. Reconciliation changes only those exact email addresses and does not modify normal users. It must not invent, print or store a password in frontend metadata. Demo records are created only when the user database is empty. The normalized v2 repair is also idempotent and is intended to repair or normalize the isolated demonstration baseline without duplicating records. Production data must never be reset or reseeded for a demo. Seeding is not an undo mechanism for attempts, grades, evidence, allocations or certificates; use an authorized disposable database or restored baseline for rehearsal.

## Local run guidance

At a conceptual command level:

1. Configure a development PostgreSQL database and the required local secrets without placing values in the repository.
2. Apply the managed migration set through the approved migration workflow.
3. Start the Reflex application with the normal development command, for example `reflex run`.
4. Exercise the supplied test suite after startup and record actual results separately from source inspection.

This session did not boot the browser runtime. Browser behavior, concurrency, durable uploads, provider delivery and a complete cross-role rehearsal therefore remain evidence-limited.

## Production run guidance

Configure deployment-managed secrets, authorized domains and approved storage/access controls. Apply persisted migrations through the deployment workflow, then start the application through the platform's Reflex deployment runtime. Complete post-deploy acceptance for authentication, authorization, database persistence, protected downloads, AI boundaries, notification delivery and certificate verification.

**Production deployment: NOT_VERIFIED.** No production-readiness claim is made. Known release blockers and gaps remain documented in `CAPACITY_CONNECT_SECURITY_AUDIT.md`.

## AI setup and fallback boundary

CAPACITY AI uses `GOOGLE_API_KEY` and may use the optional `GEMINI_BASE_URL`. Requests must contain minimized, authorized learning context. Gemini is advisory only: it cannot authorize access, disclose active official answers, write official grades, issue certificates or award verified competency. Model output and approved resource text are untrusted. If the provider is unavailable or unconfigured, the application uses a database-grounded advisory fallback and labels it as a fallback, not as a successful model response. Full adversarial prompting, all actions and browser behavior remain NOT_VERIFIED.

## Storage setup and assurance limits

Training resources and submitted files use private storage outside Reflex’s public upload directory, bounded content validation, bounded filenames and paths, and authorization at download time. Fresh role-scoped server events retrieve bytes: trainees require current non-dropped enrollment and a published matching-course resource; trainers require a current approved course assignment. Frontend payloads do not expose stored filenames and direct `rx.get_upload_url` access was removed. Read/write operations are bounded at 50 MB and private storage round-trip tests pass.

Production must configure `CC_PRIVATE_UPLOAD_DIR` to durable non-public storage with least-privilege filesystem access. Deployment storage durability, large-file delivery behavior, malicious-content scanning and post-deploy persistence remain NOT_VERIFIED. Do not treat UI visibility as download authorization.

## Demo accounts and guide

The isolated demonstration actors and role-specific navigation are documented in [`CAPACITY_CONNECT_DEMO_GUIDE.md`](CAPACITY_CONNECT_DEMO_GUIDE.md). The fixed shared credential `Demo@1234` is intentionally public in the demo sign-in UI and is for demonstration access only. It must never be used for production accounts or private records. The guide names the exact account identifiers but never exposes sessions, recovery links or certificate tokens. Use separate browser profiles, and never rehearse against production.

## Concise eleven-step demo flow

1. Administrator identifies an organizational competency gap and affected trainee.
2. Administrator reviews explainable Trainer Fit and revalidates assignment eligibility.
3. Trainee reviews the gap and an owned, persisted learning path.
4. Trainee completes an approved learning activity and optionally uses advisory AI.
5. Trainee completes formative practice without changing official mastery.
6. Trainee takes the authorized, timed official assessment.
7. The server records qualifying evidence and recalculates the gap.
8. Trainee reviews the evidence-backed competency passport and provenance.
9. If currently eligible, trainee requests certification and an administrator reviews issuance; public verification is checked separately.
10. Administrator reviews observed, chronological training effectiveness without claiming causality.
11. Administrator recalculates Trainer Fit and trainer reviews permitted cohort feedback/performance.

The eleven-step sequence is a rehearsal plan, not proof that the browser workflow has been executed. Preserve the conservative distinctions between recommendation and authorization, practice and official assessment, observed improvement and causal impact, and course certificates and verified competency evidence.

## Cross-cutting role and security boundaries

Trainees access their own records and eligible learning; trainers access authorized courses, cohorts and grading work; administrators manage organizational and operational controls; public visitors receive only deliberately limited information. Navigation visibility is not authorization. Every sensitive read and mutation must independently check current identity, approval/activity, ownership and course scope.

Current assurance limits include the **INSECURE** client-managed non-HttpOnly session cookie, plus partially implemented recovery delivery and complete session revocation. Protected resource downloads are authorization-scoped, while complete browser workflow, concurrency, real email delivery, deployment storage durability, large-file delivery, malicious-content scanning, post-deploy persistence and production deployment remain **NOT_VERIFIED**. See the companion audit, security audit, test report and demo guide for evidence and limitations.
