# Privacy And Retention

MedGuide AI stores medication assistance data for the authenticated patient and linked caregivers.
It is not a medical record system of record, but its data can still be sensitive and must be
handled conservatively.

## Audit Logging

The `audit_logs` table records security and privacy relevant actions:

- user registration;
- medication, schedule, and dose state changes;
- caregiver invite, acceptance, revocation, and linked-patient views;
- image upload and deletion;
- AI verification event creation;
- notification sent and failed states;
- privacy export.

Audit metadata must stay low sensitivity. Do not store raw OCR text, JWTs, refresh tokens,
password hashes, push tokens, signed URLs, private object keys, or provider secrets in audit
metadata.

## Privacy Export

`GET /api/v1/privacy/export` returns the authenticated user's own data only. It intentionally omits
password hashes, refresh tokens, push tokens, private storage object keys, signed URLs, raw OCR
text, and provider secrets.

The endpoint is authenticated. A user cannot request another user's export by ID.

## Image Deletion

`DELETE /api/v1/privacy/images/{image_id}` deletes the provider object through the configured
storage provider and then soft-deletes the database record. Deleted images cannot be read through
the signed-read endpoint because all read paths require an active image record.

## Caregiver Revocation

`POST /api/v1/privacy/revoke-caregiver/{link_id}` reuses the caregiver revocation service. The
owning patient can revoke access at any time. Revoked caregivers lose access on the next request
because every caregiver request checks the ACTIVE link in PostgreSQL.

## Retention

Medication and dose history are not deleted by default. Automatic deletion of medication history
requires a separate clinical, legal, and product retention policy.

Image retention is optional and controlled by `STORAGE_RETENTION_DAYS`. When unset, the image
cleanup job deletes nothing. When configured, the worker deletes active private image objects older
than the configured number of days and soft-deletes their records. The cleanup job does not delete
medication or dose records.

Run cleanup through Celery Beat or call the worker task:

```bash
celery -A app.worker.celery_app beat --loglevel=INFO
celery -A app.worker.celery_app worker --loglevel=INFO
```

## Log Redaction

Structured logs pass through a redaction utility before serialization. Known sensitive keys and
Bearer token strings are replaced with `[REDACTED]`. This is a safeguard, not permission to log
sensitive request bodies.

Application code must not log raw OCR text, JWTs, refresh tokens, passwords, push tokens, signed
URLs, or private object keys.
