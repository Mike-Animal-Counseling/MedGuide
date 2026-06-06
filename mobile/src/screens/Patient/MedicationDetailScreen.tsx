import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useQuery } from '@tanstack/react-query';
import { Text } from 'react-native';

import { apiRequest } from '../../api/client';
import { Medication } from '../../api/types';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'MedicationDetail'>;

export function MedicationDetailScreen({ navigation, route }: Props) {
  const { data, error, isLoading } = useQuery({
    queryKey: ['medication', route.params.medicationId],
    queryFn: () => apiRequest<Medication>(`/api/v1/medications/${route.params.medicationId}`),
  });

  return (
    <Screen title="Medication details">
      {isLoading ? <Text accessibilityRole="progressbar">Loading medication...</Text> : null}
      {error ? (
        <StatusCard
          title="Medication unavailable"
          message="We could not load this medication."
          tone="warning"
        />
      ) : null}
      {data ? (
        <>
          <StatusCard title={data.name} message={data.dosage ?? 'No dosage text entered'} />
          <StatusCard title="Form" message={data.form} />
          <StatusCard
            title="Instructions"
            message={data.instructions ?? 'No user-confirmed instructions entered'}
          />
          <AccessibleButton
            title="Edit medication"
            onPress={() =>
              navigation.navigate('ManualMedicationForm', {
                medicationId: data.id,
                extracted: {
                  name: data.name,
                  dosage: data.dosage ?? undefined,
                  instructions: data.instructions ?? undefined,
                },
              })
            }
            accessibilityLabel={`Edit ${data.name}`}
            accessibilityHint="Opens the confirmed medication form for editing"
          />
        </>
      ) : null}
    </Screen>
  );
}
