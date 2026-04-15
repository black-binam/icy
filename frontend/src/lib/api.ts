import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';
import { getAccessToken, getRefreshToken, useAuthStore } from '@/lib/auth';
import type { AuthTokens } from '@/types/api';

/**
 * Instance Axios partagée.
 *
 * Règles de sécurité (cf. docs/SECURITY.md) :
 *   - Ne JAMAIS logger le token d'accès ni les corps de /auth/*.
 *   - Sur 401 : tenter un seul refresh, sinon purger la session.
 *   - Jamais de credentials dans l'URL (query string).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const AUTH_PATHS = ['/auth/login', '/auth/refresh', '/auth/register'];

interface RetriableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20_000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/* --------- Request interceptor : attache le bearer token --------- */
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/* --------- Refresh orchestration (single-flight) --------- */

let refreshPromise: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    // Appel direct (sans l'instance `api`) pour éviter les boucles d'intercepteur.
    const { data } = await axios.post<AuthTokens>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' }, timeout: 15_000 },
    );
    useAuthStore.getState().setSession(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    // Toute erreur sur le refresh → déconnexion ; ne pas logger les tokens.
    useAuthStore.getState().clear();
    return null;
  }
}

function isAuthPath(url: string | undefined): boolean {
  if (!url) return false;
  return AUTH_PATHS.some((p) => url.includes(p));
}

/* --------- Response interceptor : 401 → refresh une fois --------- */
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const status = error.response?.status;

    if (status === 401 && original && !original._retry && !isAuthPath(original.url)) {
      original._retry = true;

      refreshPromise ??= performRefresh().finally(() => {
        refreshPromise = null;
      });
      const newToken = await refreshPromise;
      if (newToken) {
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return api.request(original);
      }
    }

    return Promise.reject(error);
  },
);

/* --------- Helpers typés --------- */

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const { data } = await api.get<T>(url, config);
  return data;
}

export async function apiPost<TResp, TBody = unknown>(
  url: string,
  body?: TBody,
  config?: AxiosRequestConfig,
): Promise<TResp> {
  const { data } = await api.post<TResp>(url, body, config);
  return data;
}

export async function apiPut<TResp, TBody = unknown>(
  url: string,
  body?: TBody,
  config?: AxiosRequestConfig,
): Promise<TResp> {
  const { data } = await api.put<TResp>(url, body, config);
  return data;
}

export async function apiDelete<TResp = void>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<TResp> {
  const { data } = await api.delete<TResp>(url, config);
  return data;
}
