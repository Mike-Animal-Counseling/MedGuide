import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { ManualMedicationFormScreen } from '../screens/Patient/ManualMedicationFormScreen';
import { renderWithAccessibility } from './test-utils';

const mockNavigate = jest.fn();
const mockApiRequest = jest.fn();

jest.mock('../api/client', () => ({
  apiRequest: (...args: unknown[]) => mockApiRequest(...args),
}));

describe('ManualMedicationFormScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiRequest.mockResolvedValue({ id: 'med-1' });
  });

  it('creates a medication from confirmed manual entry', async () => {
    renderWithAccessibility(
      <ManualMedicationFormScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: undefined } as never}
      />,
    );

    fireEvent.changeText(screen.getByLabelText('Medication name'), 'Manual Medication');
    fireEvent.changeText(screen.getByLabelText('Medication instructions'), 'Follow the saved label.');
    fireEvent.press(screen.getByRole('button', { name: 'Save medication' }));

    await waitFor(() => {
      expect(mockApiRequest).toHaveBeenCalledWith('/api/v1/medications', {
        method: 'POST',
        body: expect.objectContaining({
          name: 'Manual Medication',
          instructions: 'Follow the saved label.',
          source: 'MANUAL',
        }),
      });
    });
  });
});
