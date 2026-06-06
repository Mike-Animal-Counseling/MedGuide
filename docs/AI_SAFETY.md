# AI Safety

MedGuide AI is a medication assistance product, not a medical diagnosis or prescription system.

## Required Boundaries

Any future AI-generated content must:

- clearly state uncertainty and avoid claims of certainty;
- never recommend or change a dosage;
- never prescribe, discontinue, substitute, or select medication;
- never diagnose a condition or claim to replace a healthcare professional;
- encourage users to contact a pharmacist, prescriber, or emergency service when appropriate;
- preserve source provenance where factual medication information is summarized;
- be clearly identified as AI-generated and subject to review.

## High-Risk Situations

Potential overdose, severe adverse reactions, self-harm, poisoning, dangerous interactions, or
other urgent situations must use reviewed escalation language and direct users to appropriate
emergency or poison-control resources. AI output must not attempt to resolve the emergency.

## Engineering Controls

AI integrations require a typed provider interface, input/output validation, safety policy tests,
auditability, timeout and outage behavior, and monitoring. Missing credentials or unavailable
providers must produce a clear error, never fabricated content.

Prompts and model output are untrusted data. Do not allow either to directly execute tools, mutate
medical records, or trigger user-facing actions without validated authorization and controls.

## Label OCR Boundary

Label OCR extracts visible text into candidate fields only. It does not validate that a label is
correct for the user, prescribe medication, infer missing dosage, or create a medication record.
Every successful scan returns `requires_confirmation=true` and the fixed safety message:

> Please confirm the extracted medication information before saving.

The parser preserves visible label lines for dosage, instructions, and frequency rather than
turning them into recommendations. Empty OCR results and images that fail decoding, minimum
dimensions, or contrast checks return `UNREADABLE_IMAGE`. Users should retake the image or confirm
the label manually.

Each scan creates a `LABEL_OCR` verification event for auditability. A readable result is recorded
as `CAREGIVER_REVIEW_REQUIRED`, not as a verified medication match. OCR text and candidate fields
are sensitive medication data and must not be placed in application logs.

## Scheduled Medication Verification Boundary

Medication verification compares a captured private image only with the medication attached to a
currently or recently due dose log. It is not universal pill identification and must never be
presented as proof that a medication is safe to take.

The vision provider extracts observable labels and visible text. A deterministic backend scorer,
not the provider, compares available color, shape, imprint, and optional private reference-image
similarity. Weights are color `0.25`, shape `0.25`, imprint `0.35`, and reference similarity
`0.15`; unavailable evidence is excluded from the denominator.

- `>= 0.85`: `MATCH_LIKELY`, with explicit uncertainty and confirmation language.
- `0.60` through `0.8499`: `MATCH_UNCERTAIN`.
- `< 0.60` with an explicit observed conflict: `NO_MATCH`.
- `< 0.60` without explicit conflict: `CAREGIVER_REVIEW_REQUIRED`.
- Failed quality checks: `UNREADABLE_IMAGE` without calling the vision provider.

Every result requires confirmation, stores an auditable `ai_verification_event`, and leaves the
dose log unchanged. A low score never recommends a substitute, and a high score never authorizes
medical action or claims certainty.
