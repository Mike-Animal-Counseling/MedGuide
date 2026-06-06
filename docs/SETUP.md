# Setup

This is the simple setup guide for MedGuide AI.

## Current Status

Done:

```text
[x] Project pushed to GitHub
[x] GitHub Actions are green
[x] Provider setup guide exists
```

Not done yet:

```text
[ ] Real PostgreSQL database
[ ] Real Redis
[ ] JWT secret
[ ] S3 private image storage
[ ] AWS Textract OCR
[ ] AWS Rekognition vision
[ ] Expo push token
```

## GitHub

Repository:

```text
https://github.com/Mike-Animal-Counseling/MedGuide.git
```

GitHub Actions should show these as green:

```text
Backend CI
Mobile CI
Security CI
Docs CI
```

Do not commit:

```text
.env
.env.local
.env.production
credentials.json
service-account.json
API key files
node_modules/
backend/.venv/
mobile/.expo/
coverage reports
```

Only `.env.example` should be committed.

## Provider Setup Order

Do these one at a time:

1. PostgreSQL
2. Redis
3. JWT secret
4. S3 private image storage
5. AWS Textract OCR
6. AWS Rekognition vision
7. Expo push notifications
8. Optional Sentry
9. Optional Twilio SMS
10. Optional SendGrid email

For the complete variable list, use `PLACEHOLDERS_AND_SECRETS.md`.

## 1. PostgreSQL

Purpose: stores users, medications, schedules, dose logs, uploads, audit logs, and events.

Simple hosted options:

```text
Neon
Supabase
Railway PostgreSQL
Render PostgreSQL
AWS RDS
```

Environment variable:

```text
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
```

Do not commit this value. Put it in local `.env` or the deployment platform secret manager.

## 2. Redis

Purpose: background jobs, reminders, queue support, and readiness checks.

Simple hosted options:

```text
Upstash Redis
Railway Redis
Render Redis
AWS ElastiCache
```

Environment variable:

```text
REDIS_URL=redis://USER:PASSWORD@HOST:6379/0
```

Use the exact URL your provider gives you.

## 3. JWT Secret

Purpose: signs access and refresh tokens.

Environment variables:

```text
JWT_SECRET=
JWT_SECRET_KEY=
```

Use the same strong random value for both. It should be at least 32 random characters.

## 4. S3 Private Storage

Purpose: private medication label images, pill reference images, and verification images.

Recommended provider:

```text
AWS S3
```

Environment variables:

```text
STORAGE_PROVIDER=s3
S3_BUCKET=
S3_BUCKET_NAME=
S3_REGION=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
STORAGE_SIGNED_URL_EXPIRE_SECONDS=300
SIGNED_URL_EXPIRATION_SECONDS=300
STORAGE_MAX_UPLOAD_BYTES=10485760
MAX_UPLOAD_SIZE_MB=10
```

Rules:

```text
Bucket must be private.
Do not expose public bucket URLs.
Use short-lived signed URLs only.
```

## 5. OCR

Current backend adapter:

```text
AWS Textract
```

Environment variables:

```text
OCR_PROVIDER=aws_textract
AWS_TEXTRACT_REGION=
AWS_TEXTRACT_ACCESS_KEY_ID=
AWS_TEXTRACT_SECRET_ACCESS_KEY=
```

Safety rule:

```text
OCR never auto-saves medication.
The user must confirm extracted fields before saving.
```

## 6. Vision Verification

Current backend adapter:

```text
AWS Rekognition
```

Environment variables:

```text
VISION_PROVIDER=aws_rekognition
AWS_REKOGNITION_REGION=
AWS_REKOGNITION_ACCESS_KEY_ID=
AWS_REKOGNITION_SECRET_ACCESS_KEY=
ENABLE_AI_VERIFICATION=true
```

Safety rule:

```text
The app compares an image only against the currently due medication.
It must not claim universal drug identification.
```

## 7. Expo Push

Purpose: medication reminders on mobile devices.

Environment variables:

```text
NOTIFICATION_PROVIDER=expo
EXPO_PUSH_ACCESS_TOKEN=
EXPO_ACCESS_TOKEN=
```

Mobile public variables:

```text
EXPO_PUBLIC_API_BASE_URL=
EXPO_PUBLIC_ENABLE_PUSH_NOTIFICATIONS=true
```

## Optional Later

Sentry:

```text
SENTRY_DSN=
EXPO_PUBLIC_SENTRY_DSN=
```

Twilio SMS:

```text
ENABLE_SMS_NOTIFICATIONS=false
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_PHONE=
```

SendGrid email:

```text
ENABLE_EMAIL_NOTIFICATIONS=false
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
```

Keep SMS and email disabled until real adapters, consent, and compliance review are ready.

## Next Small Step

Create a PostgreSQL database first. Recommended simple option: Neon.

After you create it, do not paste the full secret URL publicly. Tell Codex:

```text
I created PostgreSQL and have DATABASE_URL. Where do I put it?
```
