export type RootStackParamList = {
  Login: undefined;
  Register: undefined;
  PatientHome: undefined;
  TodaySchedule: undefined;
  MedicationList: undefined;
  MedicationDetail: { medicationId: string };
  AddMedication: undefined;
  ManualMedicationForm: { medicationId?: string; extracted?: ExtractedMedicationDraft } | undefined;
  ScanLabel: undefined;
  ConfirmExtractedMedication: { scan: ScanLabelResult };
  VerifyMedication: { doseLogId: string } | undefined;
  DoseResult: { result?: string };
  CaregiverHome: undefined;
  PatientDetail: { patientId: string; linkId?: string; permissionLevel?: string };
  CaregiverDoseLogs: { patientId: string; permissionLevel?: string };
  CaregiverVerificationReview: { patientId: string; permissionLevel?: string };
  CaregiverInviteAccept: undefined;
  AccessibilitySettings: undefined;
};

export type ExtractedMedicationDraft = {
  name?: string;
  generic_name?: string;
  brand_name?: string;
  dosage?: string;
  instructions?: string;
  frequency?: string;
};

export type ScanLabelResult = {
  image_id: string;
  result: 'LABEL_READ' | 'UNREADABLE_IMAGE';
  ocr_text: string | null;
  extracted_fields: ExtractedMedicationDraft & Record<string, unknown>;
  confidence_score: number | null;
  requires_confirmation: true;
  safety_message: string;
};

export type MedicationVerificationResult =
  | 'MATCH_LIKELY'
  | 'MATCH_UNCERTAIN'
  | 'NO_MATCH'
  | 'UNREADABLE_IMAGE'
  | 'CAREGIVER_REVIEW_REQUIRED';

export type VerifyMedicationResult = {
  image_id: string;
  result: MedicationVerificationResult;
  confidence_score: number | null;
  requires_confirmation: true;
  safety_message: string;
};
