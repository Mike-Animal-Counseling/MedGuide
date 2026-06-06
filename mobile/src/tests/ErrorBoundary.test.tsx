import { render, screen } from '@testing-library/react-native';
import { ReactNode } from 'react';
import { Text } from 'react-native';

import { ErrorBoundary } from '../components/ErrorBoundary';
import { reportClientError } from '../observability/errorReporter';

jest.mock('../observability/errorReporter', () => ({
  reportClientError: jest.fn(),
}));

describe('ErrorBoundary', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => undefined);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <Text>Safe content</Text>
      </ErrorBoundary>,
    );

    expect(screen.getByText('Safe content')).toBeOnTheScreen();
  });

  it('shows safe fallback UI and reports sanitized boundary context', () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    expect(
      screen.getByText('Something went wrong. Please restart the app or try again later.'),
    ).toBeOnTheScreen();
    expect(reportClientError).toHaveBeenCalledWith(expect.any(Error), {
      boundary: 'AppErrorBoundary',
    });
  });
});

function ThrowingChild(): ReactNode {
  throw new Error('Sensitive internal detail');
}
