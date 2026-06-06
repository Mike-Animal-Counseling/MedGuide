import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { TodayScheduleScreen } from '../screens/Patient/TodayScheduleScreen';
import { renderWithAccessibility } from './test-utils';

const mockApiRequest = jest.fn();

jest.mock('../api/client', () => ({
  apiRequest: (...args: unknown[]) => mockApiRequest(...args),
}));

describe('TodayScheduleScreen dose actions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiRequest.mockImplementation((path: string) => {
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
            name: 'Confirmed Medication',
            form: 'TABLET',
            active: true,
            instructions: 'Take after breakfast.',
          },
        ]);
      }
      return Promise.resolve({
        id: 'dose-1',
        medication_id: 'med-1',
        schedule_id: 'schedule-1',
        scheduled_time: '2026-06-04T15:00:00.000Z',
        status: 'TAKEN_ON_TIME',
      });
    });
  });

  it('confirms a dose through the backend API', async () => {
    renderWithAccessibility(
      <TodayScheduleScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />,
    );

    fireEvent.press(await screen.findByRole('button', { name: 'Confirm Confirmed Medication taken' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith(
        '/api/v1/dose-logs/dose-1/confirm',
        expect.objectContaining({ method: 'PATCH' }),
      );
    });
  });

  it('skips a dose through the backend API', async () => {
    renderWithAccessibility(
      <TodayScheduleScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />,
    );

    fireEvent.press(await screen.findByRole('button', { name: 'Skip Confirmed Medication dose' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith(
        '/api/v1/dose-logs/dose-1/skip',
        expect.objectContaining({ method: 'PATCH', body: {} }),
      );
    });
  });

  it('marks a dose as needs help through the backend API', async () => {
    renderWithAccessibility(
      <TodayScheduleScreen navigation={{ navigate: jest.fn() } as never} route={{} as never} />,
    );

    fireEvent.press(await screen.findByRole('button', { name: 'Need help with Confirmed Medication' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith(
        '/api/v1/dose-logs/dose-1/needs-help',
        expect.objectContaining({ method: 'PATCH', body: {} }),
      );
    });
  });
});
