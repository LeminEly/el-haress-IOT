import { Navigate, Outlet } from 'react-router-dom';

import { LoadingState } from '@/components/states';
import { useMe } from '@/hooks/use-auth';
import { useAuthStore } from '@/stores/auth';

export function ProtectedRoute() {
  const token = useAuthStore((state) => state.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

/**
 * Reserve une route au SUPER_ADMIN : une entreprise est redirigee vers l'accueil
 * (la garde backend renvoie deja 403, mais la route ne doit pas s'afficher).
 */
export function AdminRoute() {
  const { data: account, isLoading } = useMe();
  if (isLoading) {
    return <LoadingState />;
  }
  if (account?.role !== 'SUPER_ADMIN') {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
