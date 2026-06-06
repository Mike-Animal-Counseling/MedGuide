import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { apiRequest } from '../api/client';
import { AuthProvider, useAuth } from '../auth/AuthContext';
import { AccessibleButton } from '../components/AccessibleButton';
import { handleReminderTap } from '../navigation/RootNavigator';
import { NotificationRegistrationCard } from '../notifications/NotificationRegistrationCard';
import { registerDeviceForPushNotifications } from '../notifications/deviceRegistration';
import {
  getDoseLogIdFromNotification,
  speakReminderForDose,
} from '../notifications/reminderHandling';
import { renderWithAccessibility } from './test-utils';

const mockRequestPermissionsAsync = jest.fn();
const mockGetExpoPushTokenAsync = jest.fn();
const mockSpeak = jest.fn();
const mockNavigate = jest.fn();
const secureStore: Record<string, string | null> = {
  'medguide.accessToken': 'access-token',
  'medguide.refreshToken': 'refresh-token',
  'medguide.pushDeviceId': 'device-1',
};

jest.mock('../api/client', () => ({
  apiRequest: jest.fn(),
}));

jest.mock('expo-notifications', () => ({
  requestPermissionsAsync: (...args: unknown[]) => mockRequestPermissionsAsync(...args),
  getExpoPushTokenAsync: (...args: unknown[]) => mockGetExpoPushTokenAsync(...args),
  addNotificationResponseReceivedListener: jest.fn(() => ({ remove: jest.fn() })),
}));

jest.mock('expo-speech', () => ({
  speak: (...args: unknown[]) => mockSpeak(...args),
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

describe('mobile notifications', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    secureStore['medguide.accessToken'] = 'access-token';
    secureStore['medguide.refreshToken'] = 'refresh-token';
    secureStore['medguide.pushDeviceId'] = 'device-1';
    (apiRequest as jest.Mock).mockImplementation((path: string) => {
      if (path === '/api/v1/devices') {
        return Promise.resolve({ id: 'device-2', platform: 'IOS', active: true });
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
      if (path === '/api/v1/auth/logout') {
        return Promise.resolve(null);
      }
      if (path === '/api/v1/devices/device-1') {
        return Promise.resolve(null);
      }
      if (path === '/api/v1/dose-logs/today') {
        return Promise.resolve([
          {
            id: 'dose-1',
            medication_id: 'med-1',
            schedule_id: 'schedule-1',
            scheduled_time: '2026-06-04T15:00:00.000Z',
            status: 'PENDING',
          },
        ]);
      }
      if (path === '/api/v1/medications') {
        return Promise.resolve([
          {
            id: 'med-1',
            name: 'ExampleMed',
            dosage: '10 mg',
            form: 'TABLET',
            active: true,
            instructions: 'Take with food as saved on the label.',
          },
        ]);
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });
  });

  it('registers an Expo push token with the backend', async () => {
    mockRequestPermissionsAsync.mockResolvedValue({ granted: true });
    mockGetExpoPushTokenAsync.mockResolvedValue({ data: 'ExpoPushToken[token]' });

    const result = await registerDeviceForPushNotifications();

    expect(result).toEqual({ status: 'registered', deviceId: 'device-2' });
    expect(apiRequest).toHaveBeenCalledWith('/api/v1/devices', {
      method: 'POST',
      body: {
        platform: expect.any(String),
        push_token: 'ExpoPushToken[token]',
      },
    });
    expect(secureStore['medguide.pushDeviceId']).toBe('device-2');
  });

  it('handles permission denied accessibly', async () => {
    mockRequestPermissionsAsync.mockResolvedValue({ granted: false });

    renderWithAccessibility(<NotificationRegistrationCard />);
    fireEvent.press(screen.getByRole('button', { name: 'Enable reminder notifications' }));

    expect(
      await screen.findByText(
        'Notification permission was not granted. You can still use the app and check reminders manually.',
      ),
    ).toBeOnTheScreen();
  });

  it('removes the registered backend device on logout where possible', async () => {
    renderWithAccessibility(
      <AuthProvider>
        <LogoutButton />
      </AuthProvider>,
    );

    fireEvent.press(await screen.findByRole('button', { name: 'Sign out for test' }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/devices/device-1', { method: 'DELETE' });
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/auth/logout', {
        method: 'POST',
        body: { refresh_token: 'refresh-token' },
      });
    });
    expect(secureStore['medguide.pushDeviceId']).toBeNull();
  });

  it('extracts dose id from notification tap and navigates to verification', async () => {
    const response = {
      notification: { request: { content: { data: { dose_log_id: 'dose-1' } } } },
    };
    const doseId = getDoseLogIdFromNotification(response as never);
    expect(doseId).toBe('dose-1');

    await handleReminderTap(
      { isReady: () => true, navigate: mockNavigate } as never,
      'dose-1',
    );

    expect(mockNavigate).toHaveBeenCalledWith('VerifyMedication', { doseLogId: 'dose-1' });
  });

  it('speaks reminder using saved medication text and safety disclaimer', async () => {
    await speakReminderForDose(
      {
        id: 'dose-1',
        medication_id: 'med-1',
        schedule_id: 'schedule-1',
        scheduled_time: '2026-06-04T15:00:00.000Z',
        status: 'PENDING',
      },
      [
        {
          id: 'med-1',
          name: 'ExampleMed',
          dosage: '10 mg',
          form: 'TABLET',
          active: true,
          instructions: 'Take with food as saved on the label.',
        },
      ],
    );

    expect(mockSpeak).toHaveBeenCalledWith(
      'It is time to take ExampleMed, 10 mg, Take with food as saved on the label. MedGuide cannot confirm medication with certainty. Check the label or caregiver if unsure.',
      { language: 'en-US', rate: 0.9 },
    );
  });
});

function LogoutButton() {
  const { signOut } = useAuth();
  return (
    <NotificationRegistrationCardWrapper
      onPress={() => {
        void signOut();
      }}
    />
  );
}

function NotificationRegistrationCardWrapper({ onPress }: { onPress: () => void }) {
  return (
    <AccessibleButton
      title="Sign out"
      onPress={onPress}
      accessibilityLabel="Sign out for test"
      accessibilityHint="Signs out for notification cleanup testing"
    />
  );
}
