import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { apiRequest } from '../../api/client';
import { DoseLog } from '../../api/types';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'CaregiverDoseLogs'>;

export function CaregiverDoseLogsScreen({ route }: Props) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['caregiver-dose-logs', route.params.patientId],
    queryFn: () =>
      apiRequest<DoseLog[]>(`/api/v1/caregivers/patients/${route.params.patientId}/dose-logs`),
  });
  const missed = data?.filter(dose => dose.status === 'MISSED') ?? [];

  return (
    <Screen title="Patient dose logs">
      {isLoading ? <Text accessibilityRole="progressbar">Loading dose logs...</Text> : null}
      {error ? (
        <StatusCard
          title="Dose logs unavailable"
          message="Access may have changed or this patient is not linked."
          tone="warning"
        />
      ) : null}
      {missed.length > 0 ? (
        <StatusCard
          title="Missed dose alerts"
          message={`${missed.length} missed dose${missed.length === 1 ? '' : 's'} found.`}
          tone="warning"
        />
      ) : null}
      {!isLoading && data?.length === 0 ? (
        <StatusCard title="No dose logs" message="No dose logs are visible for this patient." />
      ) : null}
      {data?.map(dose => (
        <StatusCard
          key={dose.id}
          title={`Dose ${dose.status.toLowerCase().replaceAll('_', ' ')}`}
          message={`Scheduled for ${new Date(dose.scheduled_time).toLocaleString()}`}
          tone={dose.status === 'MISSED' ? 'warning' : 'info'}
        />
      ))}
    </Screen>
  );
}
