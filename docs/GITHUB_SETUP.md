# GitHub Setup

This is the simple path for putting MedGuide AI on GitHub safely.

## Step 1: Check Secrets First

Before pushing, make sure these files are not committed:

```text
.env
.env.local
.env.production
service-account.json
credentials.json
API key files
node_modules/
backend/.venv/
mobile/.expo/
coverage reports
```

Only `.env.example` should be committed. It must contain placeholders only, never real secrets.

## Step 2: Create A GitHub Repo

On GitHub:

1. Click `New repository`.
2. Name it `medguide-ai`.
3. Keep it private until you are ready to share it.
4. Do not add a README, `.gitignore`, or license on GitHub if they already exist locally.
5. Copy the repo URL.

## Step 3: Commit Locally

From the project root:

```bash
git init
git status
git add .
git commit -m "Initial MedGuide AI foundation"
git branch -M main
```

If `git status` shows real secret files, stop and fix `.gitignore` before committing.

## Step 4: Push To GitHub

Replace the URL with your repo URL:

```bash
git remote add origin https://github.com/YOUR_USERNAME/medguide-ai.git
git push -u origin main
```

## Step 5: Check GitHub Actions

After pushing, open the GitHub repo and click `Actions`.

You should see these workflows:

```text
Backend CI
Mobile CI
Security CI
Docs CI
```

They should pass before you treat the repo as ready.

## Step 6: Add Branch Protection

In GitHub:

1. Go to `Settings`.
2. Go to `Branches`.
3. Add a rule for `main`.
4. Require pull request review if working with other people.
5. Require status checks to pass before merge.
6. Select backend, mobile, security, and docs checks once they have run at least once.

## Step 7: Where Secrets Go

Do not put production secrets into GitHub source code.

Use deployment platform secrets for:

```text
DATABASE_URL
REDIS_URL
JWT_SECRET
S3 credentials
AWS Textract credentials
AWS Rekognition credentials
Expo push token
Sentry DSN
Twilio keys
SendGrid keys
```

GitHub Actions currently run tests and checks without real provider credentials. If future CI jobs
need secrets, add them under GitHub `Settings > Secrets and variables > Actions`.

## Current Reminder

The CI files exist in this repo, but GitHub Actions will not actually run until the project is
pushed to GitHub.
