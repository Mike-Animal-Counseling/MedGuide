import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, TextInput } from 'react-native';

import { apiRequest } from '../../api/client';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'ConfirmExtractedMedication'>;

export function ConfirmExtractedMedicationScreen({ navigation, route }: Props) {
  const queryClient = useQueryClient();
  const { scan } = route.params;
  const fields = scan.extracted_fields;
  const [name, setName] = useState(toText(fields.name));
  const [genericName, setGenericName] = useState(toText(fields.generic_name));
  const [brandName, setBrandName] = useState(toText(fields.brand_name));
  const [dosage, setDosage] = useState(toText(fields.dosage));
  const [instructions, setInstructions] = useState(toText(fields.instructions));
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      apiRequest('/api/v1/medications', {
        method: 'POST',
        body: {
          name: name.trim(),
          generic_name: genericName.trim() || undefined,
          brand_name: brandName.trim() || undefined,
          dosage: dosage.trim() || undefined,
          form: 'OTHER',
          instructions: instructions.trim() || undefined,
          label_image_id: scan.image_id,
          source: 'MANUAL',
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['medications'] });
      navigation.navigate('MedicationList');
    },
    onError: () => setError('Medication could not be saved. Please confirm the fields and try again.'),
  });

  function submit() {
    setError(null);
    if (!name.trim()) {
      setError('Medication name is required before saving.');
      return;
    }
    mutation.mutate();
  }

  const spokenSummary = buildSpokenExtractedFields({
    name,
    genericName,
    brandName,
    dosage,
    instructions,
    safetyMessage: scan.safety_message,
  });

  return (
    <Screen title="Confirm extracted medication">
      <StatusCard
        title="OCR requires confirmation"
        message="Review and edit every field before saving. MedGuide will not auto-save OCR results."
        tone="warning"
      />
      <StatusCard title="Safety message" message={scan.safety_message} />
      <VoicePrompt text={spokenSummary} buttonTitle="Read extracted fields" />
      {scan.ocr_text ? <StatusCard title="Raw OCR text" message={scan.ocr_text} /> : null}
      <Text>Medication name</Text>
      <TextInput
        accessibilityLabel="Extracted medication name"
        accessibilityHint="Review and edit the medication name before saving"
        onChangeText={setName}
        value={name}
      />
      <Text>Generic name</Text>
      <TextInput
        accessibilityLabel="Extracted generic name"
        accessibilityHint="Review and edit the generic name if present"
        onChangeText={setGenericName}
        value={genericName}
      />
      <Text>Brand name</Text>
      <TextInput
        accessibilityLabel="Extracted brand name"
        accessibilityHint="Review and edit the brand name if present"
        onChangeText={setBrandName}
        value={brandName}
      />
      <Text>Dosage text</Text>
      <TextInput
        accessibilityLabel="Extracted dosage text"
        accessibilityHint="Review dosage text exactly as shown on the label"
        onChangeText={setDosage}
        value={dosage}
      />
      <Text>Instructions</Text>
      <TextInput
        accessibilityLabel="Extracted instructions"
        accessibilityHint="Review and edit instructions before saving"
        multiline
        onChangeText={setInstructions}
        value={instructions}
      />
      {error ? <StatusCard title="Confirmation problem" message={error} tone="warning" /> : null}
      <AccessibleButton
        title={mutation.isPending ? 'Saving...' : 'Confirm and save medication'}
        disabled={mutation.isPending}
        onPress={submit}
        accessibilityLabel="Confirm and save medication"
        accessibilityHint="Saves only the fields you have reviewed and confirmed"
      />
      <AccessibleButton
        title="Edit in manual form"
        onPress={() =>
          navigation.navigate('ManualMedicationForm', {
            extracted: {
              name,
              generic_name: genericName,
              brand_name: brandName,
              dosage,
              instructions,
            },
          })
        }
        accessibilityLabel="Edit extracted fields manually"
        accessibilityHint="Opens the manual medication form with these fields"
      />
    </Screen>
  );
}

function toText(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function buildSpokenExtractedFields(input: {
  name: string;
  genericName: string;
  brandName: string;
  dosage: string;
  instructions: string;
  safetyMessage: string;
}): string {
  const parts = [
    input.name ? `Medication name: ${input.name}.` : '',
    input.genericName ? `Generic name: ${input.genericName}.` : '',
    input.brandName ? `Brand name: ${input.brandName}.` : '',
    input.dosage ? `Dosage text: ${input.dosage}.` : '',
    input.instructions ? `Instructions: ${input.instructions}.` : '',
    input.safetyMessage,
  ].filter(Boolean);
  return parts.join(' ');
}
