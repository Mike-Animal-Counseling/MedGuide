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

  it('validates login before calling auth', () => {
    renderWithAccessibility(<LoginScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />);

    fireEvent.press(screen.getByRole('button', { name: 'Sign in' }));

    expect(mockSignIn).not.toHaveBeenCalled();
    expect(screen.getByText('Enter a valid email and password.')).toBeOnTheScreen();
  });

  it('validates registration password strength before calling auth', () => {
    renderWithAccessibility(
      <RegisterScreen navigation={{ navigate: mockNavigate } as never} route={{} as never} />,
    );

    fireEvent.changeText(screen.getByLabelText('Full name'), 'Pat Patient');
    fireEvent.changeText(screen.getByLabelText('Email address'), 'pat@example.com');
    fireEvent.changeText(screen.getByLabelText('Password'), 'short');
    fireEvent.press(screen.getByRole('button', { name: 'Register' }));

    expect(mockRegister).not.toHaveBeenCalled();
    expect(
      screen.getByText('Enter your name, a valid email, and a password of at least 12 characters.'),
    ).toBeOnTheScreen();
  });
});
