# Testing

Tests must verify real application behavior. Mocks are allowed only in test files or explicit test
fixtures and must not become production fallbacks.

`docs/PLACEHOLDERS_AND_SECRETS.md` is the configuration source of truth. `.env.example` lists
provider keys with empty values or safe local examples only; empty optional provider secrets are
normalized as missing configuration by backend settings. Production must configure real providers
or fail safely.

## Backend

```bash
cd backend
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy
pytest
```

`pytest` enforces backend coverage through `pyproject.toml`:

- coverage source: `app`
- terminal missing-line report
- `coverage.xml` report for CI artifacts
- minimum coverage: 85%

Run a focused file with coverage disabled only when debugging locally, for example
`pytest app/tests/test_auth.py --no-cov`. Full CI and pre-merge validation must use the default
coverage threshold.

Unit tests cover configuration validation, database foundations, API contracts, and safety
language. The database session and repository test uses isolated in-memory SQLite through the same
async SQLAlchemy APIs; it does not replace PostgreSQL integration testing.

Authentication tests cover registration, Argon2 hashing, email normalization, login failure,
unauthorized access, refresh rotation, logout revocation, role enforcement, profile updates, and
soft deletion. Test-only registration helpers live under `app/tests`; production modules do not
contain an authentication bypass.

Medication tests cover creation, owner-only listing, cross-user read/update/delete denial, invalid
payloads, soft deletion, caregiver denial, and OCR confirmation behavior. Alembic check verifies
that the OCR confirmation constraint and medication schema match the real PostgreSQL database.

Schedule tests cover daily, weekly, every-X-hours, bounded, inactive, and as-needed generation.
They also verify DST behavior, UTC normalization, idempotency, confirmation windows, state
transitions, cross-user denial, schedule deactivation, and preservation of historical dose logs.
Pure engine tests use fixed dates; API tests use the registered user's IANA timezone.

Caregiver tests cover invitation and email-bound acceptance, linked-patient listing, VIEW_ONLY and
MANAGE_MEDICATIONS enforcement, FULL_ACCESS inheritance, immediate revocation, expired and invalid
tokens, unlinked-patient isolation, and safe failure when invite delivery is not configured.
Invite tokens are returned only because the isolated test settings explicitly enable the
non-production token-return option.

Storage tests inject a recording provider only inside test fixtures. They cover signed upload/read
generation, content-type and size validation, S3 presigned conditions, production configuration
failure, owner and caregiver authorization, private medication image references, provider delete,
and database soft deletion. Production code never falls back to the test provider.

OCR pipeline tests inject a mock `OCRProvider` only inside test files and use generated in-memory
images for Pillow quality checks. They verify readable and unreadable paths, conservative field
extraction, mandatory confirmation, audit-event persistence, owner and FULL_ACCESS caregiver
authorization, missing-provider failure, and that OCR never auto-creates medication records.
The AWS Textract adapter is separately tested with an SDK client mock; production code has no fake
OCR fallback.

Medication verification tests inject a mock `VisionProvider` only inside tests. They cover
high/medium/low scoring, explicit mismatches, unreadable images, due-window enforcement, owner and
FULL_ACCESS caregiver authorization, cross-user denial, audit events, conservative safety
messages, and missing-provider failure. The AWS Rekognition adapter is separately tested with an
SDK client mock; production code has no fake vision fallback.

Notification tests inject a recording `NotificationProvider` only inside test files. They cover
device registration and deactivation, background dose generation, first and second reminders,
database idempotency across duplicate worker runs, failed-delivery retries, caregiver escalation,
retry after a dose becomes missed, missed-dose cutoff, provider status updates, safe missing-device
behavior, and missing production provider configuration. The Expo adapter is tested with an HTTP
client mock; production code never claims a push was sent without calling the configured provider.

Provider-mock rule: `ENABLE_TEST_PROVIDER_MOCKS` is documentation-only unless a test harness reads
it. Production modules must not branch on that flag to install fake OCR, fake vision, fake storage,
fake notifications, or fake authentication.

The backend test suite blocks raw socket connections by default. Any test that needs provider
behavior must inject a fake SDK/client inside the test. This prevents accidental calls to AWS,
Expo, OpenAI, Twilio, SendGrid, or other external services.

Run worker processes locally after PostgreSQL, Redis, and migrations are ready:

```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO --pool=solo
celery -A app.worker.celery_app beat --loglevel=INFO
```

Tests call `ReminderProcessor` directly with fixed times for determinism. Do not start Celery Beat
during the test suite.

Audit and privacy tests cover critical audit creation, user-only privacy export, unauthenticated
export rejection, image deletion through the privacy endpoint, signed-read denial after deletion,
caregiver revocation, redaction of sensitive values, and image retention cleanup only when
configured. Retention tests use the storage recording provider from test fixtures; production code
still requires the configured real storage provider.

Observability tests cover structured JSON redaction, request ID propagation, production-safe
unexpected-error responses, Sentry-disabled local development behavior, and metrics endpoint event
counts. Tests must not assert on raw OCR text or medication label text in observability payloads.

OpenAPI contract tests verify that `/openapi.json` generates, critical routes expose success
response schemas, standard error responses use the documented error envelope, and AI scan/verify
schemas include `safety_message`.

Export the API schema for mobile engineers and external reviewers:

```bash
cd backend
python scripts/export_openapi.py
```

Run local dependency readiness checks against PostgreSQL and Redis:

```bash
docker compose up -d
cd backend
alembic upgrade head
uvicorn app.main:app --port 8000
curl http://localhost:8000/ready
```

Readiness route unit tests replace health-check dependencies only inside test fixtures. Production
code always executes real PostgreSQL and Redis checks.

For manual authentication testing, configure a local `JWT_SECRET`, apply migrations, and use the
OpenAPI interface at `http://localhost:8000/docs`. Never use `.env.example` credentials in a shared
environment.

## Mobile

```bash
cd mobile
npm install
npm run lint
npm run typecheck
npm test
npm run test:coverage
```

React Native Testing Library tests should query the interface as a user or assistive technology
would. Keep snapshots focused; prefer behavioral and accessibility assertions.

`npm run test:coverage` enforces the mobile Jest thresholds configured in `mobile/package.json`:

- statements: 78%
- branches: 65%
- functions: 75%
- lines: 80%

Mobile tests cover:

- Required accessibility labels and press behavior for shared buttons.
- Login and registration client-side validation.
- Login flow through `AuthProvider` using a mocked API client and mocked SecureStore.
- Startup unauthorized responses clearing persisted tokens so the unauthenticated flow is shown.
- Logout clearing stored access and refresh tokens.
- Root navigation smoke rendering for the unauthenticated flow.
- API bearer-token attachment from Expo SecureStore.
- Home screen current-due medication display.
- Dose confirmation, skip, and needs-help endpoint calls.
- Voice prompt construction from saved instructions plus safety disclaimer.
- Camera permission denial fallback to manual medication entry.
- Signed upload URL, storage POST, and `/ai/scan-label` request flow with test mocks.
- Signed verification image upload and `/ai/verify-medication` request flow with test mocks.
- OCR confirmation screen behavior, including no medication creation before confirmation.
- Manual medication creation through the real API client wrapper.
- Medication list rendering, medication detail rendering, add-medication choices, and edit flow
  using backend `PATCH /api/v1/medications/{id}`.
- Medication verification result branches for `MATCH_LIKELY`, `MATCH_UNCERTAIN`,
  `CAREGIVER_REVIEW_REQUIRED`, and `UNREADABLE_IMAGE`.
- Safety-message speech and Mark as Taken visibility rules for verification.
- Retake behavior and Contact Caregiver mapping to the needs-help dose action.
- Expo push token registration through `/api/v1/devices`.
- Logout cleanup for the stored backend device ID.
- Notification tap parsing, backend dose refresh, speech reminder, and verification navigation.
- Accessible handling for denied notification permission.
- Caregiver linked-patient dashboard rendering.
- Caregiver patient today status and missed-dose alert rendering.
- Permission-based caregiver UI for VIEW_ONLY, MANAGE_MEDICATIONS, and FULL_ACCESS behavior.
- Caregiver invite acceptance and safe unauthorized-access errors.
- Critical patient workflow labels on home, schedule, and label-scanning screens.
- Accessibility settings for high contrast, large text, and patient caregiver revocation.
- Client error reporter redaction and Sentry-disabled no-op behavior.

Use `EXPO_PUBLIC_API_BASE_URL` for local manual testing. The app intentionally has no hardcoded
production URL and no production demo data. Test mocks for SecureStore, navigation, and auth
context live only in `mobile/src/tests`; global Jest mocks such as Expo Notifications live in
`mobile/jest.setup.ts` and are used only by tests.

## Infrastructure

```bash
docker compose config
docker compose up -d
docker compose ps
```

## CI Quality Gates

GitHub Actions are split by responsibility:

- `backend-ci.yml` runs backend install, lint, format check, type check, pytest coverage, and
  Alembic migration graph checks.
- `mobile-ci.yml` runs mobile install, TypeScript, lint, and Jest coverage checks.
- `security-ci.yml` runs secret scanning, committed `.env` rejection, Python dependency auditing,
  and npm dependency auditing.
- `docs-ci.yml` runs documentation/configuration checks and validates Docker Compose config.

Run the docs/config gate locally:

```bash
python scripts/check_docs_config.py
```

CI validates both applications, security gates, documentation consistency, and the Compose file.
Production readiness additionally requires integration, security, privacy, and manual
accessibility testing. See `docs/CI_CD.md` for workflow details and recommended branch protection
rules.
