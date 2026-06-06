export type ThemeMode = {
  highContrast: boolean;
  largeText: boolean;
};

export function createTheme(mode: ThemeMode) {
  return {
    colors: {
      background: mode.highContrast ? '#000000' : '#F3F8F7',
      surface: mode.highContrast ? '#111111' : '#FFFFFF',
      text: mode.highContrast ? '#FFFFFF' : '#123D36',
      mutedText: mode.highContrast ? '#F2F2F2' : '#244A44',
      primary: mode.highContrast ? '#FFFF00' : '#146C5F',
      danger: mode.highContrast ? '#FFB3B3' : '#8A1F11',
      border: mode.highContrast ? '#FFFFFF' : '#8AAFA8',
    },
    fontSize: {
      body: mode.largeText ? 20 : 16,
      title: mode.largeText ? 34 : 28,
      button: mode.largeText ? 22 : 18,
    },
    spacing: { sm: 8, md: 16, lg: 24 },
  };
}
