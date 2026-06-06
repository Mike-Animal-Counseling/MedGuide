import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { useState } from 'react';
import { Text, TextInput } from 'react-native';

import { useAuth } from '../../auth/AuthContext';
import { AccessibleButton } from '../../components/AccessibleButton';
import { Screen } from '../../components/Screen';
import { StatusCard } from '../../components/StatusCard';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

export function LoginScreen({ navigation }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);
  const isValid = email.includes('@') && password.length >= 8;

  async function submit() {
    setError(null);
    if (!isValid) {
      setError('Enter a valid email and password.');
      return;
    }
    setSubmitting(true);
    try {
      await signIn(email, password);
    } catch {
      setError('Sign in failed. Check your email and password.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen title="Sign in">
      <Text>Email</Text>
      <TextInput
        accessibilityLabel="Email address"
        accessibilityHint="Enter the email address for your MedGuide account"
        autoCapitalize="none"
        keyboardType="email-address"
        onChangeText={setEmail}
        value={email}
      />
      <Text>Password</Text>
      <TextInput
        accessibilityLabel="Password"
        accessibilityHint="Enter your account password"
        onChangeText={setPassword}
        secureTextEntry
        value={password}
      />
      {error ? <StatusCard title="Sign in problem" message={error} tone="warning" /> : null}
      <AccessibleButton
        title={isSubmitting ? 'Signing in...' : 'Sign in'}
        onPress={submit}
        disabled={isSubmitting}
        accessibilityLabel="Sign in"
        accessibilityHint="Signs in to your MedGuide account"
      />
      <AccessibleButton
        title="Create account"
        onPress={() => navigation.navigate('Register')}
        accessibilityLabel="Create account"
        accessibilityHint="Opens the registration form"
      />
    </Screen>
  );
}
