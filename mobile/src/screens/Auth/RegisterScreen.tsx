import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useState } from 'react';
import { Text, TextInput } from 'react-native';

import { useAuth } from '../../auth/AuthContext';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Register'>;

export function RegisterScreen({ navigation }: Props) {
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const isValid = email.includes('@') && password.length >= 12 && fullName.trim().length > 1;

  async function submit() {
    setError(null);
    if (!isValid) {
      setError('Enter your name, a valid email, and a password of at least 12 characters.');
      return;
    }
    try {
      await register({
        email,
        password,
        fullName,
        role: 'PATIENT',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
    } catch {
      setError('Registration failed. Please review the form and try again.');
    }
  }

  return (
    <Screen title="Create account">
      <Text>Full name</Text>
      <TextInput
        accessibilityLabel="Full name"
        accessibilityHint="Enter your name"
        onChangeText={setFullName}
        value={fullName}
      />
      <Text>Email</Text>
      <TextInput
        accessibilityLabel="Email address"
        accessibilityHint="Enter the email address you want to use"
        autoCapitalize="none"
        keyboardType="email-address"
        onChangeText={setEmail}
        value={email}
      />
      <Text>Password</Text>
      <TextInput
        accessibilityLabel="Password"
        accessibilityHint="Use at least 12 characters"
        onChangeText={setPassword}
        secureTextEntry
        value={password}
      />
      {error ? <StatusCard title="Registration problem" message={error} tone="warning" /> : null}
      <AccessibleButton
        title="Register"
        onPress={submit}
        accessibilityLabel="Register"
        accessibilityHint="Creates your MedGuide account"
      />
      <AccessibleButton
        title="Back to sign in"
        onPress={() => navigation.navigate('Login')}
        accessibilityLabel="Back to sign in"
        accessibilityHint="Returns to the sign in screen"
      />
    </Screen>
  );
}
