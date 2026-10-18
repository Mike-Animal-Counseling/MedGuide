import { fireEvent, screen } from '@testing-library/react-native';

import { LoginScreen } from '../screens/Auth/LoginScreen';
import { RegisterScreen } from '../screens/Auth/RegisterScreen';
import { renderWithAccessibility } from './test-utils';

const mockSignIn = jest.fn();
const mockRegister = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    register: mockRegister,
    user: null,
    isLoading: false,
    signOut: jest.fn(),
  }),
}));

describe('Auth screens', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('validates login before calling auth', async () => {
    await renderWithAccessibility(<LoginScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />);

    await fireEvent.press(screen.getByRole('button', { name: 'Sign in' }));

    expect(mockSignIn).not.toHaveBeenCalled();
    expect(screen.getByText('Enter a valid email and password.')).toBeOnTheScreen();
  });

  it('validates registration password strength before calling auth', async () => {
    await renderWithAccessibility(
      <RegisterScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    await fireEvent.changeText(screen.getByLabelText('Full name'), 'Pat Patient');
    await fireEvent.changeText(screen.getByLabelText('Email address'), 'pat@example.com');
    await fireEvent.changeText(screen.getByLabelText('Password'), 'short');
    await fireEvent.press(screen.getByRole('button', { name: 'Register' }));

    expect(mockRegister).not.toHaveBeenCalled();
    expect(
      screen.getByText('Enter your name, a valid email, and a password of at least 12 characters.'),
    ).toBeOnTheScreen();
  });
});
