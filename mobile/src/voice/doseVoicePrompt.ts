import { Medication } from '../api/types';

export const MEDICATION_SAFETY_DISCLAIMER =
  'MedGuide is medication assistance only. Confirm this with your medication label or caregiver if you are unsure.';

export function buildDoseVoicePrompt(medication: Medication | undefined): string {
  const instruction = medication?.instructions?.trim();
  if (!instruction) {
    return `No saved user-confirmed instruction is available. ${MEDICATION_SAFETY_DISCLAIMER}`;
  }
  return `${instruction} ${MEDICATION_SAFETY_DISCLAIMER}`;
}
