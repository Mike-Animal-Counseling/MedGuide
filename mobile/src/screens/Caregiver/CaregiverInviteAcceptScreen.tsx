import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Text, TextInput } from 'react-native';

import { apiRequest } from '../../api/client';
import { CaregiverLink } from '../../api/types';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'CaregiverInviteAccept'>;

export function CaregiverInviteAcceptScreen({ navigation }: Props) {
  const queryClient = useQueryClient();
  const [inviteToken, setInviteToken] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      apiRequest<CaregiverLink>('/api/v1/caregivers/accept', {
        method: 'POST',
        body: { invite_token: inviteToken.trim() },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['caregiver-patients'] });
      navigation.navigate('CaregiverHome');
    },
    onError: () =>
      setMessage('Invitation could not be accepted. It may be invalid, expired, or for another email.'),
  });

  function submit() {
    if (inviteToken.trim().length < 32) {
      setMessage('Enter the full caregiver invite token.');
      return;
    }
    setMessage(null);
    mutation.mutate();
  }

  return (
    <Screen title="Accept invite">
      <StatusCard
        title="Caregiver invitation"
        message="Accept only invitations you recognize. Access is limited by the patient's permission settings."
      />
      <Text>Invite token</Text>
      <TextInput
        accessibilityLabel="Caregiver invite token"
        accessibilityHint="Enter the invite token sent by the patient"
        autoCapitalize="none"
        onChangeText={setInviteToken}
        value={inviteToken}
      />
      {message ? <StatusCard title="Invite problem" message={message} tone="warning" /> : null}
      <AccessibleButton
        title={mutation.isPending ? 'Accepting...' : 'Accept invite'}
        disabled={mutation.isPending}
        onPress={submit}
        accessibilityLabel="Accept caregiver invite"
        accessibilityHint="Accepts the caregiver link invitation"
      />
    </Screen>
  );
}
