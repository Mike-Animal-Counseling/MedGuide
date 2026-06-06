import { fireEvent, screen } from '@testing-library/react-native';

import { Medication } from '../api/types';
import { VoicePrompt } from '../components/VoicePrompt';
import { buildDoseVoicePrompt, MEDICATION_SAFETY_DISCLAIMER } from '../voice/doseVoicePrompt';
import { renderWithAccessibility } from './test-utils';

const mockSpeak = jest.fn();

jest.mock('expo-speech', () => ({
  speak: (...args: unknown[]) => mockSpeak(...args),
}));

describe('dose voice prompt', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('uses saved user-confirmed instruction and safety disclaimer', () => {
    const medication: Medication = {
      id: 'med-1',
      name: 'Confirmed Medication',
      form: 'TABLET',
      active: true,
      instructions: 'Take after breakfast.',
    };

    const text = buildDoseVoicePrompt(medication);

    expect(text).toBe(`Take after breakfast. ${MEDICATION_SAFETY_DISCLAIMER}`);
    expect(text).not.toMatch(/you should take|recommended dose/i);
  });

  it('speaks the exact safe text supplied to the component', () => {
    const text = `Take after breakfast. ${MEDICATION_SAFETY_DISCLAIMER}`;
    renderWithAccessibility(<VoicePrompt text={text} buttonTitle="Repeat instruction" />);

    fireEvent.press(screen.getByRole('button', { name: 'Repeat instruction' }));

    expect(mockSpeak).toHaveBeenCalledWith(text, { language: 'en-US', rate: 0.9 });
  });
});
