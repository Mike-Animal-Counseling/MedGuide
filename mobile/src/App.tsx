import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusBar } from 'expo-status-bar';
import { useMemo } from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from './auth/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RootNavigator } from './navigation/RootNavigator';
import { AccessibilityProvider } from './accessibility/AccessibilityContext';

export function App() {
  const queryClient = useMemo(() => new QueryClient(), []);

  return (
    <ErrorBoundary>
      <SafeAreaProvider>
        <AccessibilityProvider>
          <QueryClientProvider client={queryClient}>
            <AuthProvider>
              <StatusBar style="auto" />
              <RootNavigator />
            </AuthProvider>
          </QueryClientProvider>
        </AccessibilityProvider>
      </SafeAreaProvider>
    </ErrorBoundary>
  );
}
