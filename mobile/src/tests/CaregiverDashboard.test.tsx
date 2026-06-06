import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { apiRequest } from '../api/client';
import { CaregiverHomeScreen } from '../screens/Caregiver/CaregiverHomeScreen';
import { CaregiverInviteAcceptScreen } from '../screens/Caregiver/CaregiverInviteAcceptScreen';
import { CaregiverVerificationReviewScreen } from '../screens/Caregiver/CaregiverVerificationReviewScreen';
import { PatientDetailScreen } from '../screens/Caregiver/PatientDetailScreen';
import { renderWithAccessibility } from './test-utils';

const mockNavigate = jest.fn();

jest.mock('../api/client', () => ({
  apiRequest: jest.fn(),
}));

describe('caregiver mobile dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiRequest as jest.Mock).mockImplementation((path: string) => {
      if (path === '/api/v1/caregivers/patients') {
        return Promise.resolve([
          {
            link: {
              id: 'link-1',
              patient_id: 'patient-1',
              caregiver_email: 'caregiver@example.com',
              relationship: 'Daughter',
              permission_level: 'FULL_ACCESS',
              status: 'ACTIVE',
              created_at: '2026-06-04T00:00:00Z',
              accepted_at: '2026-06-04T00:00:00Z',
              revoked_at: null,
            },
            patient: {
              id: 'patient-1',
              email: 'patient@example.com',
              full_name: 'Pat Patient',
              role: 'PATIENT',
              timezone: 'America/Chicago',
              accessibility_preferences: {},
            },
          },
        ]);
      }
      if (path === '/api/v1/caregivers/patients/patient-1/today') {
        return Promise.resolve({
          patient_id: 'patient-1',
          schedules: [],
          dose_logs: [
            {
              id: 'dose-1',
              medication_id: 'med-1',
              schedule_id: 'schedule-1',
              scheduled_time: '2026-06-04T15:00:00.000Z',
              status: 'MISSED',
            },
          ],
        });
      }
      if (path === '/api/v1/caregivers/patients/patient-1/dose-logs') {
        return Promise.resolve([
          {
            id: 'dose-1',
            medication_id: 'med-1',
            schedule_id: 'schedule-1',
            scheduled_time: '2026-06-04T15:00:00.000Z',
            status: 'VERIFICATION_FAILED',
          },
        ]);
      }
      if (path === '/api/v1/caregivers/accept') {
        return Promise.resolve({ id: 'link-2', status: 'ACTIVE' });
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });
  });

  it('shows linked patients and navigates to patient detail', async () => {
    renderWithAccessibility(
      <CaregiverHomeScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    fireEvent.press(await screen.findByLabelText('Open patient patient@example.com'));

    expect(mockNavigate).toHaveBeenCalledWith('PatientDetail', {
      patientId: 'patient-1',
      linkId: 'link-1',
      permissionLevel: 'FULL_ACCESS',
    });
    expect(screen.getByRole('button', { name: 'Accept caregiver invite' })).toBeOnTheScreen();
  });

  it("renders today's dose status and permission-based actions", async () => {
    renderWithAccessibility(
      <PatientDetailScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: { patientId: 'patient-1', permissionLevel: 'FULL_ACCESS' } } as never}
      />,
    );

    expect(await screen.findByText('Missed dose alerts')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Review AI verification events' })).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Manage patient medications' })).toBeOnTheScreen();
  });

  it('hides management UI for view-only caregiver links', async () => {
    renderWithAccessibility(
      <PatientDetailScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: { patientId: 'patient-1', permissionLevel: 'VIEW_ONLY' } } as never}
      />,
    );

    expect(await screen.findByText('Missed dose alerts')).toBeOnTheScreen();
    expect(await screen.findByText('View only')).toBeOnTheScreen();
    expect(screen.queryByRole('button', { name: 'Manage patient medications' })).toBeNull();
    expect(screen.getByText('Verification review unavailable')).toBeOnTheScreen();
  });

  it('displays safe error when caregiver access is denied or changed', async () => {
    (apiRequest as jest.Mock).mockRejectedValueOnce(new Error('forbidden'));

    renderWithAccessibility(
      <PatientDetailScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: { patientId: 'unlinked-patient', permissionLevel: 'FULL_ACCESS' } } as never}
      />,
    );

    expect(await screen.findByText('Patient data unavailable')).toBeOnTheScreen();
    expect(screen.getByText('Access may have changed.')).toBeOnTheScreen();
  });

  it('accepts caregiver invitations through the backend', async () => {
    renderWithAccessibility(
      <CaregiverInviteAcceptScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{} as never}
      />,
    );

    fireEvent.changeText(screen.getByLabelText('Caregiver invite token'), 'a'.repeat(32));
    fireEvent.press(screen.getByRole('button', { name: 'Accept caregiver invite' }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/caregivers/accept', {
        method: 'POST',
        body: { invite_token: 'a'.repeat(32) },
      });
    });
  });

  it('shows verification review boundary for FULL_ACCESS users', async () => {
    renderWithAccessibility(
      <CaregiverVerificationReviewScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: { patientId: 'patient-1', permissionLevel: 'FULL_ACCESS' } } as never}
      />,
    );

    expect(await screen.findByText('AI event access boundary')).toBeOnTheScreen();
    expect(await screen.findByText('Review verification failed')).toBeOnTheScreen();
  });
});
