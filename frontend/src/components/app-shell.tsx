import { Activity, Bell, GaugeCircle, History, LogOut, Settings, Users } from 'lucide-react';
import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { LanguageSwitch } from '@/components/language-switch';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  key: string;
  icon: ComponentType<{ className?: string }>;
  end?: boolean;
}

const BASE_NAV: NavItem[] = [
  { to: '/', key: 'nav.dashboard', icon: GaugeCircle, end: true },
  { to: '/history', key: 'nav.history', icon: History },
  { to: '/alerts', key: 'nav.alerts', icon: Bell },
  { to: '/settings', key: 'nav.settings', icon: Settings },
];

function NavItems({ items }: { items: NavItem[] }) {
  const { t } = useTranslation();
  return (
    <>
      {items.map(({ to, key, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
              isActive ? 'bg-surface text-fg' : 'text-fg-muted hover:bg-surface',
            )
          }
        >
          <Icon className="size-4" />
          {t(key)}
        </NavLink>
      ))}
    </>
  );
}

export function AppShell() {
  const { t } = useTranslation();
  const { data: account } = useMe();
  const logout = useLogout();
  const navigate = useNavigate();

  const items =
    account?.role === 'SUPER_ADMIN'
      ? [...BASE_NAV, { to: '/accounts', key: 'nav.accounts', icon: Users }]
      : BASE_NAV;

  const handleLogout = () => logout.mutate(undefined, { onSettled: () => navigate('/login') });

  return (
    <div className="flex min-h-dvh">
      <aside className="hidden w-60 shrink-0 flex-col gap-2 border-e border-border bg-elevated md:flex">
        <div className="flex items-center gap-2 px-5 py-4">
          <Activity className="size-5 text-primary" aria-hidden="true" />
          <span className="text-lg font-semibold tracking-tight">{t('app.name')}</span>
        </div>
        <nav className="flex flex-col gap-1 px-3">
          <NavItems items={items} />
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 md:px-6">
          <span className="truncate text-sm text-fg-muted">{account?.company_name ?? ''}</span>
          <div className="flex items-center gap-2">
            <LanguageSwitch />
            <ThemeToggle />
            <Button variant="ghost" size="icon" aria-label={t('nav.logout')} onClick={handleLogout}>
              <LogOut className="size-5" />
            </Button>
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-border px-2 py-2 md:hidden">
          <NavItems items={items} />
        </nav>

        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
