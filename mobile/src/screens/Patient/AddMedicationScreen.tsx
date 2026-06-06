import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'AddMedication'>;

export function AddMedicationScreen({ navigation }: Props) {
  return (
    <Screen title="Add medication">
      <StatusCard
        title="Choose how to add"
        message="You can type confirmed medication details yourself or scan a label for assistance."
      />
      <AccessibleButton
        title="Manual entry"
        onPress={() => navigation.navigate('ManualMedicationForm')}
        accessibilityLabel="Add medication manually"
        accessibilityHint="Opens a form to type confirmed medication information"
      />
      <AccessibleButton
        title="Scan label"
        onPress={() => navigation.navigate('ScanLabel')}
        accessibilityLabel="Scan medication label"
        accessibilityHint="Uses the camera to upload a label image for OCR assistance"
      />
    </Screen>
  );
}
