import { format, formatDistanceToNow } from 'date-fns';
import { ar, enUS, fr } from 'date-fns/locale';

const LOCALES = { fr, ar, en: enUS } as const;

function dfnsLocale(locale: string) {
  return LOCALES[locale as keyof typeof LOCALES] ?? fr;
}

export function formatDateTime(value: string, locale: string): string {
  return format(new Date(value), 'Pp', { locale: dfnsLocale(locale) });
}

export function formatRelative(value: string, locale: string): string {
  return formatDistanceToNow(new Date(value), { addSuffix: true, locale: dfnsLocale(locale) });
}

export function formatValue(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value);
}
