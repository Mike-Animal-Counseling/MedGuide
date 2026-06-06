# Deployment

MedGuide AI can be deployed only with real production providers. The backend must not use fake
OCR, fake vision, fake storage, fake notifications, fake authentication, or test mocks in
production.

Before deploying, review `docs/PLACEHOLDERS_AND_SECRETS.md` and provide all required production
values through the hosting platform secret manager.

## Production Safety Gates

`APP_ENV=production` refuses unsafe configuration:

- Localhost or placeholder PostgreSQL/Redis URLs.
- Missing, short, or placeholder JWT secret.
- Empty or wildcard CORS origins.
- Caregiver invite raw-token return.
- Local development storage.
- Test provider mocks.
- Storage provider other than real S3.
- OCR provider other than AWS Textract.
- Vision provider other than AWS Rekognition.
- Notification provider other than Expo push.
- Missing credentials for S3, Textract, Rekognition, or Expo push.

Production S3 buckets must be private. Do not use public buckets, public-read ACLs, public bucket
policies, or public object URLs. The backend stores private object references and generates
short-lived signed URLs.

## Container Images

Backend API image:

```bash
docker build -f backend/Dockerfile -t medguide-ai-backend:latest backend
```

Worker image:

```bash
docker build -f backend/Dockerfile.worker -t medguide-ai-worker:latest backend
```

Both images:

- Install production dependencies only.
- Run as a non-root `medguide` user.
- Load configuration from environment variables.
- Avoid checked-in secrets.

The API image exposes port `8000` and has a `/health` healthcheck.

## Local Development

Local development infrastructure is PostgreSQL and Redis only:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Apply migrations and start the backend:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Start a worker and beat scheduler when testing reminders:

```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO --pool=solo
celery -A app.worker.celery_app beat --loglevel=INFO
```

## Production Commands

Migration command:

```bash
alembic upgrade head
```

API command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Worker command:

```bash
celery -A app.worker.celery_app worker --loglevel=INFO
```

Scheduler command:

```bash
celery -A app.worker.celery_app beat --loglevel=INFO
```

Run exactly one scheduler per environment unless your platform provides an equivalent singleton
scheduled-job mechanism.

## Required Environment Variables

At minimum, production needs:

```text
APP_ENV=production
API_CORS_ORIGINS=https://your-mobile-or-web-origin.example
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=rediss://...
JWT_SECRET=...
STORAGE_PROVIDER=s3
S3_BUCKET=...
S3_REGION=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
OCR_PROVIDER=aws_textract
AWS_TEXTRACT_REGION=...
AWS_TEXTRACT_ACCESS_KEY_ID=...
AWS_TEXTRACT_SECRET_ACCESS_KEY=...
VISION_PROVIDER=aws_rekognition
AWS_REKOGNITION_REGION=...
AWS_REKOGNITION_ACCESS_KEY_ID=...
AWS_REKOGNITION_SECRET_ACCESS_KEY=...
NOTIFICATION_PROVIDER=expo
EXPO_PUSH_ACCESS_TOKEN=...
CAREGIVER_INVITE_TOKEN_RETURN_ENABLED=false
ENABLE_LOCAL_DEV_STORAGE=false
ENABLE_TEST_PROVIDER_MOCKS=false
```

See `docs/PLACEHOLDERS_AND_SECRETS.md` for the full configuration list, aliases, and ownership
checklist.

## Render Or Railway Outline

Use this path for a simple staging or early production deployment.

1. Create a managed PostgreSQL service.
2. Create a managed Redis service.
3. Create an S3 bucket with Block Public Access enabled.
4. Create least-privilege IAM credentials for S3, Textract, and Rekognition.
5. Configure Expo push access token.
6. Create an API web service from `backend/Dockerfile`.
7. Create a worker service from `backend/Dockerfile.worker`.
8. Create a scheduled or worker process for Celery Beat. If the platform cannot run a singleton
   beat process, use its scheduled job feature to trigger worker tasks instead.
9. Add all production environment variables through platform secrets.
10. Run `alembic upgrade head` as a release/migration command before the API serves traffic.
11. Verify `/health` and `/ready`.

Do not use platform-provided public disk storage for medication images. Medication images require
private object storage with signed URLs.

## AWS ECS Production Outline

Recommended AWS architecture:

- ECS Fargate service for the FastAPI API container.
- ECS Fargate service for Celery workers.
- One ECS scheduled task, singleton service, or EventBridge-triggered task for Celery Beat or
  equivalent scheduled jobs.
- RDS PostgreSQL for `DATABASE_URL`.
- ElastiCache Redis for `REDIS_URL` and Celery broker.
- Private S3 bucket for medication label, pill reference, and verification images.
- AWS Textract for label OCR.
- AWS Rekognition for visual feature extraction.
- Secrets Manager or SSM Parameter Store for all secrets.
- CloudWatch Logs with redaction and retention configured.
- ALB or API gateway terminating TLS and routing to the API service.

Security requirements:

- Run tasks in private subnets where possible.
- Restrict security groups to required service-to-service access.
- Use IAM task roles rather than static AWS access keys when the adapter supports it.
- Keep S3 Block Public Access enabled.
- Restrict S3 bucket CORS to deployed app origins.
- Encrypt RDS, ElastiCache, S3, logs, and secrets.
- Rotate JWT/provider secrets after exposure or according to policy.
- Do not log JWTs, raw OCR text, provider credentials, signed URLs, or push tokens.

Deployment flow:

1. Build and push backend and worker images to ECR.
2. Run database migrations as a one-off ECS task:

   ```bash
   alembic upgrade head
   ```

3. Deploy/update API service.
4. Deploy/update worker service.
5. Deploy/update scheduler.
6. Verify `/health`, `/ready`, reminder processing, OCR provider configuration, storage signed
   URLs, and notification delivery in staging before production rollout.

## Reference Compose

`docker-compose.prod.example.yml` is a reference only. It intentionally contains no secrets and
expects all production values to be provided through environment variables or a secret manager.

Validate it after exporting required placeholder values:

```bash
docker compose -f docker-compose.prod.example.yml config
```

Do not commit a populated production `.env` file.
