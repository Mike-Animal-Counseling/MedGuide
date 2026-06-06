# Observability

MedGuide AI must be observable in production without leaking medication, identity, credential, or
image data. Logs, metrics, and error reports are operational tools; they are not medical records
or analytics sinks.

## Backend Logging

Backend logs use structured JSON through `app.core.logging.JsonFormatter`.

Every request receives an `X-Request-ID`:

- A valid incoming UUID request ID is preserved.
- A new UUID is generated when the header is absent or invalid.
- The request ID is added to API error responses and response headers.

Request completion logs include:

- `request_id`
- HTTP method
- request path
- status code
- duration in milliseconds

Unexpected errors return a generic `internal_server_error` response. Production responses must not
include stack traces, exception messages, OCR text, medication instructions, tokens, signed URLs,
or provider payloads.

## Redaction

Backend redaction is centralized in `app.core.redaction.redact_sensitive`.

Do not log:

- JWT access or refresh tokens.
- Authorization headers.
- Passwords or password hashes.
- Invite tokens.
- S3 signed upload/read URLs.
- Push tokens.
- Raw OCR text or medication label text.
- Medication instructions or free-text user notes unless a reviewed redaction rule covers them.
- Provider credentials or API keys.

Safe log metadata examples:

- `request_id`
- status code
- route path
- event name
- notification type
- verification result enum
- confidence score
- internal resource UUIDs when needed for debugging

## Sentry

Backend Sentry is optional and configured by environment:

```text
SENTRY_DSN=
SENTRY_ENVIRONMENT=
SENTRY_TRACES_SAMPLE_RATE=0
```

If `SENTRY_DSN` is missing, local development and tests continue without Sentry. If it is set,
the backend initializes `sentry-sdk` with `send_default_pii=false`.

Mobile error reporting is behind:

```text
EXPO_PUBLIC_SENTRY_DSN=
```

The mobile app uses a safe error-reporting abstraction. It redacts sensitive client context and
does not send raw medication label text, OCR text, or raw JavaScript error messages to client
analytics.

## Metrics

The backend exposes a foundation metrics endpoint:

```text
GET /metrics
```

It returns process-local counters:

```json
{
  "counters": {
    "ai_scan_completed|result=LABEL_READ": 1
  }
}
```

Tracked events:

- `reminder_sent`
- `dose_confirmed`
- `dose_missed`
- `ai_scan_completed`
- `ai_verify_completed`
- `caregiver_escalation_sent`
- `notification_failed`

Metrics tags are intentionally low-cardinality. Do not add medication names, OCR text, patient
emails, medication instructions, image object keys, signed URLs, push tokens, or provider raw
responses as tags.

The current in-process metrics service is a foundation. A production deployment can replace the
`MetricsService` implementation with Prometheus, OpenTelemetry, CloudWatch, or another managed
metrics backend without changing business logic.

## Mobile Error Reporting

The mobile `ErrorBoundary` displays a generic accessible message:

```text
Something went wrong. Please restart the app or try again later.
```

It reports errors through `src/observability/errorReporter.ts`. The reporter redacts keys such as
`ocr_text`, `label_text`, `authorization`, `token`, `signed_url`, and `push_token`.
When Sentry is configured, the client sends a Sentry envelope with a generic exception value rather
than the raw error message.

Do not add medication names, label OCR output, image URLs, or user-entered medication instructions
to mobile analytics events.

## Operational Notes

- Correlate user support incidents with `request_id`, audit logs, and resource IDs.
- Use audit logs for privacy-sensitive user actions; use metrics for aggregate operational health.
- Keep Sentry traces sampling low until PHI exposure and retention are reviewed.
- Configure log retention, access control, and export restrictions before production use.
