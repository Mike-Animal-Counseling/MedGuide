import { createContext, PropsWithChildren, useContext, useMemo, useState } from 'react';

import { createTheme, ThemeMode } from '../theme/theme';

type AccessibilityContextValue = ThemeMode & {
  setHighContrast: (value: boolean) => void;
  setLargeText: (value: boolean) => void;
  theme: ReturnType<typeof createTheme>;
};

const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined);

export function AccessibilityProvider({ children }: PropsWithChildren) {
  const [highContrast, setHighContrast] = useState(false);
  const [largeText, setLargeText] = useState(false);
  const theme = useMemo(() => createTheme({ highContrast, largeText }), [highContrast, largeText]);
  const value = useMemo(
    () => ({ highContrast, largeText, setHighContrast, setLargeText, theme }),
    [highContrast, largeText, theme],
  );

  return (
    <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }
  return context;
}
