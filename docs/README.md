# MedGuide AI Docs

Start here. The docs folder is intentionally kept small.

## Read In This Order

1. `SETUP.md`: GitHub status, provider setup order, and what you still need to configure.

2. `PLACEHOLDERS_AND_SECRETS.md`: The complete environment variable and secret checklist.

3. `TESTING.md`: Backend, mobile, Docker, and CI test commands.

4. `DEPLOYMENT.md`: How to deploy the backend API and worker safely.

5. `PRODUCTION_READINESS_CHECKLIST.md`: What is done, what is manual, and what blocks production.

## Reference Docs

- `API.md`: endpoint behavior and safety boundaries.
- `SAFETY_PRIVACY_ACCESSIBILITY.md`: medical safety, privacy, logging, and accessibility rules.

## Current Step

GitHub setup is complete and CI is green.

Provider setup is not complete yet. The next small task is to create a real PostgreSQL database
and set `DATABASE_URL` safely.
