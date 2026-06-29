import type { FormEvent } from 'react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { LanguageSwitch } from '@/components/language-switch';
import { Logo } from '@/components/logo';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useLogin } from '@/hooks/use-auth';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useLogin();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ phone_number: phone, password }, { onSuccess: () => navigate('/') });
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center p-4">
      <div className="absolute end-4 top-4 flex gap-2">
        <LanguageSwitch />
        <ThemeToggle />
      </div>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border bg-elevated/80 p-6 shadow-lg backdrop-blur-md"
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <Logo markClassName="size-9" />
          <p className="text-sm text-fg-muted">{t('auth.subtitle')}</p>
        </div>

        <div className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="phone">{t('auth.phone')}</Label>
            <Input
              id="phone"
              type="tel"
              dir="ltr"
              autoComplete="username"
              placeholder="+222..."
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">{t('auth.password')}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          {login.isError && <p className="text-sm text-critical">{t('auth.error')}</p>}
          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? t('auth.submitting') : t('auth.submit')}
          </Button>
        </div>
      </form>
    </div>
  );
}
