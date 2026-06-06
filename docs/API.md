# API

The API is served under `/api/v1`. Protected endpoints require a valid Bearer access token.
Errors use a standard response envelope with `code`, `message`, and `request_id`.

## Medication Safety Boundary

Medication records store user-confirmed information. The API does not diagnose, prescribe,
recommend dosage, or generate medication instructions. Clients must clearly distinguish entered or
confirmed label text from medical advice.

## Medication Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/medications` | List the authenticated patient's non-deleted medications |
| `POST` | `/api/v1/medications` | Create a medication for the authenticated patient |
| `GET` | `/api/v1/medications/{id}` | Read an owned, non-deleted medication |
| `PATCH` | `/api/v1/medications/{id}` | Update an owned, non-deleted medication |
| `DELETE` | `/api/v1/medications/{id}` | Soft-delete an owned medication |

Patients access their own medication records without a query parameter. A caregiver with an ACTIVE
`MANAGE_MEDICATIONS` or `FULL_ACCESS` link may list or create records for a linked patient by
supplying `patient_id`; caregiver-created records must use the `CAREGIVER` source. Item updates and
deletes resolve the owning patient from the record and recheck the link. Admin accounts do not
bypass ownership.

Requests for records owned by another user return HTTP 404 to avoid disclosing record existence.
Deleted records are hidden from list and detail endpoints.

## OCR Confirmation

An OCR-sourced medication without `confirmed_by` is always stored with `active=false`, even if the
request asks for it to be active. Unconfirmed OCR records cannot store instructions. The owning
patient may confirm the record by setting `confirmed_by` to their own user ID, then provide
user-confirmed instructions and set `active=true`. PostgreSQL also enforces the active confirmation
rule with a check constraint.

Medication image fields contain private `uploaded_images` IDs only. Arbitrary image URLs are
rejected. Clients obtain short-lived signed read URLs through the upload API.

## Schedule Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/schedules` | Create a schedule for an owned medication |
| `GET` | `/api/v1/schedules` | List the authenticated patient's schedules |
| `GET` | `/api/v1/schedules/today` | List active schedules applicable today |
| `PATCH` | `/api/v1/schedules/{id}` | Update an owned schedule |
| `DELETE` | `/api/v1/schedules/{id}` | Deactivate an owned schedule |

Caregivers with any ACTIVE link may read schedules by supplying `patient_id`. Creating or changing
a linked patient's schedule requires `MANAGE_MEDICATIONS` or `FULL_ACCESS`. An inactive medication
cannot have an active schedule. `AS_NEEDED` schedules are stored for user reference but never
auto-generate dose logs.

## Dose Log Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/dose-logs` | List the authenticated patient's dose history |
| `GET` | `/api/v1/dose-logs/today` | Idempotently generate and list today's doses |
| `PATCH` | `/api/v1/dose-logs/{id}/confirm` | Confirm a pending dose |
| `PATCH` | `/api/v1/dose-logs/{id}/skip` | Mark a pending dose skipped |
| `PATCH` | `/api/v1/dose-logs/{id}/needs-help` | Mark a pending dose as needing help |

The confirmation window is configured by `DOSE_ON_TIME_WINDOW_MINUTES`. Confirmation within the
window is `TAKEN_ON_TIME`; confirmation after it is `TAKEN_LATE`. A confirmation earlier than the
allowed window is recorded as `VERIFICATION_FAILED` rather than accepted as taken. Resolved dose
logs cannot be changed through these endpoints. No endpoint deletes dose history.

## Caregiver Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/caregivers/invite` | Patient creates a caregiver invitation |
| `POST` | `/api/v1/caregivers/accept` | Matching caregiver account accepts an invitation token |
| `GET` | `/api/v1/caregivers/patients` | Caregiver lists ACTIVE linked patients |
| `GET` | `/api/v1/caregivers/patients/{patient_id}/today` | Read linked patient's schedules and today's dose logs |
| `GET` | `/api/v1/caregivers/patients/{patient_id}/dose-logs` | Read linked patient's dose logs |
| `PATCH` | `/api/v1/caregivers/links/{id}/revoke` | Owning patient revokes a link |

Permission levels are cumulative:

- `VIEW_ONLY`: read schedules and dose logs.
- `MANAGE_MEDICATIONS`: VIEW_ONLY plus create and edit medications and schedules.
- `FULL_ACCESS`: MANAGE_MEDICATIONS plus access to future AI verification events.

No AI verification event API currently exists, so the backend does not fabricate one. Every
caregiver request checks the ACTIVE link in PostgreSQL. Revocation therefore takes effect on the
next request. Invitations are bound to the normalized caregiver email, expire, and are stored only
as SHA-256 token hashes.

## Private Image Upload Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/uploads/signed-url` | Create a private image record and short-lived signed upload |
| `GET` | `/api/v1/uploads/{image_id}/signed-read-url` | Create a short-lived signed read URL |
| `DELETE` | `/api/v1/uploads/{image_id}` | Delete the provider object and soft-delete its record |

The upload request declares `purpose`, `content_type`, optional `size_bytes`, and optional
`patient_id` for an authorized caregiver. The backend generates the object key; clients cannot
choose bucket paths. Allowed content types and maximum size are configuration-controlled and are
included in S3 presigned POST conditions.

Owners may read and delete their images. Caregivers with an ACTIVE link may read medication label
and pill reference images; creating or deleting those images requires `MANAGE_MEDICATIONS`.
`VERIFICATION_IMAGE` access requires `FULL_ACCESS`. Unauthorized image IDs return not found.

Medication `label_image_id` must reference an owned, active `MEDICATION_LABEL`; `pill_image_id`
must reference an owned, active `PILL_REFERENCE`. Public bucket URLs are never stored or returned.

## Label OCR Endpoint

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/ai/scan-label` | Scan an authorized private medication-label image |

The request contains an `image_id`. Only the owner or an ACTIVE `FULL_ACCESS` caregiver may scan
the label. The response contains raw OCR text, visible candidate fields, provider confidence, and
`requires_confirmation=true`. It never saves a medication.

Images that fail decoding, minimum dimensions, or contrast checks return `UNREADABLE_IMAGE`
without calling the OCR provider. Readable scans return `LABEL_READ`, but this means text was
detected, not that the medication information is correct. Every response asks the user to confirm
the extracted information before saving.

## Medication Verification Endpoint

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/ai/verify-medication` | Compare a captured image with the currently due medication |

The request contains `dose_log_id`, a private `VERIFICATION_IMAGE` `image_id`, and either
`PILL_VERIFY` or `BOTTLE_VERIFY`. The dose must be pending and within the configured early or
recently-due window. Only the owning patient or an ACTIVE `FULL_ACCESS` caregiver may call it.

Results are `MATCH_LIKELY`, `MATCH_UNCERTAIN`, `NO_MATCH`, `UNREADABLE_IMAGE`, or
`CAREGIVER_REVIEW_REQUIRED`. Every response contains `requires_confirmation=true` and conservative,
voice-ready safety wording. Verification creates an audit event but never confirms, skips, or
otherwise changes the dose log.

## Device Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/devices` | Register or reactivate an authenticated user's Expo push device |
| `DELETE` | `/api/v1/devices/{id}` | Deactivate an owned device |

Registration requires an Expo push token and `IOS`, `ANDROID`, or `WEB` platform. A token may move
to the currently authenticated account when the same physical device changes users. Device tokens
are private credentials and are never returned by the API.

The reminder worker sends generic medication-assistance wording only. It does not include dosage
recommendations, prescribe medication, or claim that medication was taken.

## Privacy Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/privacy/export` | Export the authenticated user's own data |
| `DELETE` | `/api/v1/privacy/images/{image_id}` | Delete an owned private image object and soft-delete its record |
| `POST` | `/api/v1/privacy/revoke-caregiver/{link_id}` | Revoke an owned caregiver link |

Privacy export omits password hashes, refresh tokens, push tokens, storage object keys, signed
URLs, provider secrets, and raw OCR text. Deleted images cannot receive new signed read URLs.
