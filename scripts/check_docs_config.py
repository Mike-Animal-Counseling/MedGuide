from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
    "docs/ARCHITECTURE.md",
    "docs/PLACEHOLDERS_AND_SECRETS.md",
    "docs/AI_SAFETY.md",
    "docs/ACCESSIBILITY.md",
    "docs/TESTING.md",
    "docs/GITHUB_SETUP.md",
    "docs/CI_CD.md",
    "docs/DEPLOYMENT.md",
    "docs/OBSERVABILITY.md",
    "docs/PRODUCTION_READINESS_CHECKLIST.md",
]

REQUIRED_PLACEHOLDER_SECTIONS = [
    "Environment Overview",
    "Required Backend Environment Variables",
    "Storage Provider",
    "OCR Provider",
    "Vision Provider",
    "Notification Providers",
    "Mobile Environment Variables",
    "Feature Flags",
    "Explicit Rules",
    "Checklist",
]

REQUIRED_ENV_VARS = [
    "APP_ENV",
    "DATABASE_URL",
    "REDIS_URL",
    "JWT_SECRET_KEY",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    "CORS_ALLOWED_ORIGINS",
    "LOG_LEVEL",
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SENTRY_TRACES_SAMPLE_RATE",
    "API_BASE_URL",
    "STORAGE_PROVIDER",
    "S3_BUCKET_NAME",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_ENDPOINT_URL",
    "SIGNED_URL_EXPIRATION_SECONDS",
    "MAX_UPLOAD_SIZE_MB",
    "ALLOWED_IMAGE_CONTENT_TYPES",
    "OCR_PROVIDER",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AWS_TEXTRACT_REGION",
    "VISION_PROVIDER",
    "OPENAI_API_KEY",
    "VISION_MODEL_NAME",
    "EXPO_ACCESS_TOKEN",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_PHONE",
    "SENDGRID_API_KEY",
    "SENDGRID_FROM_EMAIL",
    "EXPO_PUBLIC_API_BASE_URL",
    "EXPO_PUBLIC_SENTRY_DSN",
    "EXPO_PUBLIC_APP_ENV",
    "ENABLE_SMS_NOTIFICATIONS",
    "ENABLE_EMAIL_NOTIFICATIONS",
    "ENABLE_LOCAL_DEV_STORAGE",
    "ENABLE_TEST_PROVIDER_MOCKS",
    "ENABLE_AI_VERIFICATION",
    "ENABLE_CAREGIVER_ESCALATION",
]


def main() -> int:
    errors: list[str] = []
    errors.extend(check_required_docs())
    errors.extend(check_placeholders_sections())
    errors.extend(check_env_example())
    errors.extend(check_tracked_env_files())

    if errors:
        print("CI documentation/configuration checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("CI documentation/configuration checks passed.")
    return 0


def check_required_docs() -> list[str]:
    return [f"Missing required document: {path}" for path in REQUIRED_DOCS if not (ROOT / path).is_file()]


def check_placeholders_sections() -> list[str]:
    path = ROOT / "docs/PLACEHOLDERS_AND_SECRETS.md"
    if not path.is_file():
        return ["docs/PLACEHOLDERS_AND_SECRETS.md is missing"]

    content = path.read_text(encoding="utf-8").lower()
    missing = [
        section
        for section in REQUIRED_PLACEHOLDER_SECTIONS
        if f"## {section}".lower() not in content
    ]
    return [f"PLACEHOLDERS_AND_SECRETS.md missing section: {section}" for section in missing]


def check_env_example() -> list[str]:
    path = ROOT / ".env.example"
    if not path.is_file():
        return [".env.example is missing"]

    keys = set(parse_env_keys(path))
    missing = [key for key in REQUIRED_ENV_VARS if key not in keys]
    return [f".env.example missing required variable: {key}" for key in missing]


def parse_env_keys(path: Path) -> list[str]:
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key:
            keys.append(key)
    return keys


def check_tracked_env_files() -> list[str]:
    tracked_files = run_git_ls_files()
    if tracked_files is None:
        return []

    invalid = [
        path
        for path in tracked_files
        if is_env_file(path) and not path.endswith(".env.example") and path != ".env.example"
    ]
    return [f"Non-example .env file is tracked: {path}" for path in invalid]


def run_git_ls_files() -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def is_env_file(path: str) -> bool:
    name = Path(path).name
    return name == ".env" or name.startswith(".env.")


if __name__ == "__main__":
    sys.exit(main())
