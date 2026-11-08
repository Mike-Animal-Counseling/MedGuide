# MedGuide AI

**Medication schedules, caregiver coordination, and dose history in one place.**

> MedGuide is an assistance tool, not medical advice. It does not diagnose conditions,
> prescribe medication, recommend dosages, or replace a qualified healthcare professional.

[Quick start](#quick-start) · [API guide](docs/API.md) · [Setup details](docs/SETUP.md) · [Release readiness](docs/PRODUCTION_READINESS_CHECKLIST.md)

## What it does

- **Organize** — create and manage user-confirmed medication records.
- **Schedule** — set medication schedules and review today's doses.
- **Track** — record taken, skipped, and needs-help dose states.
- **Coordinate** — invite caregivers with scoped access to linked patient records.

## Stack

FastAPI · PostgreSQL · Redis · Celery · Expo React Native

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
| [API guide](docs/API.md) | Supported operations and safety boundaries |
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
