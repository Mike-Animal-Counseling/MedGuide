import * as Notifications from 'expo-notifications';

import { apiRequest } from '../api/client';
import { DoseLog, Medication } from '../api/types';
import { speak } from '../voice/speech';
import { buildMedicationCheckIntro } from '../voice/verificationVoicePrompt';

const scheduledLocalDoseIds = new Set<string>();

export type ReminderNotificationData = {
  dose_log_id?: unknown;
};

export function getDoseLogIdFromNotification(
  response: Notifications.NotificationResponse,
): string | null {
  const data = response.notification.request.content.data as ReminderNotificationData;
  return typeof data.dose_log_id === 'string' && data.dose_log_id.length > 0
    ? data.dose_log_id
    : null;
}

export async function fetchLatestDoseForReminder(doseLogId: string): Promise<DoseLog | null> {
  const today = await apiRequest<DoseLog[]>('/api/v1/dose-logs/today');
  const todayDose = today.find(dose => dose.id === doseLogId);
  if (todayDose) return todayDose;
  const allDoses = await apiRequest<DoseLog[]>('/api/v1/dose-logs');
  return allDoses.find(dose => dose.id === doseLogId) ?? null;
}

export async function speakReminderForDose(dose: DoseLog, medications: Medication[]): Promise<void> {
  const medication = medications.find(item => item.id === dose.medication_id);
  speak(buildMedicationCheckIntro(medication));
}

export async function scheduleLocalReminderForFetchedDose(
  dose: DoseLog,
  medication: Medication | undefined,
): Promise<string | null> {
  if (dose.status !== 'PENDING') return null;
  if (scheduledLocalDoseIds.has(dose.id)) return null;
  const triggerDate = new Date(dose.scheduled_time);
  if (triggerDate.getTime() <= Date.now()) return null;
  const notificationId = await Notifications.scheduleNotificationAsync({
    content: {
      title: 'Medication reminder',
      body: 'A scheduled medication is due. Please check your confirmed medication details.',
      data: { dose_log_id: dose.id },
    },
    trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: triggerDate },
  });
  scheduledLocalDoseIds.add(dose.id);
  return notificationId;
}

export async function scheduleLocalFallbackReminders(
  doses: DoseLog[],
  medications: Medication[],
): Promise<void> {
  await Promise.all(
    doses.map(dose =>
      scheduleLocalReminderForFetchedDose(
        dose,
        medications.find(item => item.id === dose.medication_id),
      ),
    ),
  );
}
