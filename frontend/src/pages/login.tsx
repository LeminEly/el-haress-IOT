import { ArrowLeft } from 'lucide-react';
import type { FormEvent } from 'react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

import { LanguageSwitch } from '@/components/language-switch';
import { LogoMark } from '@/components/logo';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button, buttonVariants } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import { useLogin } from '@/hooks/use-auth';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useLogin();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate({ phone_number: phone, password }, { onSuccess: () => navigate('/app') });
  };

  return (
    <div className="relative flex min-h-dvh items-center justify-center p-4">
      <div className="absolute start-4 top-4 z-10 flex gap-2">
        <Link
          to="/"
          className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'gap-1')}
          aria-label={t('auth.backToHome')}
        >
          <ArrowLeft className="size-4" />
          <span className="hidden sm:inline">{t('auth.backToHome')}</span>
        </Link>
      </div>
      <div className="absolute end-4 top-4 z-10 flex gap-2">
        <LanguageSwitch />
        <ThemeToggle />
      </div>
      <div className="flex w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-elevated/80 shadow-lg backdrop-blur-md md:flex-row">
        <div className="flex flex-col items-center justify-center gap-3 bg-surface p-8 md:w-5/12 md:p-10">
          <LogoMark className="size-28 text-fg md:size-36" />
        </div>
        <form
          onSubmit={handleSubmit}
          className="flex flex-1 flex-col justify-center gap-6 p-8 md:p-10"
        >
          <p className="text-balance text-sm text-fg-muted">{t('auth.subtitle')}</p>
          <div className="flex flex-col gap-4">
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
          <p className="text-center text-xs text-fg-subtle">{t('app.name')}</p>
        </form>
      </div>
    </div>
  );
}
