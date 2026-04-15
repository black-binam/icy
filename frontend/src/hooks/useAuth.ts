import { useCallback } from 'react';
import { apiPost } from '@/lib/api';
import { useAuthStore } from '@/lib/auth';
import type { AuthTokens, LoginRequest, User } from '@/types/api';

interface LoginResponse extends AuthTokens {
  user: User;
}

/**
 * Hook d'authentification exposant l'état et les actions.
 * Lecture fine : ne sélectionne que ce dont on a besoin pour éviter les re-renders.
 */
export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const clear = useAuthStore((s) => s.clear);

  const login = useCallback(
    async (credentials: LoginRequest): Promise<User> => {
      const data = await apiPost<LoginResponse, LoginRequest>('/auth/login', credentials);
      setSession(data.access_token, data.refresh_token, data.user);
      return data.user;
    },
    [setSession],
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiPost('/auth/logout');
    } catch {
      /* silencieux — on purge quoiqu'il arrive */
    }
    clear();
  }, [clear]);

  const refreshMe = useCallback(async (): Promise<User | null> => {
    try {
      const me = await apiPost<User>('/users/me/refresh-profile');
      setUser(me);
      return me;
    } catch {
      return null;
    }
  }, [setUser]);

  return {
    user,
    isAuthenticated: Boolean(accessToken),
    login,
    logout,
    refreshMe,
  };
}
