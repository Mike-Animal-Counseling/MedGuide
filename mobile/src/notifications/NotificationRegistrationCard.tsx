import { useState } from 'react';

import { AccessibleButton } from '../components/AccessibleButton';
import { StatusCard } from '../components/StatusCard';
import { registerDeviceForPushNotifications } from './deviceRegistration';

export function NotificationRegistrationCard() {
  const [message, setMessage] = useState<string | null>(null);
  const [isRegistering, setRegistering] = useState(false);

  async function register() {
    setRegistering(true);
    try {
      const result = await registerDeviceForPushNotifications();
      setMessage(
        result.status === 'registered'
          ? 'Reminder notifications are enabled for this device.'
          : 'Notification permission was not granted. You can still use the app and check reminders manually.',
      );
    } catch {
      setMessage('Reminder notifications could not be enabled. Please try again later.');
    } finally {
      setRegistering(false);
    }
  }

  return (
    <StatusCard
      title="Reminder notifications"
      message={
        message ??
        'Enable reminders on this device. Backend dose logs remain the source of truth.'
      }
    >
      <AccessibleButton
        title={isRegistering ? 'Enabling reminders...' : 'Enable reminders'}
        disabled={isRegistering}
        onPress={() => void register()}
        accessibilityLabel="Enable reminder notifications"
        accessibilityHint="Requests notification permission and registers this device with MedGuide"
      />
    </StatusCard>
  );
}
