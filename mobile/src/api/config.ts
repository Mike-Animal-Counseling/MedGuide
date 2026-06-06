export class ConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigurationError';
  }
}

export function getApiBaseUrl(): string {
  const value = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (!value) {
    throw new ConfigurationError('EXPO_PUBLIC_API_BASE_URL is not configured');
  }
  return value.replace(/\/$/, '');
}
