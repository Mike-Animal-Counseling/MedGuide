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
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new ConfigurationError('EXPO_PUBLIC_API_BASE_URL must be an absolute URL');
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new ConfigurationError('API URL cannot contain credentials, a query or a fragment');
  }
  const local = ['localhost', '127.0.0.1', '10.0.2.2', '[::1]'].includes(parsed.hostname);
  if (parsed.protocol !== 'https:' && !(__DEV__ && local && parsed.protocol === 'http:')) {
    throw new ConfigurationError('Production API connections must use HTTPS');
  }
  return value.replace(/\/$/, '');
}
