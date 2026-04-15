import { create } from 'zustand';
import type { User } from '@/types/api';

/**
 * Stockage des jetons d'authentification.
 *
 * Stratégie :
 *   - `accessToken` : uniquement en MÉMOIRE (état Zustand).
 *     N'est jamais persisté — perdu au refresh. C'est voulu : un XSS ne
 *     peut pas le récupérer depuis localStorage/sessionStorage.
 *   - `refreshToken` : persisté en `sessionStorage` (cloisonné à l'onglet).
 *
 *   ⚠️ RECOMMANDATION PRODUCTION
 *   Remplacer ce schéma par un cookie HttpOnly + Secure + SameSite=Lax émis
 *   par le backend pour le refresh token (invisible à JS donc immunisé XSS).
 *   Le présent fichier stocke en sessionStorage uniquement pour simplifier le
 *   MVP ; un attaquant XSS peut alors exfiltrer le refresh token. Voir
 *   `docs/SECURITY.md`.
 */

const REFRESH_STORAGE_KEY = 'icy.refresh_token';

function readRefreshToken(): string | null {
  try {
    return sessionStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeRefreshToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(REFRESH_STORAGE_KEY, token);
    else sessionStorage.removeItem(REFRESH_STORAGE_KEY);
  } catch {
    /* storage indisponible — ignoré */
  }
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isHydrated: boolean;
  setSession: (accessToken: string, refreshToken: string, user?: User | null) => void;
  setUser: (user: User | null) => void;
  setAccessToken: (token: string | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: readRefreshToken(),
  user: null,
  isHydrated: true,
  setSession: (accessToken, refreshToken, user = null) => {
    writeRefreshToken(refreshToken);
    set({ accessToken, refreshToken, user });
  },
  setAccessToken: (token) => set({ accessToken: token }),
  setUser: (user) => set({ user }),
  clear: () => {
    writeRefreshToken(null);
    set({ accessToken: null, refreshToken: null, user: null });
  },
}));

/** Lecture non-réactive (hors React). */
export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}

export function getRefreshToken(): string | null {
  return useAuthStore.getState().refreshToken;
}
