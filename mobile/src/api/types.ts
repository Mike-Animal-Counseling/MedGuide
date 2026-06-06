export type AuthTokens = {
  access_token: string;
  refresh_token: string;
};

export type UserRole = 'PATIENT' | 'CAREGIVER' | 'ADMIN';

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  timezone: string;
  accessibility_preferences: Record<string, unknown>;
};

export type Medication = {
  id: string;
  name: string;
  dosage?: string | null;
  form: string;
  active: boolean;
  instructions?: string | null;
};

export type DoseStatus =
  | 'PENDING'
  | 'TAKEN_ON_TIME'
  | 'TAKEN_LATE'
  | 'SKIPPED'
  | 'MISSED'
  | 'NEEDS_HELP'
  | 'VERIFICATION_FAILED';

export type DoseLog = {
  id: string;
  medication_id: string;
  schedule_id: string;
  scheduled_time: string;
  actual_taken_time?: string | null;
  status: DoseStatus;
  confirmation_method?: string | null;
  notes?: string | null;
};

export type CaregiverPermission = 'VIEW_ONLY' | 'MANAGE_MEDICATIONS' | 'FULL_ACCESS';

export type CaregiverLink = {
  id: string;
  patient_id: string;
  caregiver_id?: string | null;
  caregiver_email: string;
  relationship?: string | null;
  permission_level: CaregiverPermission;
  status: 'PENDING' | 'ACTIVE' | 'REVOKED';
  created_at: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
};

export type LinkedPatient = {
  link: CaregiverLink;
  patient: CurrentUser;
};

export type PatientToday = {
  patient_id: string;
  schedules: unknown[];
  dose_logs: DoseLog[];
};
