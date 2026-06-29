import { useTranslation } from 'react-i18next';

import { cn } from '@/lib/utils';

/** Marque El-Haress : bouclier + courbe de supervision + noeuds reseau.
 *  Monochrome via `currentColor` : nette en clair comme en sombre. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn('size-7', className)}
      role="img"
      aria-label="El-Haress"
    >
      <path d="M16 3 26.5 6.8V14.5C26.5 21.5 21.8 26.4 16 28.6 10.2 26.4 5.5 21.5 5.5 14.5V6.8Z" />
      <path d="M9.5 15.5H12L13.7 11 16.4 19 18 14.5 19.6 15.5H22.5" />
      <path d="M12 22 16.5 23.2 20.5 21.5" strokeWidth={1} />
      <circle cx="12" cy="22" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="16.5" cy="23.2" r="1.05" fill="currentColor" stroke="none" />
      <circle cx="20.5" cy="21.5" r="1.05" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function Logo({ className, markClassName }: { className?: string; markClassName?: string }) {
  const { t } = useTranslation();
  return (
    <span className={cn('inline-flex items-center gap-2 text-fg', className)}>
      <LogoMark className={markClassName} />
      <span className="text-lg font-semibold tracking-tight">{t('app.name')}</span>
    </span>
  );
}
