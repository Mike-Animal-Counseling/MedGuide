import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { Pressable, Text } from 'react-native';

import { MedicationCard } from '../../components/MedicationCard';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { useMedications } from '../../hooks/useMedications';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'MedicationList'>;

export function MedicationListScreen({ navigation }: Props) {
  const { data, error, isLoading, refetch } = useMedications();

  return (
    <Screen title="Medications">
      {isLoading ? <Text accessibilityRole="progressbar">Loading medications...</Text> : null}
      {error ? (
        <StatusCard
          title="Medications unavailable"
          message="We could not load your medications. Please try again."
          tone="warning"
        />
      ) : null}
      {!isLoading && data?.length === 0 ? (
        <StatusCard title="No medications saved" message="Add medication details you have confirmed." />
      ) : null}
      {data?.map(medication => (
        <Pressable
          key={medication.id}
          accessibilityRole="button"
          accessibilityLabel={`Open ${medication.name}`}
          accessibilityHint="Opens medication details"
          onPress={() => navigation.navigate('MedicationDetail', { medicationId: medication.id })}
        >
          <MedicationCard medication={medication} />
        </Pressable>
      ))}
      <AccessibleButton
        title="Add medication"
        onPress={() => navigation.navigate('AddMedication')}
        accessibilityLabel="Add medication"
        accessibilityHint="Opens the medication form"
      />
      <AccessibleButton
        title="Refresh medications"
        onPress={() => void refetch()}
        accessibilityLabel="Refresh medications"
        accessibilityHint="Reloads your medication list"
      />
    </Screen>
  );
}
