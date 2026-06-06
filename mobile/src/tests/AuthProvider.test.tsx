import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Text } from 'react-native';

import { apiRequest } from '../api/client';
import { AuthProvider, useAuth } from '../auth/AuthContext';
import { AccessibleButton } from '../components/AccessibleButton';
import { renderWithAccessibility } from './test-utils';

const secureStore: Record<string, string | null> = {
  'medguide.accessToken': null,
  'medguide.refreshToken': null,
};

jest.mock('../api/client', () => ({
  apiRequest: jest.fn(),
}));

jest.mock('../notifications/deviceRegistration', () => ({
  unregisterCurrentDevice: jest.fn(async () => undefined),
}));

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (key: string) => secureStore[key] ?? null),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    secureStore[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    secureStore[key] = null;
  }),
}));

describe('AuthProvider production auth behavior', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    secureStore['medguide.accessToken'] = 'access-token';
    secureStore['medguide.refreshToken'] = 'refresh-token';
  });

  it('clears persisted tokens when startup user lookup is unauthorized', async () => {
    (apiRequest as jest.Mock).mockRejectedValueOnce(new Error('unauthorized'));

    renderWithAccessibility(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText('signed-out')).toBeOnTheScreen();
    expect(secureStore['medguide.accessToken']).toBeNull();
    expect(secureStore['medguide.refreshToken']).toBeNull();
  });

  it('logs out through the backend and clears tokens', async () => {
    (apiRequest as jest.Mock).mockImplementation((path: string) => {
      if (path === '/api/v1/auth/me') {
        return Promise.resolve({
          id: 'user-1',
          email: 'patient@example.com',
          full_name: 'Patient User',
          role: 'PATIENT',
          timezone: 'America/Chicago',
          accessibility_preferences: {},
        });
      }
      if (path === '/api/v1/auth/logout') {
        return Promise.resolve(null);
      }
      return Promise.resolve(null);
    });

    renderWithAccessibility(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText('signed-in:patient@example.com')).toBeOnTheScreen();
    fireEvent.press(screen.getByRole('button', { name: 'Sign out test user' }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/auth/logout', {
        method: 'POST',
        body: { refresh_token: 'refresh-token' },
      });
    });
    expect(await screen.findByText('signed-out')).toBeOnTheScreen();
    expect(secureStore['medguide.accessToken']).toBeNull();
    expect(secureStore['medguide.refreshToken']).toBeNull();
  });
});

function AuthProbe() {
  const { isLoading, signOut, user } = useAuth();
  if (isLoading) return null;
  return (
    <>
      <Text>{user ? `signed-in:${user.email}` : 'signed-out'}</Text>
      <AccessibleButton
        title="Sign out"
        onPress={() => {
          void signOut();
        }}
        accessibilityLabel="Sign out test user"
        accessibilityHint="Signs out the authenticated test user"
      />
    </>
  );
}
