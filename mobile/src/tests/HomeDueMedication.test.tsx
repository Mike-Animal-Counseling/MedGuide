import { screen } from '@testing-library/react-native';

import { HomeScreen } from '../screens/Patient/HomeScreen';
import { renderWithAccessibility } from './test-utils';

jest.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: { full_name: 'Pat Patient' },
    signOut: jest.fn(),
  }),
}));

jest.mock('../hooks/useTodayDoseLogs', () => ({
  useTodayDoseLogs: () => ({
    isLoading: false,
    data: [
      {
        id: 'dose-1',
        medication_id: 'med-1',
        schedule_id: 'schedule-1',
        scheduled_time: '2020-01-01T12:00:00.000Z',
        status: 'PENDING',
      },
    ],
  }),
}));

jest.mock('../hooks/useMedications', () => ({
  useMedications: () => ({
    data: [
      {
        id: 'med-1',
        name: 'Atorvastatin',
        form: 'TABLET',
        active: true,
        instructions: 'Take with water as written on your saved label.',
      },
    ],
  }),
}));

describe('HomeScreen daily workflow', () => {
  it('displays the current due medication and main action', () => {
    renderWithAccessibility(<HomeScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />);

    expect(screen.getByText('Current due medication')).toBeOnTheScreen();
    expect(screen.getByText('Atorvastatin is due now.')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Start medication check' })).toBeOnTheScreen();
  });
});
