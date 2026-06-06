import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useEffect } from 'react';
import { Text } from 'react-native';

import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { useDoseLogActions } from '../../hooks/useDoseLogActions';
import { useMedications } from '../../hooks/useMedications';
import { useTodayDoseLogs } from '../../hooks/useTodayDoseLogs';
import { RootStackParamList } from '../../navigation/types';
import { buildDoseVoicePrompt } from '../../voice/doseVoicePrompt';
import { scheduleLocalFallbackReminders } from '../../notifications/reminderHandling';

type Props = NativeStackScreenProps<RootStackParamList, 'TodaySchedule'>;

export function TodayScheduleScreen({ navigation }: Props) {
  const { data, error, isLoading, refetch } = useTodayDoseLogs();
  const { data: medications } = useMedications();
  const { confirm, skip, needsHelp } = useDoseLogActions();

  useEffect(() => {
    if (data && medications) {
      void scheduleLocalFallbackReminders(data, medications);
    }
  }, [data, medications]);

  return (
    <Screen title="Today's schedule">
      {isLoading ? <Text accessibilityRole="progressbar">{"Loading today's doses..."}</Text> : null}
      {error ? (
        <StatusCard
          title="Schedule unavailable"
          message="We could not load your schedule. Please try again."
          tone="warning"
        />
      ) : null}
      {!isLoading && data?.length === 0 ? (
        <StatusCard title="No scheduled doses" message="No doses are scheduled for today." />
      ) : null}
      {data?.map(dose => {
        const medication = medications?.find(item => item.id === dose.medication_id);
        const isPending = dose.status === 'PENDING';
        return (
          <StatusCard
            key={dose.id}
            title={`${medication?.name ?? 'Medication'} - ${formatDoseStatus(dose.status)}`}
            message={`Scheduled for ${new Date(dose.scheduled_time).toLocaleTimeString()}`}
          >
            <VoicePrompt text={buildDoseVoicePrompt(medication)} buttonTitle="Repeat instruction" />
            {isPending ? (
              <>
                <AccessibleButton
                  title="Start Medication Check"
                  onPress={() => navigation.navigate('VerifyMedication', { doseLogId: dose.id })}
                  accessibilityLabel={`Start medication check for ${medication?.name ?? 'medication'}`}
                  accessibilityHint="Opens camera verification for this pending dose"
                />
                <AccessibleButton
                  title="Confirm taken"
                  onPress={() => confirm.mutate(dose.id)}
                  disabled={confirm.isPending}
                  accessibilityLabel={`Confirm ${medication?.name ?? 'medication'} taken`}
                  accessibilityHint="Confirms this dose with the backend"
                />
                <AccessibleButton
                  title="Skip dose"
                  onPress={() => skip.mutate(dose.id)}
                  disabled={skip.isPending}
                  accessibilityLabel={`Skip ${medication?.name ?? 'medication'} dose`}
                  accessibilityHint="Marks this dose as skipped"
                />
                <AccessibleButton
                  title="Needs help"
                  onPress={() => needsHelp.mutate(dose.id)}
                  disabled={needsHelp.isPending}
                  accessibilityLabel={`Need help with ${medication?.name ?? 'medication'}`}
                  accessibilityHint="Marks this dose as needing help"
                />
              </>
            ) : null}
          </StatusCard>
        );
      })}
      <AccessibleButton
        title="Refresh schedule"
        onPress={() => void refetch()}
        accessibilityLabel="Refresh today's schedule"
        accessibilityHint="Reloads today's dose schedule from MedGuide"
      />
      <AccessibleButton
        title="Verify a dose"
        onPress={() => navigation.navigate('VerifyMedication')}
        accessibilityLabel="Verify medication"
        accessibilityHint="Starts the medication verification workflow"
      />
    </Screen>
  );
}

function formatDoseStatus(status: string): string {
  return status.toLowerCase().replaceAll('_', ' ');
}
