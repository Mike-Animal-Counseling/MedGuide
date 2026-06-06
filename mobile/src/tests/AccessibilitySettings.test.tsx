import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { Text } from 'react-native';

import { useAccessibility } from '../accessibility/AccessibilityContext';
import { apiRequest } from '../api/client';
import { AccessibilitySettingsScreen } from '../screens/Settings/AccessibilitySettingsScreen';
import { renderWithAccessibility } from './test-utils';

jest.mock('../api/client', () => ({
  apiRequest: jest.fn(),
}));

describe('accessibility settings screen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiRequest as jest.Mock).mockResolvedValue({ id: 'link-1', status: 'REVOKED' });
  });

  it('toggles high contrast and large text behavior through accessible controls', () => {
    renderWithAccessibility(
      <>
        <AccessibilitySettingsScreen />
        <ThemeProbe />
      </>,
    );

    expect(screen.getByText('contrast:false text:16')).toBeOnTheScreen();

    fireEvent(screen.getByLabelText('High contrast'), 'valueChange', true);
    fireEvent(screen.getByLabelText('Large text'), 'valueChange', true);

    expect(screen.getByText('contrast:true text:20')).toBeOnTheScreen();
  });

  it('revokes caregiver access through the backend', async () => {
    renderWithAccessibility(<AccessibilitySettingsScreen />);

    fireEvent.changeText(screen.getByLabelText('Caregiver link id'), 'link-1');
    fireEvent.press(screen.getByRole('button', { name: 'Revoke caregiver access' }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/caregivers/links/link-1/revoke', {
        method: 'PATCH',
        body: {},
      });
    });
    expect(await screen.findByText('Caregiver access was revoked.')).toBeOnTheScreen();
  });
});

function ThemeProbe() {
  const { highContrast, theme } = useAccessibility();
  return <Text>{`contrast:${String(highContrast)} text:${theme.fontSize.body}`}</Text>;
}
