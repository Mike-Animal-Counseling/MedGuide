# Production security requirements

Production requires the existing validated provider configuration, strong JWT keys, explicit HTTPS frontend origins, managed PostgreSQL and authenticated TLS Redis. Redis request budgets are atomic across workers, bounded by connection/command deadlines, and deny API requests when the rate store fails. Never trust arbitrary forwarded client-address headers: configure Uvicorn/proxy trusted addresses precisely.

Authentication requests are limited by client address and normalized account, and auth bodies are capped at 8 KiB. AI and signed-upload creation also have per-client and global provider budgets. Apply provider-side spending caps and signed-upload size enforcement in S3. Keep object buckets private and restrict service credentials to required operations.

The backend has hashed full-platform `requirements.lock` and `requirements-prod.lock`. Use the production lock for deployment and the full development lock for CI, installing with `pip install --require-hashes -r <lock>`. Never put AWS keys, medical records, tokens or exported patient data in Git. Mobile dependencies use the stable Expo SDK's official compatibility list; run Expo's compatibility check and create fresh native builds when upgrading SDKs.

The application assists users and does not provide clinical diagnosis. Passing software/security tests is not medical, privacy or regulatory certification. Configure consent, retention, provider processing agreements, emergency resources, monitoring and backups for your actual jurisdiction before a public patient deployment.

Three unpublished upstream fixes are maintained as [licensed local backports](../mobile/vendor/SECURITY_BACKPORTS.md), with independent vulnerability regression tests. Do not drop these overrides until verified upstream fixed versions replace them.
