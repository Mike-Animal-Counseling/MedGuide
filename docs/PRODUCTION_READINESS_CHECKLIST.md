# Production Readiness Checklist

This checklist captures the current production-readiness audit status for MedGuide AI. It is not
a substitute for filling production secrets, provisioning managed infrastructure, or completing
manual accessibility, security, and compliance review.

## Status Summary

| Category | Status | Notes | Remaining manual tasks | Required external credentials | Deployment blockers |
| --- | --- | --- | --- | --- | --- |
| Fake production behavior | Pass | Real app code uses provider interfaces and unconfigured providers that fail safely. Test mocks are limited to test files and fixtures. | Re-run search before each release when adding providers. | None | None found in app code. |
| External provider configuration | Pass with manual action | Required provider variables are centralized in `docs/PLACEHOLDERS_AND_SECRETS.md` and `.env.example`. Production settings reject missing required S3, OCR, vision, Expo, JWT, CORS, database, and Redis configuration. | Owner must fill real staging/production values in the deployment secret manager. | PostgreSQL, Redis, JWT, S3, AWS Textract, AWS Rekognition, Expo push; optional Sentry, Twilio, SendGrid | Production cannot start safely until required credentials and managed URLs are provided. |
| Medical safety | Pass | AI/OCR flows require confirmation and use conservative safety messages. Verification compares images only against the currently due medication and does not claim universal pill identification. | Clinical/product safety wording review before launch. Review any future AI-generated content. | OCR and vision credentials if scan/verification are enabled | Do not enable AI verification in production until real provider credentials and safety review are complete. |
| Security | Pass with manual action | Protected backend endpoints require auth. Caregiver access is permission-scoped. Signed image URLs require owner or authorized caregiver access. Production rejects weak/missing JWT config and permissive CORS. | Run staging penetration/security review, configure secret rotation, and enforce least-privilege IAM. | JWT secret, S3 IAM, AWS provider IAM, Expo token | Real secret manager and least-privilege cloud identities must be configured. |
| Privacy and retention | Pass with manual action | Audit logging, privacy export, caregiver revocation, image soft delete, signed URL denial after delete, and redaction utilities exist. Raw OCR text is not logged by app logging paths. | Finalize retention policy, privacy policy, incident process, and data residency requirements. | S3 retention/lifecycle credentials and optional Sentry DSN | Production retention automation depends on approved policy and infrastructure settings. |
| Testing | Pass locally | Backend and mobile tests enforce coverage thresholds and provider mocks stay in test code. | Keep coverage thresholds enforced as modules change. Run full suite in CI on the hosted repository. | None for tests; provider calls are mocked | Hosted CI has not run until the repo is pushed/connected to GitHub. |
| Accessibility | Pass with manual action | Mobile screens use accessibility-first components, labels, hints, large actions, high contrast, large text settings, and voice prompts. | Manual VoiceOver, TalkBack, large text, reduced motion, keyboard/focus, and contrast checks before release. | None | Manual assistive-technology testing is still required before production release. |
| CI/CD | Configured, pending hosted run | GitHub Actions cover backend, mobile, security, and docs gates. | Push/connect the repository to GitHub and verify all Actions pass on `main` and pull requests. | GitHub repository access; optional CI secrets if future workflows need them | CI files exist locally, but hosted checks do not run until GitHub is connected. |
| Documentation | Pass | Required docs exist: architecture, API contract, AI safety, accessibility, testing, placeholders/secrets, deployment, privacy/retention, observability, and this checklist. | Keep docs updated with every new env var, provider, secret, workflow, or safety boundary. | None | None. |
| Deployment assets | Pass with manual action | Production Dockerfile, worker command, dev/prod compose examples, deployment docs, and production config safety tests exist. | Provision managed PostgreSQL, Redis, S3, provider accounts, run Alembic migrations, configure worker/scheduler, and deploy mobile with production API URL. | PostgreSQL, Redis, JWT, S3, Textract, Rekognition, Expo push, optional Sentry/Twilio/SendGrid | Managed infrastructure and required secrets are not provisioned in this repository by design. |
| Observability | Pass with manual action | Backend JSON logging, request IDs, duration logging, redaction, optional Sentry, metrics endpoint, and mobile error reporting abstraction exist. | Decide Sentry/data-retention policy, sampling rate, alert routing, and safe production dashboards. | Optional `SENTRY_DSN` and `EXPO_PUBLIC_SENTRY_DSN` | Optional unless the launch plan requires hosted error monitoring. |

## Required External Credentials

These values must be provided by the project owner or deployment operator. They must not be
committed to the repository.

| Credential group | Required for MVP | Required for production | Environment variables |
| --- | --- | --- | --- |
| Managed PostgreSQL | Yes | Yes | `DATABASE_URL` |
| Redis | Yes | Yes | `REDIS_URL` |
| JWT signing | Yes | Yes | `JWT_SECRET`, `JWT_SECRET_KEY` |
| CORS and public API URL | Yes | Yes | `API_CORS_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `API_BASE_URL`, `EXPO_PUBLIC_API_BASE_URL` |
| Private S3 storage | Yes for images | Yes | `STORAGE_PROVIDER`, `S3_BUCKET`, `S3_BUCKET_NAME`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` |
| OCR provider | Yes if label scan is enabled | Yes if label scan is enabled | `OCR_PROVIDER`, `AWS_TEXTRACT_REGION`, `AWS_TEXTRACT_ACCESS_KEY_ID`, `AWS_TEXTRACT_SECRET_ACCESS_KEY` |
| Vision provider | Yes if medication verification is enabled | Yes if medication verification is enabled | `VISION_PROVIDER`, `AWS_REKOGNITION_REGION`, `AWS_REKOGNITION_ACCESS_KEY_ID`, `AWS_REKOGNITION_SECRET_ACCESS_KEY` |
| Expo push | Yes for reminders | Yes for reminders | `NOTIFICATION_PROVIDER`, `EXPO_PUSH_ACCESS_TOKEN`, `EXPO_ACCESS_TOKEN` |
| Sentry | No | Optional | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `EXPO_PUBLIC_SENTRY_DSN` |
| Twilio SMS | No | Optional only when SMS is enabled | `ENABLE_SMS_NOTIFICATIONS`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE` |
| SendGrid email | No | Optional only when email is enabled | `ENABLE_EMAIL_NOTIFICATIONS`, `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` |

## Manual Release Tasks

1. Fill all production secrets in a deployment secret manager, not in `.env` files committed to git.
2. Provision managed PostgreSQL and Redis, then set production URLs.
3. Configure a private S3 bucket with Block Public Access, least-privilege IAM, signed URL CORS,
   lifecycle rules, and retention policy if required.
4. Configure AWS Textract and AWS Rekognition credentials if OCR and medication verification are
   enabled.
5. Configure Expo push credentials if reminder notifications are enabled.
6. Set `APP_ENV=production`, explicit CORS origins, a strong JWT secret, and production mobile API
   URL.
7. Run `alembic upgrade head` against the production database before serving traffic.
8. Start the FastAPI web process, Celery worker, and Celery beat/scheduler under production
   process supervision.
9. Push/connect the repository to GitHub and verify backend, mobile, security, and docs workflows
   pass.
10. Complete manual VoiceOver/TalkBack, security, privacy, retention, and safety wording review.

## Current Deployment Blockers

| Blocker | Why it matters | Resolution |
| --- | --- | --- |
| Production external credentials are not provided | The app intentionally refuses unsafe provider fallbacks in production. | Fill required secrets from `docs/PLACEHOLDERS_AND_SECRETS.md` in a secret manager. |
| Managed PostgreSQL and Redis are not provisioned by this repo | Local Docker Compose is for development only. | Provision managed services and set `DATABASE_URL` and `REDIS_URL`. |
| Hosted GitHub Actions have not run until the repo is connected | Workflow files exist locally, but hosted CI status requires GitHub. | Push/connect the repository and verify all workflows. |
| Manual accessibility and security reviews are not automated | Automated tests cannot fully validate assistive technology behavior or production threat model. | Complete documented manual release checks. |
