import { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/lib/auth';

interface ProtectedRouteProps {
  children: ReactNode;
}

/**
 * Bloque l'accès si aucune session n'est présente. Redirige vers /login en
 * conservant l'intention (`from`) pour un retour après login.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthed = useAuthStore((s) => Boolean(s.accessToken));
  const location = useLocation();

  if (!isAuthed) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}
