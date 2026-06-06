# Architecture

## Overview

MedGuide AI is a monorepo with independently deployable backend and mobile applications.

- `backend`: FastAPI application using Pydantic v2 settings, SQLAlchemy 2 async APIs, Alembic,
  PostgreSQL, and Redis.
- `mobile`: Expo React Native application using TypeScript and React Navigation.
- `infra`: local-development infrastructure notes. Local Docker Compose runs PostgreSQL and Redis
  only.

## Mobile Application

The Expo app is a typed client for the real backend API. It does not contain demo medication data
or local authentication bypasses. Runtime configuration reads `EXPO_PUBLIC_API_BASE_URL`; public
Expo variables must never contain secrets.

```text
mobile/src/
  api/                    API base URL and typed fetch wrapper
  auth/                   SecureStore token persistence and auth context
  navigation/             React Navigation stack composition
  screens/                Auth, patient, caregiver, and settings screens
  components/             Accessibility-first reusable UI components
  hooks/                  TanStack Query hooks for backend resources
  accessibility/          High contrast and large text preferences
  notifications/          Expo notification permission helpers
  camera/                 Expo camera permission helpers
  voice/                  Expo Speech helpers for voice-ready prompts
  theme/                  Device-level visual theme primitives
  tests/                  React Native Testing Library tests
```

`apiRequest` attaches the access token from Expo SecureStore and uses the backend's structured
error response to raise typed client errors. Missing mobile API configuration fails clearly rather
than falling back to a hardcoded production URL.

The initial navigation stack separates unauthenticated screens from authenticated patient,
caregiver, and accessibility workflows. Screens use loading and error states around real API
queries and mutations. Empty states are plain UI states, not seeded production data.

The patient daily workflow reads `/api/v1/dose-logs/today` and `/api/v1/medications` from the
backend, then maps dose logs to the user's saved medication records on-device. The Home screen
surfaces the current due dose or next pending dose and offers a large medication-check entry point.
The Today Schedule screen calls the real dose-log action endpoints:

- `PATCH /api/v1/dose-logs/{id}/confirm`
- `PATCH /api/v1/dose-logs/{id}/skip`
- `PATCH /api/v1/dose-logs/{id}/needs-help`

Medication verification starts from a pending dose. The mobile app reads the saved medication name,
dosage text, and user-confirmed instruction aloud, asks the user to center the pill or bottle in
the camera, uploads the captured image through a signed `VERIFICATION_IMAGE` upload, and calls
`POST /api/v1/ai/verify-medication`. The backend remains the only verifier; the mobile app only
renders the returned safety result:

- `MATCH_LIKELY`: show cautious "appears to match" wording and allow Mark as Taken.
- `MATCH_UNCERTAIN`: show Retake, Contact Caregiver, and a de-emphasized Mark as Taken path that
  requires extra user confirmation text.
- `CAREGIVER_REVIEW_REQUIRED` or `NO_MATCH`: do not show the primary Mark as Taken action.
- `UNREADABLE_IMAGE`: ask the user to retake the photo.

Logout calls `/api/v1/auth/logout` with the stored refresh token and then clears local SecureStore
tokens even if the network request fails, keeping device logout safe.

Critical medication workflows repeat the backend safety boundary: OCR requires confirmation,
verification compares only against the currently due medication, and safety copy avoids certainty
or dosage recommendations.

## Backend Boundaries

The backend uses async SQLAlchemy consistently.

```text
backend/app/
  main.py                 FastAPI composition root and resource lifespan
  core/                   settings, logging, errors, middleware, security contracts
  db/                     SQLAlchemy base, session factories, Alembic migrations
  api/                    operational routes and versioned API routers
  models/                 SQLAlchemy models
  schemas/                Pydantic request and response models
  services/               application and infrastructure health services
  repositories/           persistence abstractions
  tests/                  backend unit and isolated database tests
```

`app.main` creates the async database engine and Redis client during application lifespan and
closes both during shutdown. Request dependencies obtain resources from application state rather
than creating global connections.

`GET /health` is a liveness check and does not contact dependencies. `GET /ready` executes a real
database `SELECT 1` and Redis `PING`; it returns HTTP 503 using the standard error format when
either dependency is unavailable.

`app.repositories.base.BaseRepository` provides the minimal shared persistence operations.
Feature repositories should extend it only when they have domain-specific query behavior.

`app.core.security.RateLimiter` is a provider-neutral interface only. No permissive or fabricated
rate limiter is installed in the production request path. A real implementation and configuration
must be added before routes claim to be rate limited.

## Authentication and Users

Authentication uses normalized email/password credentials, Argon2 password hashes, short-lived
JWT access tokens, and rotating JWT refresh tokens.

- Public registration permits `PATIENT` and `CAREGIVER`; it never permits creating `ADMIN`.
- Protected routes load the active user from PostgreSQL, so soft-deleted users are rejected
  immediately even if an access token has not expired.
- Refresh tokens are rotated on use. Only their SHA-256 hashes and identifiers are persisted.
- Logout revokes the supplied refresh token. Soft deletion revokes every active refresh token for
  the user.
- Refresh rotation locks the stored token row to prevent concurrent reuse.
- User responses never expose password hashes, refresh-token hashes, or deletion metadata.
- Role checks use the current database role instead of trusting the role claim in a JWT.

Password hashing runs in a worker thread so Argon2 work does not block the async event loop.

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
PATCH  /api/v1/users/me
DELETE /api/v1/users/me
```

## Medication Domain

Medication CRUD follows strict ownership scoping in `MedicationRepository`: every list, read,
update, and delete query includes the authenticated patient ID and excludes soft-deleted rows.
Cross-user requests return not found instead of revealing record existence.

Caregiver medication access is resolved through `CaregiverAuthorizationService`. Every operation
maps the authenticated actor to a patient and requires a minimum permission level. Admin is not an
ownership bypass. Caregiver-created medication records use the `CAREGIVER` source, and only the
owning patient may confirm OCR records.

OCR records may be stored as unconfirmed drafts, but application logic and a PostgreSQL check
constraint force them inactive until the owning patient confirms them. Instructions are stored only
as user-confirmed text, so unconfirmed OCR drafts cannot store instructions. The medication domain
does not generate advice, dosages, or prescriptions.

User deletion is soft deletion. Confirmation references intentionally do not use `ON DELETE SET
NULL`, because clearing a confirmer on an active OCR record would violate confirmation integrity.

## Medication Scheduling

`ScheduleService` enforces patient ownership and active-medication rules.
`schedule_engine.generate_scheduled_times` is a deterministic, side-effect-free generator, while
`DoseLogRepository` persists generated occurrences with a database unique constraint on
`(schedule_id, scheduled_time)`. Repeated generation is therefore idempotent even when workers
race.

- `DAILY` and `WEEKLY` schedules use the patient's local wall-clock time.
- `EVERY_X_HOURS` uses real elapsed hours from `start_date` and the optional local
  `scheduled_time`; midnight is the explicit default anchor when no time is supplied.
- `AS_NEEDED` schedules never auto-generate dose logs.
- Inactive schedules, inactive or deleted medications, and dates outside schedule bounds do not
  generate dose logs.
- A nonexistent local time during a daylight-saving transition is skipped. An ambiguous repeated
  time uses the first occurrence. This makes regeneration deterministic.
- Generated times are stored and returned in UTC. Local-day queries calculate UTC bounds from the
  user's IANA timezone.

Schedule deletion deactivates the schedule. Schedule edits and deactivation never update or delete
historical dose logs. Automatic missed-dose transitions are intentionally not implemented until a
real background job system exists.

## Caregiver Links

Caregiver invitations use cryptographically random, one-time tokens. PostgreSQL stores only token
hashes. Acceptance requires an authenticated `CAREGIVER` account whose normalized email matches the
invitation. A partial unique index prevents more than one PENDING or ACTIVE link for the same
patient and caregiver email.

Authorization is cumulative: `VIEW_ONLY`, `MANAGE_MEDICATIONS`, then `FULL_ACCESS`. Each request
queries the ACTIVE link rather than trusting token claims or cached roles, so revocation is
immediate. `FULL_ACCESS` is represented in the shared authorization service for future AI
verification events; no event data or endpoint is invented before that domain exists.

`NotificationService` is a provider-neutral invite-delivery interface. The default application
composition uses an unconfigured implementation that returns a clear 503 instead of pretending an
invite was delivered. Raw invite tokens may be returned only outside production when explicitly
enabled.

The mobile caregiver dashboard consumes the database-backed caregiver endpoints:

- `GET /api/v1/caregivers/patients`
- `GET /api/v1/caregivers/patients/{patient_id}/today`
- `GET /api/v1/caregivers/patients/{patient_id}/dose-logs`
- `POST /api/v1/caregivers/accept`
- `PATCH /api/v1/caregivers/links/{id}/revoke`

Caregiver UI is permission-aware but not security-authoritative. The backend still enforces linked
patient access for every request. `VIEW_ONLY` hides management actions, `MANAGE_MEDICATIONS`
shows medication-management entry points, and `FULL_ACCESS` shows the verification review entry.
The current backend does not expose a caregiver AI verification event listing endpoint, so mobile
does not fabricate low-confidence events; it shows dose statuses requiring review and a clear API
boundary message until that endpoint exists.

## Private Image Storage

`StorageProvider` defines provider-neutral signed upload, signed read, and delete operations.
`S3StorageProvider` is the real production implementation and uses S3 presigned POST for upload,
presigned GET for read, and `delete_object` for deletion. The default unconfigured provider fails
with a clear 503; it never invents URLs or claims an object was stored.

`uploaded_images` stores private object keys and provider names. API responses expose image IDs and
short-lived signed URLs only; object keys and public bucket URLs are not returned. Medication rows
reference uploaded image IDs rather than URLs. Migration `0008` removes the legacy
`label_image_url` and `pill_image_url` columns because arbitrary URLs do not satisfy the private
storage boundary. It refuses to proceed when either legacy column contains data, preventing silent
loss and requiring an explicit private-object migration first.

The API generates object keys under a patient-specific random path. S3 upload signatures enforce
content type and content-length conditions. Optional retention metadata is included as
`x-amz-meta-retain-until`; actual retention enforcement still requires an S3 lifecycle or Object
Lock policy configured on the bucket.

Image authorization reuses the database-backed caregiver permission service. Provider deletion
must succeed before the database record is soft-deleted. No local-development storage provider is
currently implemented, so local upload endpoints fail clearly unless a real S3 provider or an
explicit test fixture is injected.

## Label OCR Pipeline

`OCRProvider` isolates external OCR. `AWSTextractOCRProvider` is the real adapter; the default
unconfigured provider returns a clear 503 and never fabricates label text. The scan pipeline:

1. Loads an active private `MEDICATION_LABEL` after owner or FULL_ACCESS caregiver authorization.
2. Reads bytes through `StorageProvider` with a server-side size limit.
3. Uses Pillow to verify decoding, minimum dimensions, and contrast.
4. Calls Textract only for readable images.
5. Conservatively extracts visible candidate lines without inferring missing medical information.
6. Persists a `LABEL_OCR` verification event and returns mandatory confirmation wording.

The pipeline never creates or updates a medication. Readable scans are audited as
`CAREGIVER_REVIEW_REQUIRED`; unreadable or empty-text scans are audited as `UNREADABLE_IMAGE`.

## Scheduled Medication Verification

`VisionProvider` isolates external visual feature extraction. `AWSRekognitionVisionProvider` is
the real adapter and extracts observable labels and visible text only; it does not identify drugs.
The verification service authorizes the due dose and private `VERIFICATION_IMAGE`, requires an
ACTIVE medication, enforces configurable early/recent-due windows, and performs image-quality
checks before calling the provider.

`MedicationVerificationScorer` is a deterministic backend rule engine. It compares only the
features stored on the medication attached to that dose. Optional private pill or label reference
images are compared with a local normalized color-histogram intersection. The safety rule engine
maps the resulting score and explicit conflicts to a conservative result, and
`SafetyMessageService` supplies reviewed uncertainty language.

Verification never changes a dose-log status or medication record. Each attempt stores an
`ai_verification_event` linked to the patient, dose, medication, and captured image. Owners and
ACTIVE `FULL_ACCESS` caregivers may verify; other actors receive not found responses to avoid data
leakage.

## Notification Worker

Celery uses Redis as its broker. Celery Beat submits separate reminder and escalation scans every
minute. The worker uses the same async SQLAlchemy models and services as the API; it does not run a
second persistence implementation.

Before scanning reminders, the worker idempotently generates the current local day's dose logs for
all active patients using their IANA timezones. This allows reminders to work without requiring a
patient to open the app first.

The reminder lifecycle is configuration-controlled:

- At scheduled time, send `DOSE_REMINDER`.
- After the second-reminder offset, send `SNOOZE_REMINDER`.
- After the escalation threshold, send `CAREGIVER_ESCALATION` to ACTIVE linked caregivers.
- At the missed cutoff, mark a still-pending dose `MISSED` with `AUTO_MISSED` and send
  `MISSED_DOSE_ALERT` to ACTIVE linked caregivers.

`notification_events` is the durable delivery ledger. Partial unique indexes prevent duplicate
patient and caregiver events for the same dose, notification type, and channel. Redis distributed
locks prevent overlapping scans, while database uniqueness remains the final idempotency boundary.
Failed events retry independently of later dose status until the configured attempt limit.

`NotificationProvider` isolates push delivery. `ExpoPushNotificationProvider` is the real push
adapter. Provider errors and missing devices create `FAILED` events rather than fabricated
delivery. Device tokens are private and never returned by API responses or written to application
logs.

The mobile app registers Expo push tokens through `POST /api/v1/devices` after the user grants
notification permission. The backend returns a private device ID, which the mobile app stores in
Expo SecureStore so logout can call `DELETE /api/v1/devices/{id}` before clearing tokens. Push
tokens are never placed in `EXPO_PUBLIC_*` configuration or application logs.

Reminder notification taps use the backend-provided `dose_log_id` data field. When a reminder
opens the app, the client fetches the latest dose logs from the backend, reads the saved medication
details aloud using Expo Speech, then navigates to the verification flow for that dose. Client
notifications do not create dose logs, medication schedules, or confirmation state.

Local fallback reminders are allowed only for pending dose logs already fetched from the backend
and visible in the patient workflow. They are a user-visible convenience when the app has recent
backend data, not a scheduling source of truth.

Run API, worker, and scheduler as separate processes:

```bash
uvicorn app.main:app --port 8000
celery -A app.worker.celery_app worker --loglevel=INFO
celery -A app.worker.celery_app beat --loglevel=INFO
```

On Windows local development, use Celery's `--pool=solo` worker option. Production should run
separate supervised worker and Beat processes; do not embed Beat in every worker replica.

## Audit, Privacy, And Retention

`AuditService` writes durable `audit_logs` records in the same SQLAlchemy session as the business
operation. Request-scoped API dependencies inject the current request ID where available. Worker
actions have no request ID and use a null actor for system actions such as automatic missed-dose
marking.

Audit metadata is passed through the shared redaction utility and must remain low sensitivity.
Structured JSON logs also pass through the redaction utility before output, so known token, OCR,
password, push token, signed URL, and secret keys are replaced with `[REDACTED]`.

Privacy endpoints are authenticated and scoped to the current user:

- `GET /api/v1/privacy/export`
- `DELETE /api/v1/privacy/images/{image_id}`
- `POST /api/v1/privacy/revoke-caregiver/{link_id}`

The privacy export intentionally omits password hashes, refresh tokens, push tokens, storage object
keys, signed URLs, and raw OCR text. Image deletion goes through the configured `StorageProvider`
and then soft-deletes the database row; signed-read endpoints require active image rows, so deleted
images cannot receive new signed URLs.

`RetentionCleanupService` is the image-retention foundation. It deletes nothing unless
`STORAGE_RETENTION_DAYS` is configured. When enabled, it deletes expired private image objects and
soft-deletes their rows. It does not delete medication or dose history by default.

Future external integrations must be represented by typed application-facing interfaces and
injected at the composition root. Provider SDKs and provider-specific errors belong in adapter
modules. A missing production provider configuration must stop startup or return an explicit
unavailable response; it must never return invented data.

## Data and Service Boundaries

PostgreSQL is the durable system of record. Redis is reserved for ephemeral data such as cache,
rate-limit, or job-coordination state. Neither service is currently used to store medical records
or secrets. S3 stores private image objects only. New data flows require a privacy and retention
review.

## Error Handling

Errors exposed to clients must be useful without leaking credentials, internal stack traces, or
sensitive data. Logs should contain stable request correlation identifiers and must avoid
medication or personally identifiable data unless an approved logging policy explicitly permits it.

Every response receives an `X-Request-ID`. Application, HTTP, validation, readiness, and unexpected
errors use the same JSON envelope:

```json
{
  "error": {
    "code": "service_unavailable",
    "message": "Required services are unavailable",
    "request_id": "uuid",
    "details": {}
  }
}
```

Logs are emitted as single-line JSON. Request logs include request ID, method, path, status, and
duration. Sensitive request or response bodies are not logged.

## Alembic

Alembic configuration is in `backend/alembic.ini`; migration code and revisions live in
`backend/app/db/migrations`. Models must be imported from `app.models` so Alembic autogeneration
can discover their metadata.

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
