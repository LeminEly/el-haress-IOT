import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

import arCommon from './ar/common.json';
import enCommon from './en/common.json';
import frCommon from './fr/common.json';

export const SUPPORTED_LOCALES = ['fr', 'ar', 'en'] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const RTL_LOCALES: readonly Locale[] = ['ar'];

const LOCALE_STORAGE_KEY = 'el-haress-locale';

export const resources = {
  fr: { common: frCommon },
  ar: { common: arCommon },
  en: { common: enCommon },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'fr',
    supportedLngs: SUPPORTED_LOCALES,
    defaultNS: 'common',
    ns: ['common'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LOCALE_STORAGE_KEY,
      caches: [],
    },
  });

export default i18n;
