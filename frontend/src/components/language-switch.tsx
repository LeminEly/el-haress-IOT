import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { type Locale, SUPPORTED_LOCALES } from '@/i18n';
import { useSettings } from '@/stores/settings';

const LOCALE_LABELS: Record<Locale, string> = {
  fr: 'FR',
  ar: 'العربية',
  en: 'EN',
};

export function LanguageSwitch() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const setLocale = useSettings((state) => state.setLocale);

  return (
    <div role="group" aria-label={t('language.label')} className="flex gap-1">
      {SUPPORTED_LOCALES.map((value) => (
        <Button
          key={value}
          variant={value === locale ? 'primary' : 'ghost'}
          size="sm"
          aria-pressed={value === locale}
          onClick={() => setLocale(value)}
        >
          {LOCALE_LABELS[value]}
        </Button>
      ))}
    </div>
  );
}
