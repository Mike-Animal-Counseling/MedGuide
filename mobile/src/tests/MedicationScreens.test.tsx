import { fireEvent, screen, waitFor } from '@testing-library/react-native';

import { apiRequest } from '../api/client';
import { AddMedicationScreen } from '../screens/Patient/AddMedicationScreen';
import { ManualMedicationFormScreen } from '../screens/Patient/ManualMedicationFormScreen';
import { MedicationDetailScreen } from '../screens/Patient/MedicationDetailScreen';
import { MedicationListScreen } from '../screens/Patient/MedicationListScreen';
import { renderWithAccessibility } from './test-utils';

const mockNavigate = jest.fn();

jest.mock('../api/client', () => ({
  apiRequest: jest.fn(),
}));

describe('medication mobile screens', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiRequest as jest.Mock).mockImplementation((path: string) => {
      if (path === '/api/v1/medications') {
        return Promise.resolve([
          {
            id: 'med-1',
            name: 'ExampleMed',
            dosage: '10 mg',
            form: 'TABLET',
            active: true,
            instructions: 'Take with saved label instructions.',
          },
        ]);
      }
      if (path === '/api/v1/medications/med-1') {
        return Promise.resolve({
          id: 'med-1',
          name: 'ExampleMed',
          dosage: '10 mg',
          form: 'TABLET',
          active: true,
          instructions: 'Take with saved label instructions.',
        });
      }
      return Promise.reject(new Error(`Unexpected path ${path}`));
    });
  });

  it('renders medication list and opens selected medication', async () => {
    renderWithAccessibility(
      <MedicationListScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    expect(await screen.findByText('ExampleMed')).toBeOnTheScreen();
    expect(screen.getByText('10 mg')).toBeOnTheScreen();

    fireEvent.press(screen.getByLabelText('Open ExampleMed'));
    expect(mockNavigate).toHaveBeenCalledWith('MedicationDetail', { medicationId: 'med-1' });

    fireEvent.press(screen.getByRole('button', { name: 'Add medication' }));
    expect(mockNavigate).toHaveBeenCalledWith('AddMedication');
  });

  it('renders medication details and exposes edit flow', async () => {
    renderWithAccessibility(
      <MedicationDetailScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{ params: { medicationId: 'med-1' } } as never}
      />,
    );

    expect(await screen.findByText('ExampleMed')).toBeOnTheScreen();
    expect(screen.getByText('Take with saved label instructions.')).toBeOnTheScreen();

    fireEvent.press(screen.getByRole('button', { name: 'Edit ExampleMed' }));
    expect(mockNavigate).toHaveBeenCalledWith('ManualMedicationForm', {
      medicationId: 'med-1',
      extracted: {
        name: 'ExampleMed',
        dosage: '10 mg',
        instructions: 'Take with saved label instructions.',
      },
    });
  });

  it('updates an existing medication through the confirmed form', async () => {
    (apiRequest as jest.Mock).mockResolvedValueOnce({ id: 'med-1' });

    renderWithAccessibility(
      <ManualMedicationFormScreen
        navigation={{ navigate: mockNavigate } as never}
        route={{
          params: {
            medicationId: 'med-1',
            extracted: {
              name: 'ExampleMed',
              dosage: '10 mg',
              instructions: 'Take with saved label instructions.',
            },
          },
        } as never}
      />,
    );

    fireEvent.changeText(screen.getByLabelText('Medication instructions'), 'Updated confirmed text.');
    fireEvent.press(screen.getByRole('button', { name: 'Update medication' }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith('/api/v1/medications/med-1', {
        method: 'PATCH',
        body: expect.objectContaining({
          name: 'ExampleMed',
          dosage: '10 mg',
          instructions: 'Updated confirmed text.',
          source: 'MANUAL',
        }),
      });
    });
  });

  it('navigates from add medication choice to manual entry or scan label', () => {
    renderWithAccessibility(
      <AddMedicationScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    fireEvent.press(screen.getByRole('button', { name: 'Add medication manually' }));
    expect(mockNavigate).toHaveBeenCalledWith('ManualMedicationForm');

    fireEvent.press(screen.getByRole('button', { name: 'Scan medication label' }));
    expect(mockNavigate).toHaveBeenCalledWith('ScanLabel');
  });
});
