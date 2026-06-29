import { useTranslation } from 'react-i18next';

import { LanguageSwitch } from '@/components/language-switch';
import { ThemeToggle } from '@/components/theme-toggle';

const STATUSES = [
  { key: 'normal', dot: 'bg-normal' },
  { key: 'warning', dot: 'bg-warning' },
  { key: 'critical', dot: 'bg-critical' },
  { key: 'offline', dot: 'bg-offline' },
] as const;

export default function App() {
  const { t } = useTranslation();

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between border-b border-border px-6 py-4">
        <div className="flex items-baseline gap-3">
          <span className="text-lg font-semibold tracking-tight">{t('app.name')}</span>
          <span className="text-sm text-fg-muted">{t('app.tagline')}</span>
        </div>
        <div className="flex items-center gap-3">
          <LanguageSwitch />
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-16">
        <section className="rounded-lg border border-border bg-elevated p-8">
          <h1 className="text-2xl font-semibold tracking-tight">{t('foundation.title')}</h1>
          <p className="mt-3 text-fg-muted">{t('foundation.description')}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            {STATUSES.map(({ key, dot }) => (
              <div
                key={key}
                className="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-sm"
              >
                <span className={`size-2.5 rounded-full ${dot}`} aria-hidden="true" />
                <span>{t(`status.${key}`)}</span>
              </div>
            ))}
          </div>

          <p className="mt-8 text-sm text-fg-subtle">{t('foundation.ready')}</p>
        </section>
      </main>
    </div>
  );
}
