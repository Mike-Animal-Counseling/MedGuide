import { PropsWithChildren } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAccessibility } from '../accessibility/AccessibilityContext';

type Props = PropsWithChildren<{
  title: string;
}>;

export function Screen({ title, children }: Props) {
  const { theme } = useAccessibility();
  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: theme.colors.background }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text accessibilityRole="header" style={[styles.title, { color: theme.colors.text, fontSize: theme.fontSize.title }]}>
          {title}
        </Text>
        <View style={styles.body}>{children}</View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  content: { gap: 20, padding: 20 },
  title: { fontWeight: '800' },
  body: { gap: 16 },
});
