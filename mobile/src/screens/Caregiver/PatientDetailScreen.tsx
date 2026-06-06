import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { apiRequest } from '../../api/client';
import { PatientToday } from '../../api/types';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'PatientDetail'>;

export function PatientDetailScreen({ navigation, route }: Props) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['caregiver-patient-today', route.params.patientId],
    queryFn: () =>
      apiRequest<PatientToday>(`/api/v1/caregivers/patients/${route.params.patientId}/today`),
  });
  const missed = data?.dose_logs.filter(dose => dose.status === 'MISSED') ?? [];
  const canManage =
    route.params.permissionLevel === 'MANAGE_MEDICATIONS' ||
    route.params.permissionLevel === 'FULL_ACCESS';
  const canViewVerification = route.params.permissionLevel === 'FULL_ACCESS';

  return (
    <Screen title="Patient today">
      {isLoading ? <Text accessibilityRole="progressbar">Loading patient doses...</Text> : null}
      {error ? (
        <StatusCard title="Patient data unavailable" message="Access may have changed." tone="warning" />
      ) : null}
      {!isLoading && data?.dose_logs.length === 0 ? (
        <StatusCard title="No doses today" message="No scheduled doses are visible for this patient today." />
      ) : null}
      {missed.length > 0 ? (
        <StatusCard
          title="Missed dose alerts"
          message={`${missed.length} missed dose${missed.length === 1 ? '' : 's'} need review.`}
          tone="warning"
        />
      ) : null}
      {data?.dose_logs.map(dose => (
        <StatusCard
          key={dose.id}
          title={`Dose ${dose.status.toLowerCase().replaceAll('_', ' ')}`}
          message={`Scheduled for ${new Date(dose.scheduled_time).toLocaleTimeString()}`}
        />
      ))}
      <AccessibleButton
        title="View dose logs"
        onPress={() =>
          navigation.navigate('CaregiverDoseLogs', {
            patientId: route.params.patientId,
            permissionLevel: route.params.permissionLevel,
          })
        }
        accessibilityLabel="View patient dose logs"
        accessibilityHint="Shows dose history for this linked patient"
      />
      {canViewVerification ? (
        <AccessibleButton
          title="Review AI verification events"
          onPress={() =>
            navigation.navigate('CaregiverVerificationReview', {
              patientId: route.params.patientId,
              permissionLevel: route.params.permissionLevel,
            })
          }
          accessibilityLabel="Review AI verification events"
          accessibilityHint="Shows available low-confidence verification review information"
        />
      ) : (
        <StatusCard
          title="Verification review unavailable"
          message="FULL_ACCESS permission is required to view AI verification review information."
        />
      )}
      {canManage ? (
        <AccessibleButton
          title="Manage medications"
          onPress={() => navigation.navigate('MedicationList')}
          accessibilityLabel="Manage patient medications"
          accessibilityHint="Opens medication management tools permitted for this caregiver"
        />
      ) : (
        <StatusCard
          title="View only"
          message="This caregiver link does not allow medication management."
        />
      )}
    </Screen>
  );
}
