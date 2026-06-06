# Infrastructure

Local infrastructure is defined in the repository root `docker-compose.yml` and includes only
PostgreSQL and Redis. It is for development and testing, not production deployment.

Production infrastructure must use secret-managed credentials, encrypted connections, backups,
monitoring, least-privilege access, and an approved data-retention policy.
