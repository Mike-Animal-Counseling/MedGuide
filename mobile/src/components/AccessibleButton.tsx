import { Pressable, StyleSheet, Text } from 'react-native';

import { useAccessibility } from '../accessibility/AccessibilityContext';

type Props = {
  title: string;
  onPress: () => void;
  accessibilityLabel: string;
  accessibilityHint: string;
  disabled?: boolean;
};

export function AccessibleButton({
  title,
  onPress,
  accessibilityLabel,
  accessibilityHint,
  disabled = false,
}: Props) {
  const { theme } = useAccessibility();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[
        styles.button,
        { backgroundColor: disabled ? theme.colors.border : theme.colors.primary },
      ]}
    >
      <Text style={[styles.text, { color: theme.colors.surface, fontSize: theme.fontSize.button }]}>
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center',
    borderRadius: 12,
    minHeight: 48,
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  text: { fontWeight: '700' },
});
