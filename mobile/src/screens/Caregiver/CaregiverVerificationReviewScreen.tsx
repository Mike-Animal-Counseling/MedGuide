import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { apiRequest } from '../../api/client';
import { DoseLog } from '../../api/types';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'CaregiverVerificationReview'>;

export function CaregiverVerificationReviewScreen({ route }: Props) {
  const hasFullAccess = route.params.permissionLevel === 'FULL_ACCESS';
  const { data, error, isLoading } = useQuery({
    enabled: hasFullAccess,
    queryKey: ['caregiver-verification-review', route.params.patientId],
    queryFn: () =>
      apiRequest<DoseLog[]>(`/api/v1/caregivers/patients/${route.params.patientId}/dose-logs`),
  });
  const reviewDoses =
    data?.filter(dose =>
      ['NEEDS_HELP', 'VERIFICATION_FAILED'].includes(dose.status),
    ) ?? [];

  return (
    <Screen title="Verification review">
      {!hasFullAccess ? (
        <StatusCard
          title="Permission required"
          message="FULL_ACCESS permission is required to review AI verification information."
          tone="warning"
        />
      ) : null}
      {hasFullAccess && isLoading ? (
        <Text accessibilityRole="progressbar">Loading verification review...</Text>
      ) : null}
      {hasFullAccess && error ? (
        <StatusCard
          title="Verification review unavailable"
          message="Verification review data could not be loaded. Access may have changed."
          tone="warning"
        />
      ) : null}
      {hasFullAccess ? (
        <StatusCard
          title="AI event access boundary"
          message="The current mobile API exposes dose statuses for review. A dedicated low-confidence AI event list must be added before raw verification events can be shown."
        />
      ) : null}
      {hasFullAccess && reviewDoses.length === 0 && !isLoading ? (
        <StatusCard
          title="No review items"
          message="No dose logs currently require caregiver verification review."
        />
      ) : null}
      {reviewDoses.map(dose => (
        <StatusCard
          key={dose.id}
          title={`Review ${dose.status.toLowerCase().replaceAll('_', ' ')}`}
          message={`Dose scheduled for ${new Date(dose.scheduled_time).toLocaleString()}`}
          tone="warning"
        />
      ))}
    </Screen>
  );
}
