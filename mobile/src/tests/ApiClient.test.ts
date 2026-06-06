import { apiRequest } from '../api/client';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async (key: string) => (key === 'medguide.accessToken' ? 'access-token' : null)),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

describe('apiRequest', () => {
  beforeEach(() => {
    process.env.EXPO_PUBLIC_API_BASE_URL = 'https://api.example.test';
    globalThis.fetch = jest.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ ok: true }),
    })) as jest.Mock;
  });

  it('attaches bearer token from SecureStore', async () => {
    await apiRequest('/api/v1/auth/me');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/auth/me',
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    const [, options] = (globalThis.fetch as jest.Mock).mock.calls[0];
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer access-token');
  });
});
