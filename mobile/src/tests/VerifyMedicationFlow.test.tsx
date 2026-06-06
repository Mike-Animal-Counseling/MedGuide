import { fireEvent, screen, waitFor } from '@testing-library/react-native';
import { ForwardedRef } from 'react';

import { VerifyMedicationScreen } from '../screens/Patient/VerifyMedicationScreen';
import { renderWithAccessibility } from './test-utils';

const mockVerifyMedicationImage = jest.fn();
const mockRequestCameraPermission = jest.fn();
const mockConfirmMutate = jest.fn();
const mockNeedsHelpMutate = jest.fn();
const mockSpeak = jest.fn();

jest.mock('../api/uploads', () => ({
  verifyMedicationImage: (...args: unknown[]) => mockVerifyMedicationImage(...args),
}));

jest.mock('../camera/camera', () => ({
  requestCameraPermission: () => mockRequestCameraPermission(),
}));

jest.mock('../hooks/useTodayDoseLogs', () => ({
  useTodayDoseLogs: () => ({
    data: [
      {
        id: 'dose-1',
        medication_id: 'med-1',
        schedule_id: 'schedule-1',
        scheduled_time: '2026-06-04T15:00:00.000Z',
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
        name: 'ExampleMed',
        dosage: '10 mg',
        form: 'TABLET',
        active: true,
        instructions: 'Take with food as saved on the label.',
      },
    ],
  }),
}));

jest.mock('../hooks/useDoseLogActions', () => ({
  useDoseLogActions: () => ({
    confirm: { isPending: false, mutate: mockConfirmMutate },
    needsHelp: { isPending: false, mutate: mockNeedsHelpMutate },
    skip: { isPending: false, mutate: jest.fn() },
  }),
}));

jest.mock('expo-speech', () => ({
  speak: (...args: unknown[]) => mockSpeak(...args),
}));

jest.mock('expo-camera', () => {
  const React = jest.requireActual<typeof import('react')>('react');
  const CameraView = React.forwardRef(
    (
      props: { onCameraReady?: () => void },
      ref: ForwardedRef<{ takePictureAsync: () => Promise<{ uri: string }> }>,
    ) => {
      React.useImperativeHandle(ref, () => ({
        takePictureAsync: jest.fn(async () => ({ uri: 'file:///verification.jpg' })),
      }));
      React.useEffect(() => {
        props.onCameraReady?.();
      }, [props]);
      return null;
    },
  );
  CameraView.displayName = 'MockCameraView';
  return {
    CameraView,
  };
});

describe('VerifyMedicationScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRequestCameraPermission.mockResolvedValue(true);
  });

  it('allows Mark as Taken for MATCH_LIKELY while using cautious wording', async () => {
    mockVerifyMedicationImage.mockResolvedValue(result('MATCH_LIKELY', 'This appears to match your scheduled medication, but please confirm if unsure.'));

    await verifyOnce();

    expect(await screen.findByText('Appears to match')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Mark dose as taken' })).toBeOnTheScreen();
    expect(screen.queryByText(/correct medication/i)).toBeNull();
  });

  it('shows extra confirmation for MATCH_UNCERTAIN', async () => {
    mockVerifyMedicationImage.mockResolvedValue(result('MATCH_UNCERTAIN', 'I am not fully sure this is the scheduled medication.'));

    await verifyOnce();

    expect(await screen.findByText('Match uncertain')).toBeOnTheScreen();
    expect(screen.getByText('Extra confirmation required')).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Mark as taken after checking label' })).toBeOnTheScreen();
    expect(screen.getByRole('button', { name: 'Contact caregiver' })).toBeOnTheScreen();
  });

  it('hides primary Mark as Taken and offers caregiver contact for caregiver review', async () => {
    mockVerifyMedicationImage.mockResolvedValue(result('CAREGIVER_REVIEW_REQUIRED', 'I cannot confirm this medication. Please do not rely on this result alone.'));

    await verifyOnce();

    expect(await screen.findByText('Caregiver review needed')).toBeOnTheScreen();
    expect(screen.queryByRole('button', { name: 'Mark dose as taken' })).toBeNull();
    fireEvent.press(screen.getByRole('button', { name: 'Contact caregiver' }));
    expect(mockNeedsHelpMutate).toHaveBeenCalledWith('dose-1');
  });

  it('asks the user to retake unreadable images', async () => {
    mockVerifyMedicationImage.mockResolvedValue(result('UNREADABLE_IMAGE', 'I cannot read this image. Please retake the photo.'));

    await verifyOnce();

    expect(await screen.findByText('Image unreadable')).toBeOnTheScreen();
    fireEvent.press(screen.getByRole('button', { name: 'Retake verification photo' }));
    expect(screen.queryByText('Image unreadable')).toBeNull();
    expect(screen.getByRole('button', { name: 'Capture and check medication' })).toBeOnTheScreen();
  });

  it('speaks the backend safety message exactly', async () => {
    const safetyMessage = 'This appears to match your scheduled medication, but please confirm with the label or caregiver if unsure.';
    mockVerifyMedicationImage.mockResolvedValue(result('MATCH_LIKELY', safetyMessage));

    await verifyOnce();
    fireEvent.press(await screen.findByRole('button', { name: 'Read verification result' }));

    expect(mockSpeak).toHaveBeenCalledWith(safetyMessage, { language: 'en-US', rate: 0.9 });
  });

  it('sends the selected dose and captured image to verification upload flow', async () => {
    mockVerifyMedicationImage.mockResolvedValue(result('MATCH_LIKELY', 'This appears to match your scheduled medication.'));

    await verifyOnce();

    expect(mockVerifyMedicationImage).toHaveBeenCalledWith({
      doseLogId: 'dose-1',
      asset: {
        uri: 'file:///verification.jpg',
        contentType: 'image/jpeg',
        fileName: 'medication-verification.jpg',
      },
    });
  });
});

async function verifyOnce() {
  renderWithAccessibility(
    <VerifyMedicationScreen
      navigation={{ navigate: jest.fn() } as never}
      route={{ params: { doseLogId: 'dose-1' } } as never}
    />,
  );

  fireEvent.press(screen.getByRole('button', { name: 'Allow camera for verification' }));
  fireEvent.press(await screen.findByRole('button', { name: 'Capture and check medication' }));

  await waitFor(() => {
    expect(mockVerifyMedicationImage).toHaveBeenCalled();
  });
}

function result(
  verificationResult: string,
  safetyMessage: string,
): {
  image_id: string;
  result: string;
  confidence_score: number;
  requires_confirmation: true;
  safety_message: string;
} {
  return {
    image_id: 'image-1',
    result: verificationResult,
    confidence_score: 0.9,
    requires_confirmation: true,
    safety_message: safetyMessage,
  };
}
