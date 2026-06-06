import * as Notifications from 'expo-notifications';

export async function requestNotificationPermission(): Promise<boolean> {
  const permission = await Notifications.requestPermissionsAsync();
  return permission.granted;
}

export async function getExpoPushToken(): Promise<string | null> {
  const permissionGranted = await requestNotificationPermission();
  if (!permissionGranted) return null;
  const token = await Notifications.getExpoPushTokenAsync();
  return token.data;
}
