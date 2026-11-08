# MedGuide AI

**Scan a medication label, confirm it, get dose reminders, and check a pill or bottle photo against
the medication that is due — with caregiver oversight.**

MedGuide is a mobile medication companion for patients and the people who help them. It turns a
label photo into a medication record the patient confirms, schedules doses, sends reminders, and
compares a photo with the medication that is currently due before the dose is recorded.

[Quick start](#quick-start) · [API guide](docs/API.md) · [Setup details](docs/SETUP.md) · [Release readiness](docs/PRODUCTION_READINESS_CHECKLIST.md)

## How it works

1. **Scan** — photograph a medication label. OCR proposes fields; nothing is saved until the patient confirms them.
2. **Schedule** — set dose times and see today's schedule. As-needed schedules are reference-only and never generate dose logs.
3. **Check** — at dose time, take a photo of the pill or bottle. MedGuide compares it with the medication that is due and returns `MATCH_LIKELY`, `MATCH_UNCERTAIN`, `NO_MATCH`, `UNREADABLE_IMAGE`, or `CAREGIVER_REVIEW_REQUIRED`.
4. **Record** — confirm taken, skip, or mark needs help. A check never changes the dose log by itself.
5. **Coordinate** — invite a caregiver with view-only, manage-medications, or full-access permission; the patient can revoke access at any time.

## Safety boundary

MedGuide records information the patient has confirmed. It does not diagnose conditions, prescribe
medication, recommend dosages, or generate medication instructions. OCR text is not verified as
correct, and photo verification only compares an image with the medication that is currently due —
it cannot identify every medication. Every result requires the patient to confirm before a dose is
recorded.

## Features

- Label scanning with image-quality checks and explicit patient confirmation.
- Schedules and dose history with on-time, late, skipped, and needs-help states.
- Push reminders through Expo, plus a local fallback; reminder wording is generic and contains no dosage advice.
- Photo verification with conservative, voice-ready safety wording.
- Caregiver access with scoped permissions and a verification-review view.
- Accessibility: read-aloud prompts, large actions, high contrast, large text, and screen-reader labels.
- Privacy: private S3 uploads via signed URLs, data export, and image deletion.

## Stack

FastAPI · PostgreSQL · Redis · Celery · Expo React Native · AWS Textract and Rekognition adapters

## Quick start

Requires Python 3.12, Node.js 24+, and Docker.

```bash
cp .env.example .env        # set JWT_SECRET before using auth
docker compose up -d        # PostgreSQL and Redis
```

Backend:

```bash
cd backend
python -m venv .venv
# activate the venv for your shell
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Reminder worker and scheduler, each in its own terminal:

```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO --pool=solo
celery -A app.worker.celery_app beat --loglevel=INFO
```

Mobile app:

```bash
cd mobile
npm install
npm start
```

`http://localhost:8000/health` is the liveness endpoint. `/ready` succeeds only when
PostgreSQL and Redis respond.

## Quality checks

```bash
cd backend
ruff check . && ruff format --check . && mypy && pytest

cd mobile
npm run lint && npm run typecheck && npm test

docker compose config   # validates local infrastructure
```

## Documentation

| Document | Contents |
| --- | --- |
| [API guide](docs/API.md) | Endpoints, permission model, OCR confirmation, and dose/verification rules |
| [Setup](docs/SETUP.md) | GitHub and provider configuration, step by step |
| [Secrets and placeholders](docs/PLACEHOLDERS_AND_SECRETS.md) | Single source of truth for configuration |
| [Safety, privacy, accessibility](docs/SAFETY_PRIVACY_ACCESSIBILITY.md) | Read before adding AI-generated content |
| [Deployment](docs/DEPLOYMENT.md) | Render/Railway, AWS ECS, migrations, workers |
| [Production checklist](docs/PRODUCTION_READINESS_CHECKLIST.md) | Release status, credentials, and blockers |

## Production notes

Real S3, AWS Textract, AWS Rekognition, and Expo push adapters are included behind typed
interfaces and need real credentials before production use. Notification email/SMS,
generative AI, and external authentication providers are not selected. The application
must never fall back to fabricated provider output.

## Security

Read the [security policy](SECURITY.md) and
[production security requirements](docs/PRODUCTION_SECURITY.md) before deployment.
