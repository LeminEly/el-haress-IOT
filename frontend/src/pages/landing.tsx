import { useTranslation } from 'react-i18next';
import { Link, Navigate } from 'react-router-dom';

import { LanguageSwitch } from '@/components/language-switch';
import { LogoMark } from '@/components/logo';
import { ThemeToggle } from '@/components/theme-toggle';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

function SectionHeader({ label, title }: { label: string; title: string }) {
  return (
    <div className="mx-auto mb-16 max-w-2xl text-center">
      <span className="mb-4 inline-block text-xs font-semibold uppercase tracking-[0.2em] text-fg-subtle">
        {label}
      </span>
      <h2 className="text-balance text-3xl font-medium tracking-tight md:text-4xl">{title}</h2>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="group rounded-xl border border-border bg-elevated p-6 shadow-sm transition-colors hover:border-fg-subtle/30 dark:shadow-none">
      <div className="mb-4 flex size-10 items-center justify-center rounded-lg border border-border bg-surface text-lg">
        {icon}
      </div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-fg-muted">{description}</p>
    </div>
  );
}

function StepCard({
  number,
  title,
  description,
}: {
  number: string;
  title: string;
  description: string;
}) {
  return (
    <div className="relative pl-12">
      <span className="absolute left-0 top-0 flex size-8 items-center justify-center rounded-full border border-border bg-surface text-xs font-semibold tabular-nums text-fg-muted">
        {number}
      </span>
      <h3 className="mb-1.5 text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-fg-muted">{description}</p>
    </div>
  );
}

function HardwareCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-elevated p-6 shadow-sm dark:shadow-none">
      <div className="mb-4 flex size-10 items-center justify-center rounded-lg border border-border bg-surface text-lg">
        {icon}
      </div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-fg-muted">{description}</p>
    </div>
  );
}

function AlertingCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-elevated p-6 shadow-sm dark:shadow-none">
      <div className="mb-4 flex size-10 items-center justify-center rounded-lg border border-border bg-surface text-lg">
        {icon}
      </div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-fg-muted">{description}</p>
    </div>
  );
}

function SupportCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-elevated p-6 shadow-sm dark:shadow-none">
      <div className="mb-4 flex size-10 items-center justify-center rounded-lg border border-border bg-surface text-lg">
        {icon}
      </div>
      <h3 className="mb-2 text-sm font-semibold">{title}</h3>
      <p className="text-sm leading-relaxed text-fg-muted">{description}</p>
    </div>
  );
}

export default function LandingPage() {
  const { t } = useTranslation();
  const token = useAuthStore((state) => state.token);
  if (token) {
    return <Navigate to="/app" replace />;
  }

  const features = [
    {
      icon: '\u25B6',
      key: 'featureRealTime',
    },
    {
      icon: '\u26A0',
      key: 'featureMultiChannel',
    },
    {
      icon: '\u229E',
      key: 'featureMultiTenant',
    },
    {
      icon: '\u23F1',
      key: 'featureRetention',
    },
    {
      icon: '\u26E8',
      key: 'featureSecurity',
    },
    {
      icon: '\u25A3',
      key: 'featureDashboard',
    },
  ] as const;

  const steps = ['step1', 'step2', 'step3', 'step4'] as const;

  const hardware = [
    { icon: '\u25A1', key: 'hardwareGateway' },
    { icon: '\u25B3', key: 'hardwarePi' },
    { icon: '\u25C7', key: 'hardwareSensor' },
    { icon: '\u25C9', key: 'hardwareTunnel' },
  ] as const;

  const alertingFeatures = [
    { icon: '\u2699', key: 'alertingRule' },
    { icon: '\u25C8', key: 'alertingChannels' },
    { icon: '\u21BB', key: 'alertingLifecycle' },
  ] as const;

  const supportItems = [
    { icon: '\u25B7', key: 'supportOnsite' },
    { icon: '\u2699', key: 'supportConfig' },
    { icon: '\u25C6', key: 'supportTraining' },
    { icon: '\u21BB', key: 'supportMaintenance' },
  ] as const;

  const useCases = [
    'useCase1',
    'useCase2',
    'useCase3',
    'useCase4',
    'useCase5',
    'useCase6',
  ] as const;

  return (
    <div className="min-h-dvh bg-bg text-fg">
      {/* ---- Navigation ---- */}
      <header className="fixed inset-x-0 top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-lg">
        <nav className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="inline-flex items-center gap-2">
            <LogoMark className="size-6" />
            <span className="text-sm font-semibold tracking-tight">{t('app.name')}</span>
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitch />
            <ThemeToggle />
            <Link
              to="/login"
              className={cn(buttonVariants({ variant: 'primary', size: 'sm' }), 'ml-1')}
            >
              {t('landing.heroCta')}
            </Link>
          </div>
        </nav>
      </header>

      {/* ---- Hero ---- */}
      <section className="relative flex min-h-dvh items-center justify-center overflow-hidden px-4 pt-14">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,color-mix(in_srgb,var(--color-fg)_3%,transparent)_0%,transparent_70%)] dark:bg-[radial-gradient(ellipse_at_center,var(--color-surface)_0%,transparent_70%)]" />
        <div className="relative mx-auto max-w-3xl text-center">
          <div className="mb-8 flex justify-center">
            <LogoMark className="size-20 text-fg md:size-24" />
          </div>
          <h1 className="mb-6 text-balance text-4xl font-medium tracking-tight md:text-5xl lg:text-6xl">
            {t('app.name')}
          </h1>
          <p className="mb-4 text-balance text-lg leading-relaxed text-fg-muted md:text-xl">
            {t('app.tagline')}
          </p>
          <p className="mb-10 text-balance text-sm leading-relaxed text-fg-subtle md:text-base">
            {t('landing.heroSubtitle')}
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              to="/login"
              className={cn(buttonVariants({ variant: 'primary', size: 'md' }), 'min-w-[200px]')}
            >
              {t('landing.heroCta')}
            </Link>
            <a
              href="#features"
              className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'min-w-[200px]')}
            >
              {t('landing.heroLearnMore')}
            </a>
          </div>
        </div>
      </section>

      {/* ---- Features ---- */}
      <section
        id="features"
        className="border-t border-border bg-surface/30 px-4 py-24 dark:bg-transparent"
      >
        <div className="mx-auto max-w-6xl">
          <SectionHeader
            label={t('landing.sectionFeatures')}
            title={t('landing.featureRealTime')}
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <FeatureCard
                key={f.key}
                icon={f.icon}
                title={t(`landing.${f.key}`)}
                description={t(`landing.${f.key}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ---- How it Works ---- */}
      <section className="border-t border-border px-4 py-24">
        <div className="mx-auto max-w-6xl">
          <SectionHeader label={t('landing.sectionHow')} title={t('landing.step1Title')} />
          <div className="mx-auto grid max-w-3xl gap-10">
            {steps.map((s, i) => (
              <StepCard
                key={s}
                number={String(i + 1)}
                title={t(`landing.${s}Title`)}
                description={t(`landing.${s}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ---- Hardware ---- */}
      <section className="border-t border-border px-4 py-24">
        <div className="mx-auto max-w-6xl">
          <SectionHeader label={t('landing.sectionHardware')} title={t('landing.hardwareTitle')} />
          <p className="mx-auto mb-12 max-w-2xl text-balance text-center text-sm leading-relaxed text-fg-muted">
            {t('landing.hardwareDesc')}
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {hardware.map((h) => (
              <HardwareCard
                key={h.key}
                icon={h.icon}
                title={t(`landing.${h.key}`)}
                description={t(`landing.${h.key}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ---- Alerting ---- */}
      <section className="border-t border-border bg-surface/30 px-4 py-24 dark:bg-transparent">
        <div className="mx-auto max-w-6xl">
          <SectionHeader label={t('landing.sectionAlerting')} title={t('landing.alertingTitle')} />
          <p className="mx-auto mb-12 max-w-2xl text-balance text-center text-sm leading-relaxed text-fg-muted">
            {t('landing.alertingDesc')}
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            {alertingFeatures.map((a) => (
              <AlertingCard
                key={a.key}
                icon={a.icon}
                title={t(`landing.${a.key}`)}
                description={t(`landing.${a.key}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ---- Product / Who is it for ---- */}
      <section className="border-t border-border bg-surface/30 px-4 py-24 dark:bg-transparent">
        <div className="mx-auto max-w-6xl">
          <SectionHeader label={t('landing.sectionProduct')} title={t('landing.productFor')} />
          <p className="mx-auto mb-12 max-w-2xl text-balance text-center text-sm leading-relaxed text-fg-muted">
            {t('landing.productForDesc')}
          </p>
          <div className="mx-auto max-w-3xl">
            <h3 className="mb-6 text-center text-sm font-semibold uppercase tracking-[0.15em] text-fg-subtle">
              {t('landing.productUseCases')}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {useCases.map((uc) => (
                <div
                  key={uc}
                  className="flex items-center gap-3 rounded-lg border border-border bg-elevated px-4 py-3 shadow-sm dark:shadow-none"
                >
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-normal/30 bg-normal/10 text-[10px] text-normal">
                    {'\u2713'}
                  </span>
                  <span className="text-sm text-fg-muted">{t(`landing.${uc}`)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ---- Why ---- */}
      <section className="border-t border-border px-4 py-24">
        <div className="mx-auto max-w-3xl text-center">
          <SectionHeader label={t('landing.sectionWhy')} title={t('landing.whyTitle')} />
          <p className="text-balance text-sm leading-relaxed text-fg-muted">
            {t('landing.whyDesc')}
          </p>
        </div>
      </section>

      {/* ---- Support ---- */}
      <section className="border-t border-border bg-surface/30 px-4 py-24 dark:bg-transparent">
        <div className="mx-auto max-w-6xl">
          <SectionHeader label={t('landing.sectionSupport')} title={t('landing.supportTitle')} />
          <p className="mx-auto mb-12 max-w-2xl text-balance text-center text-sm leading-relaxed text-fg-muted">
            {t('landing.supportDesc')}
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {supportItems.map((s) => (
              <SupportCard
                key={s.key}
                icon={s.icon}
                title={t(`landing.${s.key}`)}
                description={t(`landing.${s.key}Desc`)}
              />
            ))}
          </div>
        </div>
      </section>

      {/* ---- CTA ---- */}
      <section className="border-t border-border px-4 py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-6 text-balance text-3xl font-medium tracking-tight md:text-4xl">
            {t('landing.sectionCTA')}
          </h2>
          <p className="mb-10 text-balance text-sm leading-relaxed text-fg-muted">
            {t('landing.ctaDesc')}
          </p>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <a
              href="mailto:contact@awlyg.tech"
              className={cn(buttonVariants({ variant: 'primary', size: 'md' }), 'min-w-[200px]')}
            >
              {t('landing.ctaButton')}
            </a>
            <Link
              to="/login"
              className={cn(buttonVariants({ variant: 'outline', size: 'md' }), 'min-w-[200px]')}
            >
              {t('landing.ctaLogin')}
            </Link>
          </div>
        </div>
      </section>

      {/* ---- Footer ---- */}
      <footer className="border-t border-border px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="mb-3 inline-flex items-center gap-2">
                <LogoMark className="size-5" />
                <span className="text-sm font-semibold tracking-tight">{t('app.name')}</span>
              </div>
              <p className="text-xs leading-relaxed text-fg-subtle">{t('landing.footerTagline')}</p>
            </div>
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-fg-subtle">
                {t('landing.footerProduct')}
              </h4>
              <ul className="space-y-2 text-sm text-fg-muted">
                <li>
                  <a href="#features" className="transition-colors hover:text-fg">
                    {t('landing.footerFeatures')}
                  </a>
                </li>
                <li>
                  <a href="#features" className="transition-colors hover:text-fg">
                    {t('landing.footerHowItWorks')}
                  </a>
                </li>
                <li>
                  <a href="#features" className="transition-colors hover:text-fg">
                    {t('landing.footerHardware')}
                  </a>
                </li>
                <li>
                  <a href="#features" className="transition-colors hover:text-fg">
                    {t('landing.footerSupport')}
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-fg-subtle">
                {t('landing.footerCompany')}
              </h4>
              <ul className="space-y-2 text-sm text-fg-muted">
                <li>
                  <span>{t('landing.email')}</span>
                </li>
                <li>
                  <span>{t('landing.phone')}</span>
                </li>
                <li className="text-xs leading-relaxed text-fg-subtle">{t('landing.address')}</li>
                <li className="text-xs leading-relaxed text-fg-subtle">
                  {t('landing.addressMontreal')}
                </li>
              </ul>
            </div>
            <div>
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-fg-subtle">
                {t('landing.footerSupport')}
              </h4>
              <ul className="space-y-2 text-sm text-fg-muted">
                <li>
                  <a href="mailto:contact@awlyg.tech" className="transition-colors hover:text-fg">
                    {t('landing.footerContact')}
                  </a>
                </li>
                <li>
                  <a href="#" className="transition-colors hover:text-fg">
                    {t('landing.footerPrivacy')}
                  </a>
                </li>
                <li>
                  <a href="#" className="transition-colors hover:text-fg">
                    {t('landing.footerTerms')}
                  </a>
                </li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col items-center justify-between gap-4 border-t border-border pt-8 text-xs text-fg-subtle sm:flex-row">
            <span>
              &copy; {new Date().getFullYear()} Awlyg Tech. {t('landing.footerRights')}
            </span>
            <span>{t('landing.madeBy')} Awlyg Tech</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
