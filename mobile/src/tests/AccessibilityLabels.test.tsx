import { screen } from '@testing-library/react-native';

import { HomeScreen } from '../screens/Patient/HomeScreen';
import { ScanLabelScreen } from '../screens/Patient/ScanLabelScreen';
import { renderWithAccessibility } from './test-utils';

jest.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { full_name: 'Pat Patient' },
    signOut: jest.fn(),
  }),
}));

jest.mock('../hooks/useTodayDoseLogs', () => ({
  useTodayDoseLogs: () => ({ data: [], isLoading: false }),
}));

jest.mock('../hooks/useMedications', () => ({
  useMedications: () => ({ data: [] }),
}));

jest.mock('expo-camera', () => ({
  CameraView: () => null,
  Camera: {
    requestCameraPermissionsAsync: jest.fn(async () => ({ granted: false })),
  },
}));

describe('critical screen accessibility labels', () => {
  it('labels patient home actions', () => {
    renderWithAccessibility(<HomeScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />);

    expect(screen.getByRole('button', { name: 'Start medication check' })).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Scan medication label' })).toBeOnTheScreen();
  });

  it('labels scan label controls', () => {
    renderWithAccessibility(<ScanLabelScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />);

    expect(screen.getByRole('button', { name: 'Allow camera' })).toBeOnTheScreen();
  });
});
