# MedGuide AI

MedGuide AI is a medication assistance application designed to help people understand and
organize medication information. It is an assistance tool only: it does not diagnose conditions,
prescribe medication, recommend dosages, or replace advice from a qualified healthcare
professional.

## Repository

```text
backend/            FastAPI API and database migrations
mobile/             Expo React Native application
docs/               Architecture, safety, accessibility, and operations guidance
infra/              Infrastructure notes
.github/workflows/  Continuous integration
```

## Prerequisites

- Python 3.12
- Node.js 22.13+
- Docker with Docker Compose

## Local Setup

1. Create local configuration:

   ```bash
   cp .env.example .env
   ```

   Replace `JWT_SECRET` before using authentication outside an isolated local environment. All
   required secrets and provider placeholders are centralized in
   [docs/PLACEHOLDERS_AND_SECRETS.md](docs/PLACEHOLDERS_AND_SECRETS.md).

2. Start PostgreSQL and Redis:

   ```bash
   docker compose up -d
   ```

3. Install and run the backend:

   ```bash
   cd backend
   python -m venv .venv
   # Activate .venv for your shell
   python -m pip install -e ".[dev]"
   uvicorn app.main:app --reload
   ```

4. Run the reminder worker and scheduler in separate terminals:

   ```bash
   cd backend
   celery -A app.worker.celery_app worker --loglevel=INFO --pool=solo
   celery -A app.worker.celery_app beat --loglevel=INFO
   ```

   The `--pool=solo` option is for Windows local development. Use supervised worker processes in
   production.

5. Install and run the mobile app in another terminal:

   ```bash
   cd mobile
   npm install
   npm start
   ```

The API liveness endpoint is available at `http://localhost:8000/health`. The readiness endpoint
at `http://localhost:8000/ready` returns success only when PostgreSQL and Redis respond.

## GitHub Setup

Before pushing the project, follow [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md). It explains how
to avoid committing secrets, push the repo, and confirm GitHub Actions.

## Quality Commands

Backend:

```bash
cd backend
ruff check .
ruff format --check .
mypy
pytest
alembic upgrade head
```

Mobile:

```bash
cd mobile
npm run lint
npm run typecheck
npm test
```

Validate local infrastructure configuration:

```bash
docker compose config
```

## Production Requirements

The backend includes real S3, AWS Textract, AWS Rekognition, and Expo push adapters behind typed
interfaces. They require real credentials before production use. Notification email/SMS,
generative AI, and external authentication providers are not selected. Production must never fall
back to fabricated provider output. Treat
[docs/PLACEHOLDERS_AND_SECRETS.md](docs/PLACEHOLDERS_AND_SECRETS.md) as the single source of truth
for secrets, placeholder values, provider setup, and production readiness checklists.

Review [docs/AI_SAFETY.md](docs/AI_SAFETY.md) before introducing any AI-generated medication
content.

Medication endpoint behavior and safety boundaries are documented in [docs/API.md](docs/API.md).
Privacy, audit logging, and retention behavior are documented in
[docs/PRIVACY_AND_RETENTION.md](docs/PRIVACY_AND_RETENTION.md).
Deployment assets, migration commands, worker commands, Render/Railway notes, and AWS ECS
production guidance are documented in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
The current release readiness status, manual tasks, required credentials, and deployment blockers
are tracked in [docs/PRODUCTION_READINESS_CHECKLIST.md](docs/PRODUCTION_READINESS_CHECKLIST.md).
