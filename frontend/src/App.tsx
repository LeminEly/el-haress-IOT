import type { ReactNode } from 'react';
import { Suspense, lazy } from 'react';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';

import { AppShell } from '@/components/app-shell';
import { AdminRoute, ProtectedRoute } from '@/components/protected-route';
import { LoadingState } from '@/components/states';
import { useMe } from '@/hooks/use-auth';

const LandingPage = lazy(() => import('@/pages/landing'));
const LoginPage = lazy(() => import('@/pages/login'));
const DashboardPage = lazy(() => import('@/pages/dashboard'));
const HistoryPage = lazy(() => import('@/pages/history'));
const AlertsPage = lazy(() => import('@/pages/alerts'));
const SettingsPage = lazy(() => import('@/pages/settings'));
const AccountsPage = lazy(() => import('@/pages/accounts'));
const OverviewPage = lazy(() => import('@/pages/overview'));

function lazyPage(node: ReactNode): ReactNode {
  return <Suspense fallback={<LoadingState />}>{node}</Suspense>;
}

/** Accueil selon le role : l'exploitant arrive sur la vue d'ensemble plateforme,
 * l'entreprise sur son tableau de bord de supervision. */
function HomeRedirect() {
  const { data: account, isLoading } = useMe();
  if (isLoading) {
    return <LoadingState />;
  }
  return <Navigate to={account?.role === 'SUPER_ADMIN' ? '/overview' : '/dashboard'} replace />;
}

const router = createBrowserRouter([
  { path: '/', element: lazyPage(<LandingPage />) },
  { path: '/login', element: lazyPage(<LoginPage />) },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          // '/' est la landing publique ; l'entree de l'app protegee est '/app',
          // qui redirige vers l'accueil du role. Aucune route protegee ne
          // reclame '/' (sinon un visiteur anonyme serait renvoye au login).
          { path: 'app', element: <HomeRedirect /> },
          { path: 'dashboard', element: lazyPage(<DashboardPage />) },
          { path: 'history', element: lazyPage(<HistoryPage />) },
          { path: 'alerts', element: lazyPage(<AlertsPage />) },
          { path: 'settings', element: lazyPage(<SettingsPage />) },
          {
            element: <AdminRoute />,
            children: [
              { path: 'overview', element: lazyPage(<OverviewPage />) },
              { path: 'accounts', element: lazyPage(<AccountsPage />) },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
