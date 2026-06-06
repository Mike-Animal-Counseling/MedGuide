import { fireEvent, screen } from '@testing-library/react-native';

import { uploadMedicationLabelImage, verifyMedicationImage } from '../api/uploads';
import { ScanLabelScreen } from '../screens/Patient/ScanLabelScreen';
import { renderWithAccessibility } from './test-utils';

const mockNavigate = jest.fn();
const mockRequestCameraPermission = jest.fn();
const mockApiRequest = jest.fn();

jest.mock('../camera/camera', () => ({
  requestCameraPermission: () => mockRequestCameraPermission(),
}));

jest.mock('../api/client', () => ({
  apiRequest: (...args: unknown[]) => mockApiRequest(...args),
}));

jest.mock('expo-camera', () => ({
  CameraView: () => null,
}));

describe('ScanLabelScreen camera fallback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows an accessible manual-entry fallback when camera permission is denied', async () => {
    mockRequestCameraPermission.mockResolvedValue(false);

    renderWithAccessibility(
      <ScanLabelScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    fireEvent.press(screen.getByRole('button', { name: 'Allow camera' }));

    expect(await screen.findByText('Camera permission was not granted. You can add this medication manually.')).toBeOnTheScreen();
    fireEvent.press(screen.getByRole('button', { name: 'Enter medication manually' }));
    expect(mockNavigate).toHaveBeenCalledWith('ManualMedicationForm');
  });
});

describe('signed upload and OCR flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    globalThis.fetch = jest.fn(async () => ({ ok: true })) as jest.Mock;
    mockApiRequest.mockImplementation((path: string) => {
      if (path === '/api/v1/uploads/signed-url') {
        return Promise.resolve({
          image_id: 'image-1',
          upload_url: 'https://storage.example.test/upload',
          upload_fields: { key: 'users/user-1/images/image-1', policy: 'signed-policy' },
          expires_in_seconds: 300,
        });
      }
      if (path === '/api/v1/ai/scan-label') {
        return Promise.resolve({
          result: 'LABEL_READ',
          ocr_text: 'Medication Name Example',
          extracted_fields: { name: 'Medication Name Example' },
          confidence_score: 0.81,
          requires_confirmation: true,
          safety_message: 'Please confirm the extracted medication information before saving.',
        });
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });
  });

  it('uses the API client for signed upload and scan-label requests', async () => {
    const result = await uploadMedicationLabelImage({
      uri: 'file:///label.jpg',
      contentType: 'image/jpeg',
      sizeBytes: 1234,
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/uploads/signed-url', {
      method: 'POST',
      body: {
        purpose: 'MEDICATION_LABEL',
        content_type: 'image/jpeg',
        size_bytes: 1234,
      },
    });
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'https://storage.example.test/upload',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
    );
    expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/ai/scan-label', {
      method: 'POST',
      body: { image_id: 'image-1' },
    });
    expect(result.requires_confirmation).toBe(true);
  });

  it('uses signed upload and backend verification for medication checks', async () => {
    mockApiRequest.mockImplementation((path: string) => {
      if (path === '/api/v1/uploads/signed-url') {
        return Promise.resolve({
          image_id: 'verification-image-1',
          upload_url: 'https://storage.example.test/upload',
          upload_fields: { key: 'users/user-1/images/verification-image-1' },
          expires_in_seconds: 300,
        });
      }
      if (path === '/api/v1/ai/verify-medication') {
        return Promise.resolve({
          result: 'MATCH_LIKELY',
          confidence_score: 0.9,
          requires_confirmation: true,
          safety_message: 'This appears to match your scheduled medication, but please confirm if unsure.',
        });
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });

    const verification = await verifyMedicationImage({
      doseLogId: 'dose-1',
      asset: {
        uri: 'file:///verification.jpg',
        contentType: 'image/jpeg',
      },
    });

    expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/uploads/signed-url', {
      method: 'POST',
      body: {
        purpose: 'VERIFICATION_IMAGE',
        content_type: 'image/jpeg',
        size_bytes: undefined,
      },
    });
    expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/ai/verify-medication', {
      method: 'POST',
      body: {
        dose_log_id: 'dose-1',
        image_id: 'verification-image-1',
        verification_type: 'PILL_VERIFY',
      },
    });
    expect(verification.result).toBe('MATCH_LIKELY');
  });
});
