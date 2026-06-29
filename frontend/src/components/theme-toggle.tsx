import { Moon, Sun } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { resolveIsDark, useSettings } from '@/stores/settings';

export function ThemeToggle() {
  const { t } = useTranslation();
  const theme = useSettings((state) => state.theme);
  const setTheme = useSettings((state) => state.setTheme);
  const isDark = resolveIsDark(theme);

  return (
    <Button
      variant="outline"
      size="sm"
      aria-label={t('theme.toggle')}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      className="px-2"
    >
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
