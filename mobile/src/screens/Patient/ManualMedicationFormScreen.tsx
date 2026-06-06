import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, TextInput } from 'react-native';

import { apiRequest } from '../../api/client';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'ManualMedicationForm'>;

export function ManualMedicationFormScreen({ navigation, route }: Props) {
  const queryClient = useQueryClient();
  const draft = route.params?.extracted;
  const medicationId = route.params?.medicationId;
  const [name, setName] = useState(draft?.name ?? '');
  const [genericName, setGenericName] = useState(draft?.generic_name ?? '');
  const [brandName, setBrandName] = useState(draft?.brand_name ?? '');
  const [dosage, setDosage] = useState(draft?.dosage ?? '');
  const [instructions, setInstructions] = useState(draft?.instructions ?? '');
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      apiRequest(medicationId ? `/api/v1/medications/${medicationId}` : '/api/v1/medications', {
        method: medicationId ? 'PATCH' : 'POST',
        body: {
          name: name.trim(),
          generic_name: genericName.trim() || undefined,
          brand_name: brandName.trim() || undefined,
          dosage: dosage.trim() || undefined,
          form: 'OTHER',
          instructions: instructions.trim() || undefined,
          source: 'MANUAL',
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['medications'] });
      if (medicationId) {
        await queryClient.invalidateQueries({ queryKey: ['medication', medicationId] });
      }
      navigation.navigate('MedicationList');
    },
    onError: () => setError('Medication could not be saved. Please check the form.'),
  });

  function submit() {
    setError(null);
    if (!name.trim()) {
      setError('Medication name is required.');
      return;
    }
    mutation.mutate();
  }

  return (
    <Screen title="Medication details">
      <StatusCard
        title="Confirm before saving"
        message="Only save information you confirmed from the label, prescription, or clinician instructions."
      />
      <Text>Medication name</Text>
      <TextInput
        accessibilityLabel="Medication name"
        accessibilityHint="Enter the medication name exactly as confirmed"
        onChangeText={setName}
        value={name}
      />
      <Text>Generic name</Text>
      <TextInput
        accessibilityLabel="Generic name"
        accessibilityHint="Enter the confirmed generic name if available"
        onChangeText={setGenericName}
        value={genericName}
      />
      <Text>Brand name</Text>
      <TextInput
        accessibilityLabel="Brand name"
        accessibilityHint="Enter the confirmed brand name if available"
        onChangeText={setBrandName}
        value={brandName}
      />
      <Text>Dosage text</Text>
      <TextInput
        accessibilityLabel="Dosage text"
        accessibilityHint="Enter dosage text only as confirmed from the label"
        onChangeText={setDosage}
        value={dosage}
      />
      <Text>Instructions</Text>
      <TextInput
        accessibilityLabel="Medication instructions"
        accessibilityHint="Enter user-confirmed instructions only"
        multiline
        onChangeText={setInstructions}
        value={instructions}
      />
      {error ? <StatusCard title="Medication problem" message={error} tone="warning" /> : null}
      <AccessibleButton
        title={mutation.isPending ? 'Saving...' : medicationId ? 'Update medication' : 'Save medication'}
        disabled={mutation.isPending}
        onPress={submit}
        accessibilityLabel={medicationId ? 'Update medication' : 'Save medication'}
        accessibilityHint={
          medicationId ? 'Updates the confirmed medication details' : 'Saves the confirmed medication details'
        }
      />
    </Screen>
  );
}
