import type { ReactNode } from 'react';
import { Suspense, lazy } from 'react';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';

import { AppShell } from '@/components/app-shell';
import { ProtectedRoute } from '@/components/protected-route';
import { LoadingState } from '@/components/states';

const LoginPage = lazy(() => import('@/pages/login'));
const DashboardPage = lazy(() => import('@/pages/dashboard'));
const HistoryPage = lazy(() => import('@/pages/history'));
const AlertsPage = lazy(() => import('@/pages/alerts'));
const SettingsPage = lazy(() => import('@/pages/settings'));
const AccountsPage = lazy(() => import('@/pages/accounts'));

function lazyPage(node: ReactNode): ReactNode {
  return <Suspense fallback={<LoadingState />}>{node}</Suspense>;
}

const router = createBrowserRouter([
  { path: '/login', element: lazyPage(<LoginPage />) },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: lazyPage(<DashboardPage />) },
          { path: 'history', element: lazyPage(<HistoryPage />) },
          { path: 'alerts', element: lazyPage(<AlertsPage />) },
          { path: 'settings', element: lazyPage(<SettingsPage />) },
          { path: 'accounts', element: lazyPage(<AccountsPage />) },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
