import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client';
import { AuthTokens, CurrentUser } from '../api/types';
import { unregisterCurrentDevice } from '../notifications/deviceRegistration';
import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from './tokenStorage';

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  signOut: () => Promise<void>;
};

type RegisterInput = {
  email: string;
  password: string;
  fullName: string;
  role: 'PATIENT' | 'CAREGIVER';
  timezone: string;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getAccessToken()
      .then(async token => {
        if (!token || !mounted) return;
        setUser(await apiRequest<CurrentUser>('/api/v1/auth/me'));
      })
      .catch(() => clearTokens())
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      signIn: async (email, password) => {
        const tokens = await apiRequest<AuthTokens>('/api/v1/auth/login', {
          method: 'POST',
          body: { email, password },
        });
        await saveTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
        setUser(await apiRequest<CurrentUser>('/api/v1/auth/me'));
      },
      register: async input => {
        const tokens = await apiRequest<AuthTokens>('/api/v1/auth/register', {
          method: 'POST',
          body: {
            email: input.email,
            password: input.password,
            full_name: input.fullName,
            role: input.role,
            timezone: input.timezone,
            accessibility_preferences: {},
          },
        });
        await saveTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
        setUser(await apiRequest<CurrentUser>('/api/v1/auth/me'));
      },
      signOut: async () => {
        const refreshToken = await getRefreshToken();
        try {
          await unregisterCurrentDevice();
          if (refreshToken) {
            await apiRequest('/api/v1/auth/logout', {
              method: 'POST',
              body: { refresh_token: refreshToken },
            });
          }
        } finally {
          await clearTokens();
          setUser(null);
        }
      },
    }),
    [isLoading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
