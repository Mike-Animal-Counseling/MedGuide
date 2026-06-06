import { PropsWithChildren } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { useAccessibility } from '../accessibility/AccessibilityContext';

type Props = PropsWithChildren<{
  title: string;
  message: string;
  tone?: 'info' | 'warning' | 'success';
}>;

export function StatusCard({ title, message, tone = 'info', children }: Props) {
  const { theme } = useAccessibility();
  const label = `${title}. ${message}`;
  return (
    <View
      accessible={!children}
      accessibilityRole="summary"
      accessibilityLabel={label}
      style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
    >
      <Text style={[styles.title, { color: tone === 'warning' ? theme.colors.danger : theme.colors.text }]}>
        {title}
      </Text>
      <Text style={[styles.message, { color: theme.colors.mutedText, fontSize: theme.fontSize.body }]}>
        {message}
      </Text>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 12, borderWidth: 2, gap: 8, padding: 16 },
  title: { fontSize: 18, fontWeight: '700' },
  message: { lineHeight: 24 },
});
