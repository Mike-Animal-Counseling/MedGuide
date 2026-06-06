import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useQuery } from '@tanstack/react-query';
import { Pressable, Text } from 'react-native';

import { apiRequest } from '../../api/client';
import { LinkedPatient } from '../../api/types';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'CaregiverHome'>;

export function CaregiverHomeScreen({ navigation }: Props) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['caregiver-patients'],
    queryFn: () => apiRequest<LinkedPatient[]>('/api/v1/caregivers/patients'),
  });

  return (
    <Screen title="Caregiver home">
      {isLoading ? <Text accessibilityRole="progressbar">Loading linked patients...</Text> : null}
      {error ? (
        <StatusCard title="Patients unavailable" message="Linked patients could not be loaded." tone="warning" />
      ) : null}
      {!isLoading && data?.length === 0 ? (
        <StatusCard title="No linked patients" message="Accepted caregiver invitations will appear here." />
      ) : null}
      {data?.map(patient => (
        <Pressable
          key={patient.patient.id}
          accessibilityRole="button"
          accessibilityLabel={`Open patient ${patient.patient.email}`}
          accessibilityHint="Opens today's patient medication information"
          onPress={() =>
            navigation.navigate('PatientDetail', {
              patientId: patient.patient.id,
              linkId: patient.link.id,
              permissionLevel: patient.link.permission_level,
            })
          }
        >
          <StatusCard
            title={patient.patient.full_name || patient.patient.email}
            message={`Permission: ${patient.link.permission_level}. Relationship: ${
              patient.link.relationship ?? 'Not specified'
            }`}
          />
        </Pressable>
      ))}
      <AccessibleButton
        title="Accept caregiver invite"
        onPress={() => navigation.navigate('CaregiverInviteAccept')}
        accessibilityLabel="Accept caregiver invite"
        accessibilityHint="Opens the caregiver invitation acceptance form"
      />
    </Screen>
  );
}
