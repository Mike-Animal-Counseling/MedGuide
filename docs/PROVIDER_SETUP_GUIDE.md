# Provider Setup Guide

This guide tells you what real services MedGuide AI needs before staging or production. It does
not contain real secrets. Put real values in your deployment platform secret manager, not in git.

For the complete variable list, use `docs/PLACEHOLDERS_AND_SECRETS.md`.

## Simple Order

Do these in this order:

1. PostgreSQL database
2. Redis
3. JWT secret
4. S3 private image storage
5. AWS Textract for OCR
6. AWS Rekognition for medication image verification
7. Expo push notifications
8. Optional Sentry monitoring
9. Optional Twilio SMS
10. Optional SendGrid email

For local development, PostgreSQL and Redis can run through Docker Compose. The external providers
can stay unconfigured until you test those specific features.

## Required For Basic Backend

### PostgreSQL

Purpose: stores users, medications, schedules, dose logs, uploads, audit logs, and events.

Local:

```bash
docker compose up -d postgres
```

Production options:

```text
Neon
Supabase
AWS RDS
Railway PostgreSQL
Render PostgreSQL
```

Environment variable:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
```

Production rule: do not use `localhost`, `change-me`, or shared test credentials.

### Redis

Purpose: readiness check, worker queue support, reminders, and background jobs.

Local:

```bash
docker compose up -d redis
```

Production options:

```text
Upstash Redis
AWS ElastiCache
Railway Redis
Render Redis
```

Environment variable:

```text
REDIS_URL=redis://USER:PASSWORD@HOST:6379/0
```

Use the exact URL format your provider gives you.

### JWT Secret

Purpose: signs access and refresh tokens.

Environment variables:

```text
JWT_SECRET=<at least 32 random characters>
JWT_SECRET_KEY=<same value, compatibility alias>
```

Generate a long random value. Do not use words, names, or examples from documentation.

## Required For Image Uploads

### S3 Private Storage

Purpose: stores medication label images, pill reference images, and verification images.

Recommended provider:

```text
AWS S3
```

Required setup:

1. Create a private S3 bucket.
2. Enable Block Public Access.
3. Create an IAM user or role with least-privilege bucket access.
4. Allow signed upload CORS only from your deployed app origins.
5. Never make the bucket public.

Environment variables:

```text
STORAGE_PROVIDER=s3
S3_BUCKET=<bucket name>
S3_BUCKET_NAME=<same bucket name, compatibility alias>
S3_REGION=<region>
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
STORAGE_SIGNED_URL_EXPIRE_SECONDS=300
SIGNED_URL_EXPIRATION_SECONDS=300
STORAGE_MAX_UPLOAD_BYTES=10485760
MAX_UPLOAD_SIZE_MB=10
STORAGE_ALLOWED_CONTENT_TYPES=image/jpeg,image/png,image/webp
ALLOWED_IMAGE_CONTENT_TYPES=image/jpeg,image/png,image/webp
```

Production rule: signed URLs must be short-lived, and the app must store private object keys, not
public bucket URLs.

## Required For Label Scanning

### AWS Textract OCR

Purpose: reads visible text from medication label images.

Current backend adapter:

```text
AWS Textract
```

Environment variables:

```text
OCR_PROVIDER=aws_textract
AWS_TEXTRACT_REGION=<region>
AWS_TEXTRACT_ACCESS_KEY_ID=
AWS_TEXTRACT_SECRET_ACCESS_KEY=
```

Important behavior:

```text
OCR never auto-saves medication.
OCR result always requires user confirmation.
Missing production OCR config fails safely.
```

Google Vision is documented as a future option, but the current backend does not select a Google
Vision adapter.

## Required For Medication Verification

### AWS Rekognition Vision

Purpose: extracts visual features from the user's submitted medication image. The backend then
compares those features only against the medication currently due for that user.

Current backend adapter:

```text
AWS Rekognition
```

Environment variables:

```text
VISION_PROVIDER=aws_rekognition
AWS_REKOGNITION_REGION=<region>
AWS_REKOGNITION_ACCESS_KEY_ID=
AWS_REKOGNITION_SECRET_ACCESS_KEY=
ENABLE_AI_VERIFICATION=true
```

Safety rule:

```text
The vision provider does not make the final medical decision.
The backend rule engine returns safe wording like "appears to match" or "cannot confirm".
```

OpenAI vision variables are present for future adapters, but the current production adapter is AWS
Rekognition.

## Required For Push Reminders

### Expo Push

Purpose: sends medication reminder notifications to registered mobile devices.

Environment variables:

```text
NOTIFICATION_PROVIDER=expo
EXPO_PUSH_ACCESS_TOKEN=<Expo access token>
EXPO_ACCESS_TOKEN=<same value, compatibility alias if needed>
```

Mobile public variables:

```text
EXPO_PUBLIC_ENABLE_PUSH_NOTIFICATIONS=true
EXPO_PUBLIC_API_BASE_URL=<your API URL>
```

Production rule: the backend must call the real Expo provider. It must not pretend a push was sent.

## Optional Providers

### Sentry

Purpose: error monitoring.

Environment variables:

```text
SENTRY_DSN=<backend DSN>
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0
EXPO_PUBLIC_SENTRY_DSN=<mobile public DSN>
```

Keep sensitive medication text out of logs and analytics.

### Twilio SMS

Purpose: optional SMS caregiver escalation.

Current status:

```text
Optional. Keep disabled until a real SMS adapter, consent flow, and compliance review exist.
```

Environment variables:

```text
ENABLE_SMS_NOTIFICATIONS=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_PHONE=
```

### SendGrid Email

Purpose: optional email notifications or caregiver invite delivery.

Current status:

```text
Optional. Keep disabled until a real email adapter and sender verification exist.
```

Environment variables:

```text
ENABLE_EMAIL_NOTIFICATIONS=false
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
```

## Mobile Configuration

The mobile app must not contain private secrets.

Use only public Expo variables:

```text
EXPO_PUBLIC_API_BASE_URL=<backend API URL>
EXPO_PUBLIC_APP_ENV=development | staging | production
EXPO_PUBLIC_ENABLE_PUSH_NOTIFICATIONS=true
EXPO_PUBLIC_ENABLE_LOCAL_REMINDERS=true
EXPO_PUBLIC_ENABLE_AI_VERIFICATION=true
EXPO_PUBLIC_ENABLE_CAREGIVER_DASHBOARD=true
EXPO_PUBLIC_SENTRY_DSN=<optional public Sentry DSN>
```

Never put these in `EXPO_PUBLIC_*`:

```text
JWT secrets
Database URLs
Redis URLs
S3 keys
AWS keys
Expo push access token
Twilio keys
SendGrid keys
```

## GitHub Secrets

Current GitHub Actions do not need real provider secrets. They run tests with test-only mocks and
local checks.

Put deployment secrets in your hosting platform, not in the repo.

Only add secrets to GitHub Actions later if a workflow truly needs them, such as a deployment
workflow.

## First Staging Checklist

Before staging:

```text
[ ] Managed PostgreSQL URL
[ ] Managed Redis URL
[ ] Strong JWT secret
[ ] Private S3 bucket
[ ] S3 access key and secret
[ ] AWS Textract credentials
[ ] AWS Rekognition credentials
[ ] Expo push access token
[ ] API CORS origins
[ ] Mobile API base URL
```

Can wait:

```text
[ ] Sentry
[ ] Twilio SMS
[ ] SendGrid email
```

## What To Tell Codex Later

When you start registering providers, give Codex the provider name and say what step you are on.
For example:

```text
I created a Neon PostgreSQL database. Help me fill the correct DATABASE_URL names without exposing secrets.
```

Do not paste real secrets into chat unless you are comfortable with that environment. Prefer
saying which variable you have and letting Codex tell you where it belongs.
