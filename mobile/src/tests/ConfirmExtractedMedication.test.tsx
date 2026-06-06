import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { ConfirmExtractedMedicationScreen } from '../screens/Patient/ConfirmExtractedMedicationScreen';
import { renderWithAccessibility } from './test-utils';

const mockNavigate = jest.fn();
const mockApiRequest = jest.fn();
const mockSpeak = jest.fn();

jest.mock('../api/client', () => ({
  apiRequest: (...args: unknown[]) => mockApiRequest(...args),
}));

jest.mock('expo-speech', () => ({
  speak: (...args: unknown[]) => mockSpeak(...args),
}));

const route = {
  params: {
    scan: {
      image_id: 'image-1',
      result: 'LABEL_READ',
      ocr_text: 'ExampleMed 10 mg Take with food',
      extracted_fields: {
        name: 'ExampleMed',
        dosage: '10 mg',
        instructions: 'Take with food as written on the label.',
      },
      confidence_score: 0.86,
      requires_confirmation: true,
      safety_message: 'Please confirm the extracted medication information before saving.',
    },
  },
};

describe('ConfirmExtractedMedicationScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiRequest.mockResolvedValue({ id: 'med-1' });
  });

  it('displays OCR output and does not create medication until confirmation', () => {
    renderWithAccessibility(
      <ConfirmExtractedMedicationScreen navigation={{ navigate: mockNavigate } as never} route={route as never} />,
    );

    expect(screen.getByText('OCR requires confirmation')).toBeOnTheScreen();
    expect(screen.getByText('ExampleMed 10 mg Take with food')).toBeOnTheScreen();
    expect(mockApiRequest).not.toHaveBeenCalled();
  });

  it('speaks extracted fields and safety message', () => {
    renderWithAccessibility(
      <ConfirmExtractedMedicationScreen navigation={{ navigate: mockNavigate } as never} route={route as never} />,
    );

    fireEvent.press(screen.getByRole('button', { name: 'Read extracted fields' }));

    expect(mockSpeak).toHaveBeenCalledWith(
      expect.stringContaining('Medication name: ExampleMed.'),
      { language: 'en-US', rate: 0.9 },
    );
    expect(mockSpeak).toHaveBeenCalledWith(
      expect.stringContaining('Please confirm the extracted medication information before saving.'),
      { language: 'en-US', rate: 0.9 },
    );
  });

  it('creates medication only after user confirms reviewed fields', async () => {
    renderWithAccessibility(
      <ConfirmExtractedMedicationScreen navigation={{ navigate: mockNavigate } as never} route={route as never} />,
    );

    fireEvent.press(screen.getByRole('button', { name: 'Confirm and save medication' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/medications', {
        method: 'POST',
        body: expect.objectContaining({
          name: 'ExampleMed',
          dosage: '10 mg',
          instructions: 'Take with food as written on the label.',
          label_image_id: 'image-1',
          source: 'MANUAL',
        }),
      });
    });
  });
});
