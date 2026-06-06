import { Platform } from 'react-native';

import { apiRequest } from '../api/client';
import { getExpoPushToken } from './notifications';
import {
  clearRegisteredDeviceId,
  getRegisteredDeviceId,
  saveRegisteredDeviceId,
} from './deviceStorage';

type DeviceResponse = {
  id: string;
  platform: 'IOS' | 'ANDROID' | 'WEB';
  active: boolean;
};

export type PushRegistrationResult =
  | { status: 'registered'; deviceId: string }
  | { status: 'permission_denied' };

export async function registerDeviceForPushNotifications(): Promise<PushRegistrationResult> {
  const token = await getExpoPushToken();
  if (!token) {
    return { status: 'permission_denied' };
  }
  const device = await apiRequest<DeviceResponse>('/api/v1/devices', {
    method: 'POST',
    body: {
      platform: platformForApi(),
      push_token: token,
    },
  });
  await saveRegisteredDeviceId(device.id);
  return { status: 'registered', deviceId: device.id };
}

export async function unregisterCurrentDevice(): Promise<void> {
  const deviceId = await getRegisteredDeviceId();
  if (!deviceId) return;
  try {
    await apiRequest(`/api/v1/devices/${deviceId}`, { method: 'DELETE' });
  } finally {
    await clearRegisteredDeviceId();
  }
}

function platformForApi(): DeviceResponse['platform'] {
  if (Platform.OS === 'ios') return 'IOS';
  if (Platform.OS === 'android') return 'ANDROID';
  return 'WEB';
}
