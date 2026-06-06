import { Camera } from 'expo-camera';

export async function requestCameraPermission(): Promise<boolean> {
  const permission = await Camera.requestCameraPermissionsAsync();
  return permission.granted;
}
