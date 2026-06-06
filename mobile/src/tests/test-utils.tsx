import { render, RenderOptions } from '@testing-library/react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactElement } from 'react';

import { AccessibilityProvider } from '../accessibility/AccessibilityContext';

export function renderWithAccessibility(ui: ReactElement, options?: RenderOptions) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { gcTime: Infinity, retry: false },
      mutations: { gcTime: Infinity, retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AccessibilityProvider>{ui}</AccessibilityProvider>
    </QueryClientProvider>,
    options,
  );
}
