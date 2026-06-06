import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { AuthProvider } from '../auth/AuthContext';
import { LoginScreen } from '../screens/Auth/LoginScreen';
import { renderWithAccessibility } from './test-utils';

const mockApiRequest = jest.fn();
const mockSecureStore: Record<string, string | null> = {
  'medguide.accessToken': null,
  'medguide.refreshToken': null,
};

jest.mock('../api/client', () => ({
  apiRequest: (...args: unknown[]) => mockApiRequest(...args),
}));

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (key: string) => mockSecureStore[key] ?? null),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockSecureStore[key] = value;
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    mockSecureStore[key] = null;
  }),
}));

describe('mobile login flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSecureStore['medguide.accessToken'] = null;
    mockSecureStore['medguide.refreshToken'] = null;
    mockApiRequest.mockImplementation((path: string) => {
      if (path === '/api/v1/auth/login') {
        return Promise.resolve({ access_token: 'access-token', refresh_token: 'refresh-token' });
      }
      if (path === '/api/v1/auth/me') {
        return Promise.resolve({
          id: 'user-1',
          email: 'pat@example.com',
          full_name: 'Pat Patient',
          role: 'PATIENT',
          timezone: 'America/Chicago',
          accessibility_preferences: {},
        });
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });
  });

  it('logs in, stores tokens, and fetches /auth/me', async () => {
    renderWithAccessibility(
      <AuthProvider>
        <LoginScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />
      </AuthProvider>,
    );

    fireEvent.changeText(screen.getByLabelText('Email address'), 'pat@example.com');
    fireEvent.changeText(screen.getByLabelText('Password'), 'strong-password');
    fireEvent.press(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/auth/login', {
        method: 'POST',
        body: { email: 'pat@example.com', password: 'strong-password' },
      });
      expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/auth/me');
    });
    expect(mockSecureStore['medguide.accessToken']).toBe('access-token');
    expect(mockSecureStore['medguide.refreshToken']).toBe('refresh-token');
  });
});
