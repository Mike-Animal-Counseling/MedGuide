import { StyleSheet, Text, View } from 'react-native';

import { Medication } from '../api/types';
import { useAccessibility } from '../accessibility/AccessibilityContext';

type Props = {
  medication: Medication;
};

export function MedicationCard({ medication }: Props) {
  const { theme } = useAccessibility();
  return (
    <View
      accessible
      accessibilityRole="summary"
      accessibilityLabel={`${medication.name}. ${medication.active ? 'Active' : 'Inactive'}`}
      style={[styles.card, { backgroundColor: theme.colors.surface, borderColor: theme.colors.border }]}
    >
      <Text style={[styles.name, { color: theme.colors.text, fontSize: theme.fontSize.body + 2 }]}>
        {medication.name}
      </Text>
      <Text style={{ color: theme.colors.mutedText, fontSize: theme.fontSize.body }}>
        {medication.dosage ?? 'No dosage text entered'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 12, borderWidth: 1, gap: 6, padding: 16 },
  name: { fontWeight: '700' },
});
