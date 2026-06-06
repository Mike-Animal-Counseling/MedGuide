import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Switch, Text, TextInput, View } from 'react-native';

import { useAccessibility } from '../../accessibility/AccessibilityContext';
import { apiRequest } from '../../api/client';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';

export function AccessibilitySettingsScreen() {
  const { highContrast, largeText, setHighContrast, setLargeText } = useAccessibility();
  const [linkId, setLinkId] = useState('');
  const [revokeMessage, setRevokeMessage] = useState<string | null>(null);
  const revoke = useMutation({
    mutationFn: () =>
      apiRequest(`/api/v1/caregivers/links/${linkId.trim()}/revoke`, {
        method: 'PATCH',
        body: {},
      }),
    onSuccess: () => {
      setRevokeMessage('Caregiver access was revoked.');
      setLinkId('');
    },
    onError: () =>
      setRevokeMessage('Caregiver access could not be revoked. Check the link id or your access.'),
  });

  return (
    <Screen title="Accessibility">
      <StatusCard
        title="Display preferences"
        message="These settings affect this device and help keep medication workflows easier to read."
      />
      <View>
        <Text>High contrast</Text>
        <Switch
          accessibilityLabel="High contrast"
          accessibilityHint="Increases screen contrast"
          onValueChange={setHighContrast}
          value={highContrast}
        />
      </View>
      <View>
        <Text>Large text</Text>
        <Switch
          accessibilityLabel="Large text"
          accessibilityHint="Increases text size throughout the app"
          onValueChange={setLargeText}
          value={largeText}
        />
      </View>
      <StatusCard
        title="Revoke caregiver access"
        message="Patients can revoke a caregiver link at any time. Enter the caregiver link id from your invitation or support record."
      />
      <Text>Caregiver link id</Text>
      <TextInput
        accessibilityLabel="Caregiver link id"
        accessibilityHint="Enter the caregiver link id to revoke"
        autoCapitalize="none"
        onChangeText={setLinkId}
        value={linkId}
      />
      {revokeMessage ? (
        <StatusCard title="Caregiver revoke status" message={revokeMessage} />
      ) : null}
      <AccessibleButton
        title={revoke.isPending ? 'Revoking...' : 'Revoke caregiver access'}
        disabled={revoke.isPending || !linkId.trim()}
        onPress={() => revoke.mutate()}
        accessibilityLabel="Revoke caregiver access"
        accessibilityHint="Revokes the caregiver link using the backend"
      />
    </Screen>
  );
}
