import { StyleSheet, Text, View } from 'react-native';

import { AccessibleButton } from './AccessibleButton';
import { speak } from '../voice/speech';

type Props = {
  text: string;
  buttonTitle?: string;
};

export function VoicePrompt({ text, buttonTitle = 'Read aloud' }: Props) {
  return (
    <View style={styles.container}>
      <Text accessibilityRole="text">{text}</Text>
      <AccessibleButton
        title={buttonTitle}
        onPress={() => speak(text)}
        accessibilityLabel={buttonTitle}
        accessibilityHint="Uses device speech to read the saved instruction and safety disclaimer"
      />
    </View>
  );
}

const styles = StyleSheet.create({ container: { gap: 12 } });
