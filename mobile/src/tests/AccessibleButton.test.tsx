import { fireEvent, screen } from '@testing-library/react-native';

import { AccessibleButton } from '../components/AccessibleButton';
import { renderWithAccessibility } from './test-utils';

describe('AccessibleButton', () => {
  it('renders an accessible button and handles presses', async () => {
    const onPress = jest.fn();

    await renderWithAccessibility(
      <AccessibleButton
        title="Continue"
        onPress={onPress}
        accessibilityLabel="Continue medication setup"
        accessibilityHint="Moves to the next medication setup step"
      />,
    );

    await fireEvent.press(screen.getByRole('button', { name: 'Continue medication setup' }));

    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
