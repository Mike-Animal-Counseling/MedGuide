# CI/CD

MedGuide AI uses GitHub Actions quality gates for backend, mobile, security, and documentation
checks. These workflows validate source behavior only; they do not deploy or configure production
provider credentials.

## Workflows

| Workflow | Purpose | Required gates |
| --- | --- | --- |
| `backend-ci.yml` | Backend API quality | Install Python dependencies, `ruff check`, `ruff format --check`, `mypy`, `pytest` with coverage, Alembic migration graph check |
| `mobile-ci.yml` | Expo mobile quality | Install Node dependencies, TypeScript check, ESLint, Jest with coverage |
| `security-ci.yml` | Secret and dependency safety | Gitleaks scan, committed `.env` rejection, Python dependency audit, npm dependency audit |
| `docs-ci.yml` | Documentation and config consistency | Required docs exist, placeholder sections exist, `.env.example` contains required variables, Docker Compose config parses |

All workflows run on pull requests and pushes to `main`. Backend, mobile, and docs workflows use
path filters so unrelated changes do not run unnecessary jobs. Security runs for every pull
request and `main` push.

## Coverage Gates

Backend coverage is enforced by `backend/pyproject.toml`:

- coverage source: `app`
- XML artifact: `backend/coverage.xml`
- minimum total coverage: 85%

Mobile coverage is enforced by `mobile/package.json`:

- statements: 78%
- branches: 65%
- functions: 75%
- lines: 80%

Coverage artifacts are uploaded by GitHub Actions for review.

## Secret Gates

Production secrets must never be committed. `security-ci.yml` enforces this with:

- Gitleaks secret scanning.
- A git-tracked-file check that rejects `.env`, `.env.local`, `.env.production`, and other
  non-example env files.
- `.env.example` remains the only committed env file and must contain placeholders or safe local
  examples only.

Real production values belong in the deployment secret manager. See
`docs/PLACEHOLDERS_AND_SECRETS.md` for the owner-provided values that still need configuration
before production use.

## Dependency Gates

Backend dependency checks install production Python dependencies and run `pip-audit`.
Mobile dependency checks run `npm audit --omit=dev --audit-level=high`.

These checks are intentionally conservative. If a vulnerability is found, upgrade or pin the
dependency with a documented rationale. Do not silence dependency gates without a security review.

## Migration Gate

`backend-ci.yml` checks Alembic migration graph metadata with `alembic heads` and
`alembic history --verbose`. Online migration execution requires a configured PostgreSQL database
and should be run in local integration testing, staging, and deployment pipelines:

```bash
cd backend
alembic upgrade head
```

The CI graph check catches broken migration imports or multiple unexpected heads without requiring
a fake CI database.

## Docs Gate

`docs-ci.yml` runs `scripts/check_docs_config.py`. The script verifies:

- Required docs exist.
- `docs/PLACEHOLDERS_AND_SECRETS.md` contains required configuration sections.
- `.env.example` includes required backend, storage, OCR, vision, notification, mobile, and feature
  flag variables.
- No non-example `.env` file is tracked by git.

When adding a provider, environment variable, or secret, update
`docs/PLACEHOLDERS_AND_SECRETS.md`, `.env.example`, and this gate if the item is required.

## Branch Protection

Recommended required status checks before merging to `main`:

- `Backend Quality Gates`
- `Mobile Quality Gates`
- `Secret And Environment File Gates`
- `Backend Dependency Vulnerability Check`
- `Mobile Dependency Vulnerability Check`
- `Documentation And Configuration Gates`

Production deployment should remain separate from these CI workflows until real provider
credentials, hosting targets, approval rules, rollback procedures, and environment-specific
secrets are configured.
