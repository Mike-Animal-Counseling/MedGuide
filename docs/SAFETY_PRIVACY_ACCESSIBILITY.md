# Safety, Privacy, And Accessibility

MedGuide AI is a medication assistance app. It is not a medical diagnosis, prescription, or dosage
recommendation system.

## Medical Safety

AI and OCR output must:

- state uncertainty;
- never claim certainty;
- never recommend or change dosage;
- never prescribe, discontinue, substitute, or select medication;
- never diagnose a condition;
- ask the user to confirm extracted medication information;
- tell users to contact a pharmacist, prescriber, caregiver, or emergency service when appropriate.

Safe wording examples:

```text
This appears to match your scheduled medication, but please confirm with the label or caregiver if unsure.
I cannot confirm this medication. Please do not rely on this result alone.
Please confirm the extracted medication information before saving.
```

Do not use wording like:

```text
This is definitely correct.
Take this now.
Recommended dosage.
100% sure.
```

## OCR Boundary

Label OCR extracts visible text only. It does not validate the medication and does not save a
medication automatically.

Rules:

```text
OCR result requires confirmation.
Bad images return UNREADABLE_IMAGE.
OCR text must not be logged.
```

## Verification Boundary

Medication verification compares the submitted image only with the currently due medication. It is
not universal pill identification.

Rules:

```text
The vision provider extracts features.
The backend rule engine returns the final safe result.
Dose logs are not changed by verification alone.
Every result still requires confirmation.
```

## Privacy

Sensitive data includes:

```text
OCR text
Medication instructions
JWT tokens
Refresh tokens
Password hashes
Push tokens
Signed URLs
Private image object keys
Provider secrets
```

Do not put these in logs, analytics, audit metadata, screenshots, or support tickets unless a
reviewed redaction rule covers them.

Privacy features:

```text
GET /api/v1/privacy/export exports only the authenticated user's data.
DELETE /api/v1/privacy/images/{image_id} deletes private image objects and soft-deletes records.
POST /api/v1/privacy/revoke-caregiver/{link_id} revokes caregiver access.
```

Deleted images cannot receive new signed read URLs.

## Audit Logging

Audit logs record important actions:

```text
registration
medication changes
schedule changes
dose confirmation or skip
caregiver invite, accept, revoke
AI verification event creation
notification sent or failed
image upload or deletion
privacy export
caregiver patient-data view
```

Audit metadata must stay low sensitivity.

## Logging And Observability

Backend logs are structured JSON and include request IDs. Production errors return generic
messages and must not expose stack traces or sensitive medication data.

Do not log:

```text
Authorization headers
JWTs
raw OCR text
medication label text
signed URLs
push tokens
provider credentials
```

Optional monitoring:

```text
SENTRY_DSN=
EXPO_PUBLIC_SENTRY_DSN=
```

If Sentry is missing, local development still works.

## Accessibility

Accessibility is a release requirement.

Baseline:

```text
Screen-reader friendly labels
Useful accessibility hints
Large touch targets
High contrast support
Large text support
Voice prompts for critical medication flows
No color-only status indicators
Plain safety wording
```

Mobile app choices:

```text
AccessibleButton
LargeActionButton
StatusCard
MedicationCard
VoicePrompt
AccessibilitySettingsScreen
```

Camera flows must provide a manual-entry fallback. OCR is assistance only and must never be
auto-saved.

Before release, manually test:

```text
iPhone VoiceOver
Android TalkBack
Large text
High contrast
Camera permission denied
Reminder voice prompt
Medication verification voice prompt
Caregiver dashboard
```
