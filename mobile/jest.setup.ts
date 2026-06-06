jest.mock('expo-notifications', () => ({
  addNotificationResponseReceivedListener: jest.fn(() => ({ remove: jest.fn() })),
  getExpoPushTokenAsync: jest.fn(async () => ({ data: 'ExpoPushToken[test]' })),
  requestPermissionsAsync: jest.fn(async () => ({ granted: false, status: 'denied' })),
}));
