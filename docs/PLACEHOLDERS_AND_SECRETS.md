# Placeholders And Secrets

This file is the single source of truth for MedGuide AI configuration, external providers,
secrets, and placeholder values. If a new provider, environment variable, feature flag, or secret
is introduced, document it here and update `.env.example` in the same change.

For a simpler step-by-step registration guide, see `docs/SETUP.md`.

MedGuide AI must not fabricate production behavior. Missing production credentials must fail
safely with a clear configuration or service-unavailable error. Test mocks are allowed only in
test files or explicit test fixtures.

## Environment Overview

| Environment | Purpose | Provider behavior | Secrets source |
| --- | --- | --- | --- |
| `development` / `local` | Developer machines and local Docker Compose | Real local PostgreSQL/Redis. External providers may be `unconfigured`; local dev storage must be explicitly gated if added. | Local `.env`, never committed |
| `test` | Automated unit and integration tests | Test mocks and recording providers may be injected only from test code. No production fallback may use mocks. | Test fixtures and CI test secrets |
| `staging` | Production-like validation | Real managed PostgreSQL/Redis and real external providers or explicitly disabled optional channels. No fake providers. | Deployment secret manager |
| `production` | Live user traffic | Required providers must be configured. Missing required config fails safely. Optional SMS/email must be explicitly disabled or backed by real adapters. | Deployment secret manager only |

Current backend code accepts `APP_ENV=local`, `APP_ENV=test`, and `APP_ENV=production`.
Use `APP_ENV=production` for both staging-like strict validation and production unless a staging
environment enum is added in code.

## Explicit Rules

- No fake providers in production.
- No checked-in secrets, private keys, tokens, real passwords, or provider credentials.
- Mocks only in tests or explicit test fixtures.
- Local development providers must be explicitly gated and documented.
- Production missing required provider config must fail safely.
- `APP_ENV=production` rejects local development storage and test provider mock flags.
- Never put secrets in `EXPO_PUBLIC_*`; Expo public variables are embedded in the mobile app.
- Signed URLs, JWTs, OCR text, push tokens, and provider responses must not be written to logs
  unless an approved redaction policy covers them.
- AI output is medication assistance only. It must not diagnose, prescribe, recommend dosage, or
  claim certainty.

## Required Backend Environment Variables

The table includes the prompt-required names and the current code names where they differ.
`.env.example` includes both when a compatibility alias is useful for deployment planning.

| Variable | Current code name | Required for | Secret | Safe local example | Notes |
| --- | --- | --- | --- | --- | --- |
| `APP_ENV` | `APP_ENV` | all envs | No | `local` | Use `production` for strict production validation. |
| `DATABASE_URL` | `DATABASE_URL` | all envs | Yes in shared envs | `postgresql+asyncpg://medguide:change-me@localhost:5432/medguide` | Production must use managed credentials, not localhost/change-me. |
| `REDIS_URL` | `REDIS_URL` | all envs | Yes in shared envs | `redis://localhost:6379/0` | Production must use managed credentials. |
| `JWT_SECRET_KEY` | `JWT_SECRET` | auth | Yes | empty / generated locally | Current backend reads `JWT_SECRET`; production requires at least 32 random characters. |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `ACCESS_TOKEN_EXPIRE_MINUTES` | auth | No | `15` | Current backend reads `ACCESS_TOKEN_EXPIRE_MINUTES`. |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `REFRESH_TOKEN_EXPIRE_DAYS` | auth | No | `30` | Current backend reads `REFRESH_TOKEN_EXPIRE_DAYS`. |
| `CORS_ALLOWED_ORIGINS` | `API_CORS_ORIGINS` | API security | No | `http://localhost:8081` | Current backend reads comma-separated `API_CORS_ORIGINS`. Production cannot use `*`. |
| `LOG_LEVEL` | `LOG_LEVEL` | all envs | No | `INFO` | Structured logs are redacted. |
| `SENTRY_DSN` | `SENTRY_DSN` | Optional | Yes | empty | Enables backend Sentry integration when set. Missing value is safe in local development. |
| `SENTRY_ENVIRONMENT` | `SENTRY_ENVIRONMENT` | Optional | No | empty | Defaults to `APP_ENV` when omitted. |
| `SENTRY_TRACES_SAMPLE_RATE` | `SENTRY_TRACES_SAMPLE_RATE` | Optional | No | `0` | Keep low in production and review PHI risk before increasing. |
| `API_BASE_URL` | not currently read by backend | clients/docs | No | `http://localhost:8000` | Canonical public API URL for docs, mobile config, callbacks, and deployment metadata. |
| `API_V1_PREFIX` | `API_V1_PREFIX` | backend routes | No | `/api/v1` | Existing backend route prefix. |
| `READINESS_TIMEOUT_SECONDS` | `READINESS_TIMEOUT_SECONDS` | readiness | No | `2` | Per-service readiness timeout. |
| `JWT_ALGORITHM` | `JWT_ALGORITHM` | auth | No | `HS256` | Current implementation supports `HS256`. |

## Storage Provider

Current production storage implementation is S3. The backend stores private object references and
short-lived signed URLs only; it must never expose public bucket URLs.

| Variable | Current code name | Required for production | Secret | Notes |
| --- | --- | --- | --- | --- |
| `STORAGE_PROVIDER` | `STORAGE_PROVIDER` | Yes | No | Use `s3` in production; `unconfigured` fails safely. |
| `S3_BUCKET_NAME` | `S3_BUCKET` | Yes when `s3` | No | Dedicated private bucket with Block Public Access. |
| `S3_REGION` | `S3_REGION` | Yes when `s3` | No | AWS region. |
| `S3_ACCESS_KEY_ID` | `S3_ACCESS_KEY_ID` | Yes when `s3` | Yes | Restricted IAM key. |
| `S3_SECRET_ACCESS_KEY` | `S3_SECRET_ACCESS_KEY` | Yes when `s3` | Yes | Restricted IAM secret. |
| `S3_ENDPOINT_URL` | not currently read | Optional | No | For S3-compatible storage if an adapter is added. Do not set for AWS S3 unless supported. |
| `SIGNED_URL_EXPIRATION_SECONDS` | `STORAGE_SIGNED_URL_EXPIRE_SECONDS` | Yes | No | Current backend reads `STORAGE_SIGNED_URL_EXPIRE_SECONDS`. |
| `MAX_UPLOAD_SIZE_MB` | `STORAGE_MAX_UPLOAD_BYTES` | Yes | No | Current backend reads bytes. Keep the MB value aligned manually. |
| `ALLOWED_IMAGE_CONTENT_TYPES` | `STORAGE_ALLOWED_CONTENT_TYPES` | Yes | No | Comma-separated image MIME types. |
| `STORAGE_RETENTION_DAYS` | `STORAGE_RETENTION_DAYS` | Optional | No | Enables cleanup foundation and retain-until metadata where supported. |

Production S3 checklist:

- Private bucket only, no public-read ACLs.
- Bucket CORS limited to deployed app origins and required upload headers.
- IAM policy restricted to required object prefix and `PutObject`, `GetObject`, `DeleteObject`.
- Lifecycle/Object Lock configured separately if retention must be enforced.

## OCR Provider

Current real adapter: AWS Textract. Google Vision variables are listed for future provider
selection but no Google Vision adapter is currently selected.

| Variable | Current code name | Required for production | Secret | Notes |
| --- | --- | --- | --- | --- |
| `OCR_PROVIDER` | `OCR_PROVIDER` | Yes | No | Use `aws_textract` in production. `unconfigured` fails safely. |
| `GOOGLE_APPLICATION_CREDENTIALS` | not currently read | Only if Google Vision adapter is implemented | Yes/path | Must point to secret-managed service account credentials. Do not commit JSON keys. |
| `AWS_TEXTRACT_REGION` | `AWS_TEXTRACT_REGION` | Yes for Textract | No | AWS region. |
| `AWS_TEXTRACT_ACCESS_KEY_ID` | `AWS_TEXTRACT_ACCESS_KEY_ID` | Yes for Textract | Yes | Restricted to Textract OCR operations. |
| `AWS_TEXTRACT_SECRET_ACCESS_KEY` | `AWS_TEXTRACT_SECRET_ACCESS_KEY` | Yes for Textract | Yes | Store in secret manager. |
| `IMAGE_QUALITY_MIN_WIDTH` | `IMAGE_QUALITY_MIN_WIDTH` | Yes | No | Local quality check before OCR. |
| `IMAGE_QUALITY_MIN_HEIGHT` | `IMAGE_QUALITY_MIN_HEIGHT` | Yes | No | Local quality check before OCR. |
| `IMAGE_QUALITY_MIN_CONTRAST` | `IMAGE_QUALITY_MIN_CONTRAST` | Yes | No | Local quality check before OCR. |

Provider selection:

- Set `OCR_PROVIDER=aws_textract` and configure Textract credentials for current production use.
- Do not set Google Vision variables unless a real `GoogleVisionOCRProvider` adapter is
  implemented and selected.
- If OCR credentials are missing in production, backend startup/configuration fails or the service
  returns a clear provider-not-configured error. It must never fabricate text.
- Tests inject mock OCR providers only from backend test files and generated test images. Mobile
  OCR tests mock API responses only inside mobile test files.

## Vision Provider

Current real adapter: AWS Rekognition. The product currently uses deterministic backend scoring
against the user's due medication. A vision model must never directly decide medical action.

| Variable | Current code name | Required for production | Secret | Notes |
| --- | --- | --- | --- | --- |
| `VISION_PROVIDER` | `VISION_PROVIDER` | Yes | No | Use `aws_rekognition` for current production implementation. |
| `AWS_REKOGNITION_REGION` | `AWS_REKOGNITION_REGION` | Yes for Rekognition | No | AWS region. |
| `AWS_REKOGNITION_ACCESS_KEY_ID` | `AWS_REKOGNITION_ACCESS_KEY_ID` | Yes for Rekognition | Yes | Restricted IAM key. |
| `AWS_REKOGNITION_SECRET_ACCESS_KEY` | `AWS_REKOGNITION_SECRET_ACCESS_KEY` | Yes for Rekognition | Yes | Store in secret manager. |
| `OPENAI_API_KEY` | not currently read | Only if OpenAI vision adapter is implemented | Yes | No OpenAI production adapter is currently selected. |
| `VISION_MODEL_NAME` | not currently read | Only if model-based adapter is implemented | No | Model name for future provider adapter. |
| `ENABLE_AI_VERIFICATION` | not currently read | Product flag | No | Keep aligned with selected provider and backend deployment. |

Safety boundary:

- Verification compares an image only against the currently due medication.
- Return wording must use uncertainty: "appears to match", "not fully sure", or "cannot confirm".
- The backend safety rule engine makes final classification.
- Tests inject mock vision providers only in test files. Production has no fake vision fallback.

## Notification Providers

Current production push adapter: Expo push. SMS and email provider interfaces are documented but
remain disabled until real adapters are implemented and injected.

| Variable | Current code name | Required for production | Secret | Notes |
| --- | --- | --- | --- | --- |
| `NOTIFICATION_PROVIDER` | `NOTIFICATION_PROVIDER` | Yes | No | Use `expo` in production. |
| `EXPO_ACCESS_TOKEN` | `EXPO_PUSH_ACCESS_TOKEN` | Yes for Expo push | Yes | Current backend reads `EXPO_PUSH_ACCESS_TOKEN`. |
| `TWILIO_ACCOUNT_SID` | not currently read | Only if SMS adapter is implemented | Yes | Required for Twilio SMS. |
| `TWILIO_AUTH_TOKEN` | not currently read | Only if SMS adapter is implemented | Yes | Store in secret manager. |
| `TWILIO_FROM_PHONE` | not currently read | Only if SMS adapter is implemented | No/secret depending policy | Approved sender phone. |
| `SENDGRID_API_KEY` | not currently read | Only if email adapter is implemented | Yes | Required for SendGrid email. |
| `SENDGRID_FROM_EMAIL` | not currently read | Only if email adapter is implemented | No | Verified sender email. |
| `SMS_PROVIDER` | `SMS_PROVIDER` | Optional | No | Current code supports only `disabled`. |
| `EMAIL_PROVIDER` | `EMAIL_PROVIDER` | Optional | No | Current code supports only `disabled`. |
| `ENABLE_SMS_NOTIFICATIONS` | not currently read | Feature flag | No | Must remain false until real SMS adapter exists. |
| `ENABLE_EMAIL_NOTIFICATIONS` | not currently read | Feature flag | No | Must remain false until real email adapter exists. |
| `ENABLE_CAREGIVER_ESCALATION` | not currently read | Feature flag | No | Backend escalation logic exists; deployments should document whether it is enabled operationally. |
| `REMINDER_SECOND_OFFSET_MINUTES` | `REMINDER_SECOND_OFFSET_MINUTES` | Worker | No | Optional second reminder delay. |
| `REMINDER_ESCALATION_MINUTES` | `REMINDER_ESCALATION_MINUTES` | Worker | No | Caregiver escalation threshold. |
| `REMINDER_MISSED_CUTOFF_MINUTES` | `REMINDER_MISSED_CUTOFF_MINUTES` | Worker | No | Missed-dose cutoff. |
| `NOTIFICATION_RETRY_MAX_ATTEMPTS` | `NOTIFICATION_RETRY_MAX_ATTEMPTS` | Worker | No | Durable retry limit. |

Notification content must stay generic and assistance-oriented. Review consent, opt-out, sender
identity, regional requirements, delivery receipts, cost controls, and PHI exposure before enabling
SMS or email.

## Caregiver Invite Delivery

| Variable | Required | Secret | Notes |
| --- | --- | --- | --- |
| `CAREGIVER_INVITE_EXPIRE_HOURS` | Yes | No | Invite lifetime. |
| `CAREGIVER_INVITE_TOKEN_RETURN_ENABLED` | Local/test only | No | Production rejects `true`. Raw invite tokens may be returned only in explicitly configured non-production use. |

Production invite delivery must use a real notification/email provider. The default composition
does not pretend an invite was sent.

## Mobile Environment Variables

| Variable | Required | Secret | Safe local example | Notes |
| --- | --- | --- | --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | Yes | No | `http://localhost:8000` | Mobile API base URL. No hardcoded production URL. |
| `EXPO_PUBLIC_SENTRY_DSN` | Optional | No | empty | Public Sentry DSN for client-side error reporting. Never put private secrets in Expo public variables. |
| `EXPO_PUBLIC_APP_ENV` | Yes | No | `development` | Public environment label for UI diagnostics and feature flags. |
| `EXPO_PUBLIC_ENABLE_PUSH_NOTIFICATIONS` | Optional | No | `true` | Public flag for showing reminder registration UI. Backend remains source of truth. |
| `EXPO_PUBLIC_ENABLE_LOCAL_REMINDERS` | Optional | No | `true` | Local fallback only for backend-fetched visible pending doses. |
| `EXPO_PUBLIC_ENABLE_AI_VERIFICATION` | Optional | No | `true` | UI flag only; backend provider still enforces safety. |
| `EXPO_PUBLIC_ENABLE_CAREGIVER_DASHBOARD` | Optional | No | `true` | UI flag only; backend authorizes every caregiver request. |

Do not put provider keys, JWT secrets, push access tokens, S3 credentials, OCR credentials, or
database URLs in Expo public variables.

## Feature Flags

| Variable | Scope | Allowed values | Production rule |
| --- | --- | --- | --- |
| `ENABLE_SMS_NOTIFICATIONS` | Backend/ops | `true` / `false` | Must be `false` until a real SMS adapter and consent workflow exist. |
| `ENABLE_EMAIL_NOTIFICATIONS` | Backend/ops | `true` / `false` | Must be `false` until a real email adapter and sender verification exist. |
| `ENABLE_LOCAL_DEV_STORAGE` | Backend/dev | `true` / `false` | May be true only in local development if a real local-dev provider is implemented and gated. |
| `ENABLE_TEST_PROVIDER_MOCKS` | Tests only | `true` / `false` | May be true only in `APP_ENV=test`; production must never read this to install mocks. |
| `ENABLE_AI_VERIFICATION` | Backend/mobile | `true` / `false` | Requires real vision provider in production. |
| `ENABLE_CAREGIVER_ESCALATION` | Worker/ops | `true` / `false` | Requires notification provider and caregiver permission review. |

Feature flags do not bypass backend authorization, provider configuration, or safety wording.

## Test Mock Rules

- Backend provider mocks live in backend test files or fixtures.
- Mobile API, SecureStore, camera, notification, and speech mocks live in mobile test files.
- Tests may mock provider success and failure paths, but production code must call configured
  providers or fail safely.
- `ENABLE_TEST_PROVIDER_MOCKS` is documentation-only unless a test harness explicitly reads it.
  Production code must not use it as a fallback path.
- Backend production settings explicitly reject `ENABLE_LOCAL_DEV_STORAGE=true` and
  `ENABLE_TEST_PROVIDER_MOCKS=true`.

## Deployment References

See `docs/DEPLOYMENT.md` for container commands, migration commands, worker commands,
Render/Railway deployment notes, and AWS ECS/RDS/S3/ElastiCache production deployment guidance.
Production deployments must use private S3 buckets with Block Public Access enabled and
short-lived signed URLs only.

## Checklist

| Item | Required for MVP | Required for Production | Owner must provide | Env var | Current status |
| --- | --- | --- | --- | --- | --- |
| Runtime environment | Yes | Yes | Engineering | `APP_ENV` | Documented; code supports `local`, `test`, `production` |
| Managed PostgreSQL | Yes | Yes | Infrastructure | `DATABASE_URL` | Local example only |
| Redis | Yes | Yes | Infrastructure | `REDIS_URL` | Local example only |
| JWT signing secret | Yes | Yes | Security/Infrastructure | `JWT_SECRET` / `JWT_SECRET_KEY` | Placeholder only |
| CORS origins | Yes | Yes | Engineering | `API_CORS_ORIGINS` / `CORS_ALLOWED_ORIGINS` | Local origin only |
| Public API URL | Yes | Yes | Engineering | `API_BASE_URL`, `EXPO_PUBLIC_API_BASE_URL` | Local example only |
| Private image storage | Yes | Yes | Infrastructure | `STORAGE_PROVIDER`, `S3_*` | Real S3 adapter exists; credentials not provided |
| Signed URL policy | Yes | Yes | Engineering | `STORAGE_SIGNED_URL_EXPIRE_SECONDS`, `SIGNED_URL_EXPIRATION_SECONDS` | Local safe default |
| Upload size policy | Yes | Yes | Product/Security | `STORAGE_MAX_UPLOAD_BYTES`, `MAX_UPLOAD_SIZE_MB` | Local safe default |
| OCR provider | Yes for scan feature | Yes if scan enabled | Infrastructure/AI owner | `OCR_PROVIDER`, `AWS_TEXTRACT_*` or `GOOGLE_APPLICATION_CREDENTIALS` | AWS Textract adapter exists; credentials not provided |
| Vision provider | Yes for verification | Yes if verification enabled | Infrastructure/AI owner | `VISION_PROVIDER`, `AWS_REKOGNITION_*`, optional future `OPENAI_API_KEY` | AWS Rekognition adapter exists; credentials not provided |
| Expo push | Yes for reminders | Yes for reminders | Mobile/Infrastructure | `NOTIFICATION_PROVIDER`, `EXPO_PUSH_ACCESS_TOKEN`, `EXPO_ACCESS_TOKEN` | Adapter exists; token not provided |
| SMS notifications | No | Optional | Product/Compliance | `ENABLE_SMS_NOTIFICATIONS`, `TWILIO_*` | Disabled; no adapter selected |
| Email notifications | No | Optional | Product/Compliance | `ENABLE_EMAIL_NOTIFICATIONS`, `SENDGRID_*` | Disabled; no adapter selected |
| Caregiver invite delivery | Yes for production invites | Yes | Product/Infrastructure | provider-specific notification/email variables | Interface exists; real delivery not selected |
| Local dev storage | No | No | Engineering | `ENABLE_LOCAL_DEV_STORAGE` | Disabled; no production fallback |
| Test provider mocks | Yes for tests | No | Engineering | `ENABLE_TEST_PROVIDER_MOCKS` | Tests only |
| AI safety review | Yes | Yes | Product/Clinical reviewer | `ENABLE_AI_VERIFICATION`, provider vars | Safety docs present |
| Caregiver escalation | Yes for caregiver alerts | Yes if enabled | Product/Compliance | `ENABLE_CAREGIVER_ESCALATION`, notification vars | Worker logic exists |
| Backend error monitoring | No | Optional | Infrastructure | `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE` | Optional integration; disabled when DSN missing |
| Mobile error monitoring | No | Optional | Mobile/Infrastructure | `EXPO_PUBLIC_SENTRY_DSN` | Safe client reporter abstraction exists |

## Secret Operations

- Generate JWT and provider secrets with cryptographically secure tooling.
- Store production/staging secrets in the deployment secret manager.
- Rotate a secret immediately if it appears in source, logs, screenshots, CI output, or build
  artifacts.
- Rotating `JWT_SECRET` currently invalidates issued access and refresh tokens.
- Use least-privilege IAM/service accounts for S3, Textract, Rekognition, Expo, Twilio, and
  SendGrid.
- Review data residency, retention, audit, cost limits, and healthcare/compliance requirements
  before production traffic reaches external providers.
