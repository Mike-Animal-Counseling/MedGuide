import { render, screen, waitFor } from '@testing-library/react-native';

import { RootNavigator } from '../navigation/RootNavigator';
import { AccessibilityProvider } from '../accessibility/AccessibilityContext';

jest.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    signIn: jest.fn(),
    register: jest.fn(),
    signOut: jest.fn(),
  }),
}));

describe('RootNavigator', () => {
  it('renders the unauthenticated navigation flow', async () => {
    renderWithNavigation();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Sign in' })).toBeOnTheScreen();
    });
  });
});

function renderWithNavigation() {
  return render(
    <AccessibilityProvider>
      <RootNavigator />
    </AccessibilityProvider>,
  );
}
