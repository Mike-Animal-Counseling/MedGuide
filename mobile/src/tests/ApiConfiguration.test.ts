import { getApiBaseUrl, ConfigurationError } from '../api/config';

describe('production API transport configuration', () => {
  it('accepts explicit HTTPS and rejects credential-bearing or remote HTTP endpoints', () => {
    process.env.EXPO_PUBLIC_API_BASE_URL = 'https://api.example.test';
    expect(getApiBaseUrl()).toBe('https://api.example.test');
    for (const value of ['http://api.example.test', 'https://user:password@api.example.test', 'https://api.example.test?token=x']) {
      process.env.EXPO_PUBLIC_API_BASE_URL = value;
      expect(getApiBaseUrl).toThrow(ConfigurationError);
    }
  });
});
