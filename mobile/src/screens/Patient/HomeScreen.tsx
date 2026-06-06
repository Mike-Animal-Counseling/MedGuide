import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useEffect, useState } from 'react';

import { useAuth } from '../../auth/AuthContext';
import { AccessibleButton } from '../../components/AccessibleButton';
import { LargeActionButton } from '../../components/LargeActionButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { useMedications } from '../../hooks/useMedications';
import { useTodayDoseLogs } from '../../hooks/useTodayDoseLogs';
import { RootStackParamList } from '../../navigation/types';
import { buildDoseVoicePrompt } from '../../voice/doseVoicePrompt';
import { NotificationRegistrationCard } from '../../notifications/NotificationRegistrationCard';
import { scheduleLocalFallbackReminders } from '../../notifications/reminderHandling';

type Props = NativeStackScreenProps<RootStackParamList, 'PatientHome'>;

export function HomeScreen({ navigation }: Props) {
  const { user, signOut } = useAuth();
  const { data: doses, isLoading: dosesLoading } = useTodayDoseLogs();
  const { data: medications } = useMedications();
  const [now] = useState(() => Date.now());
  const pendingDoses = (doses ?? [])
    .filter(dose => dose.status === 'PENDING')
    .sort((a, b) => Date.parse(a.scheduled_time) - Date.parse(b.scheduled_time));
  const currentDose = pendingDoses.find(dose => Date.parse(dose.scheduled_time) <= now);
  const nextDose = pendingDoses.find(dose => Date.parse(dose.scheduled_time) > now);
  const highlightedDose = currentDose ?? nextDose;
  const highlightedMedication = medications?.find(
    medication => medication.id === highlightedDose?.medication_id,
  );

  useEffect(() => {
    if (doses && medications) {
      void scheduleLocalFallbackReminders(doses, medications);
    }
  }, [doses, medications]);

  return (
    <Screen title="Today">
      <StatusCard
        title={`Hello${user?.full_name ? `, ${user.full_name}` : ''}`}
        message="MedGuide can help you review your medication schedule, but it does not replace medical advice."
      />
      {dosesLoading ? (
        <StatusCard title="Loading schedule" message="Checking today's medication schedule." />
      ) : null}
      {currentDose ? (
        <StatusCard
          title="Current due medication"
          message={`${highlightedMedication?.name ?? 'Medication'} is due now.`}
          tone="warning"
        />
      ) : null}
      {!currentDose && nextDose ? (
        <StatusCard
          title="Next due medication"
          message={`${highlightedMedication?.name ?? 'Medication'} at ${new Date(
            nextDose.scheduled_time,
          ).toLocaleTimeString()}`}
        />
      ) : null}
      {!dosesLoading && !highlightedDose ? (
        <StatusCard title="No pending doses" message="No pending medication doses are due today." />
      ) : null}
      {highlightedDose ? (
        <VoicePrompt text={buildDoseVoicePrompt(highlightedMedication)} buttonTitle="Repeat instruction" />
      ) : null}
      <NotificationRegistrationCard />
      <LargeActionButton
        title="Start Medication Check"
        onPress={() =>
          highlightedDose
            ? navigation.navigate('VerifyMedication', { doseLogId: highlightedDose.id })
            : navigation.navigate('TodaySchedule')
        }
        accessibilityLabel="Start medication check"
        accessibilityHint="Opens today's medication workflow with confirm, skip, and needs help actions"
      />
      <AccessibleButton
        title="Medications"
        onPress={() => navigation.navigate('MedicationList')}
        accessibilityLabel="Open medications"
        accessibilityHint="Shows your saved medications"
      />
      <AccessibleButton
        title="Scan label"
        onPress={() => navigation.navigate('ScanLabel')}
        accessibilityLabel="Scan medication label"
        accessibilityHint="Starts a safety-first label scanning workflow"
      />
      <AccessibleButton
        title="Accessibility settings"
        onPress={() => navigation.navigate('AccessibilitySettings')}
        accessibilityLabel="Open accessibility settings"
        accessibilityHint="Adjusts high contrast and large text options"
      />
      <AccessibleButton
        title="Sign out"
        onPress={signOut}
        accessibilityLabel="Sign out"
        accessibilityHint="Signs out of this device"
      />
    </Screen>
  );
}
