# Accessibility

Accessibility is a release requirement for MedGuide AI.

## Baseline

- Target WCAG 2.2 AA where applicable.
- Use semantic roles, accessible names, and logical focus order.
- Support screen readers, keyboard navigation, dynamic text, and reduced motion.
- Do not rely on color alone to communicate meaning.
- Maintain sufficient text and control contrast.
- Use plain language, especially for safety and medication information.
- Make touch targets at least 44 by 44 logical pixels.
- Announce errors and status changes without unexpectedly moving focus.

## Verification

Automated tests should assert key roles, names, and safety messages. Releases also require manual
checks with VoiceOver and TalkBack, large text settings, reduced motion, and representative color
contrast tooling. Automated tests do not replace assistive-technology testing.

## Mobile Choices

The Expo app starts from accessibility-first primitives instead of ad hoc buttons and cards:

- `AccessibleButton` and `LargeActionButton` require both `accessibilityLabel` and
  `accessibilityHint`.
- `StatusCard`, `MedicationCard`, and screen headings expose semantic roles and readable labels.
- Critical medication actions use large touch targets and plain, safety-first wording.
- Dose actions on the Today Schedule screen expose individual labels for confirm, skip, and needs
  help so screen-reader users can reach them without extra navigation.
- `AccessibilitySettingsScreen` provides device-local high contrast and large text preferences.
- `VoicePrompt` uses Expo Speech only for user-facing safety prompts; it does not create medical
  advice or certainty claims.

Every patient-facing medication workflow keeps the same safety boundary in visible text and spoken
prompts: MedGuide assists review, requires confirmation when OCR is used, and does not prescribe,
recommend dosage, or replace a clinician.

For dose confirmation, speech output is built from the saved user-confirmed medication instruction
plus a fixed safety disclaimer. The app does not speak generated dosage advice or inferred
instructions.

Medication verification speech follows the same boundary. Before opening the camera, the app reads
the saved medication name, dosage text, and user-confirmed instruction, followed by a reminder that
MedGuide cannot confirm medication with certainty. After backend verification, the app speaks the
backend safety message exactly.

## Notification Voice Behavior

Notification permission is requested through a visible `Enable reminders` control with an
accessible label and hint. If permission is denied, the app states that reminders can still be
checked manually rather than blocking medication access.

When a user opens the app from a reminder, MedGuide fetches the latest backend dose data before
speaking. The spoken reminder uses only saved medication details and the safety disclaimer; it does
not invent schedule data, dosage instructions, or certainty language. Notification taps navigate
to medication verification so the main action remains reachable with minimal navigation.

## Caregiver Dashboard

Caregiver cards expose linked patients as buttons with patient names, email context, and permission
level. Patient detail screens announce missed dose alerts before the longer dose list. Permission
limits are shown in plain language, so caregivers understand why management or verification review
actions may be unavailable.

Invite acceptance and caregiver revocation forms have explicit labels and hints. Revocation remains
a backend operation; the UI does not imply access was removed until the backend confirms it.

## Camera And OCR Guidance

Label scanning is optional assistance. Users can always choose manual entry before or after a
camera permission denial, provider outage, unreadable image, or uncertain OCR result.

For blind and low-vision users:

- The Scan Label screen announces the purpose of the camera step before requesting permission.
- If camera permission is denied, the screen exposes a direct `Enter medication manually` action.
- Camera instructions use plain text that can be read by screen readers.
- Verification camera guidance is available as a repeatable speech prompt: "Place the pill or
  medication bottle in the center of the camera."
- OCR output is never auto-saved; extracted fields are read aloud with the safety message and then
  presented in editable fields for confirmation.
- Raw OCR text is displayed for review, but users are reminded that OCR may be wrong and must be
  checked against the medication label, prescription, or caregiver.

Future camera work should add non-visual framing feedback only when it is based on real device
signals. Do not add fake image-quality or OCR success messages.

Before release, run manual checks on iOS VoiceOver and Android TalkBack, including login,
registration, today's schedule, medication details, label scanning, verification, and caregiver
views. Confirm that focus order follows the visual order and that all critical actions are
announced with useful labels and hints.
