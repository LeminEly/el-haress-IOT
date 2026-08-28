import { create } from 'zustand';

import i18n, { type Locale, RTL_LOCALES } from '@/i18n';

export type Theme = 'light' | 'dark' | 'system';

const THEME_STORAGE_KEY = 'el-haress-theme';
const LOCALE_STORAGE_KEY = 'el-haress-locale';

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export function resolveIsDark(theme: Theme): boolean {
  return theme === 'dark' || (theme === 'system' && systemPrefersDark());
}

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', resolveIsDark(theme));
}

function applyLocale(locale: Locale): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = RTL_LOCALES.includes(locale) ? 'rtl' : 'ltr';
}

function initialTheme(): Theme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'dark';
}

function initialLocale(): Locale {
  const current = i18n.resolvedLanguage;
  return current === 'ar' || current === 'en' ? current : 'fr';
}

interface SettingsState {
  theme: Theme;
  locale: Locale;
  setTheme: (theme: Theme) => void;
  setLocale: (locale: Locale) => void;
}

export const useSettings = create<SettingsState>((set) => ({
  theme: initialTheme(),
  locale: initialLocale(),
  setTheme: (theme) => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    applyTheme(theme);
    set({ theme });
  },
  setLocale: (locale) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    void i18n.changeLanguage(locale);
    applyLocale(locale);
    set({ locale });
  },
}));
