import { Medication } from '../api/types';

export const VERIFICATION_CAMERA_GUIDANCE =
  'Place the pill or medication bottle in the center of the camera.';

export function buildMedicationCheckIntro(medication: Medication | undefined): string {
  const name = medication?.name ?? 'your scheduled medication';
  const dosage = medication?.dosage?.trim();
  const instruction = medication?.instructions?.trim();
  const medicationDetails = [name, dosage, instruction ? stripFinalPunctuation(instruction) : null]
    .filter(Boolean)
    .join(', ');
  return `It is time to take ${medicationDetails}. MedGuide cannot confirm medication with certainty. Check the label or caregiver if unsure.`;
}

function stripFinalPunctuation(value: string): string {
  return value.replace(/[.!?]+$/u, '');
}
