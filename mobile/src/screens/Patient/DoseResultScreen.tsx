import { NativeStackScreenProps } from '@react-navigation/native-stack';

import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { VoicePrompt } from '../../components/VoicePrompt';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'DoseResult'>;

export function DoseResultScreen({ navigation, route }: Props) {
  const message =
    route.params?.result ??
    'Please confirm the medication with the label or a caregiver if you are unsure.';

  return (
    <Screen title="Dose result">
      <StatusCard title="Verification result" message={message} />
      <VoicePrompt text={message} />
      <AccessibleButton
        title="Back to today"
        onPress={() => navigation.navigate('TodaySchedule')}
        accessibilityLabel="Back to today's schedule"
        accessibilityHint="Returns to today's dose schedule"
      />
    </Screen>
  );
}
