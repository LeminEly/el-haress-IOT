import { AlertTriangle, Inbox } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';

export function LoadingState() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center gap-2 p-8 text-sm text-fg-muted">
      <Spinner />
      {t('state.loading')}
    </div>
  );
}

export function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 p-8 text-center">
      <AlertTriangle className="size-6 text-critical" aria-hidden="true" />
      <p className="text-sm text-fg-muted">{t('state.error')}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {t('state.retry')}
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message?: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center text-fg-muted">
      <Inbox className="size-6" aria-hidden="true" />
      <p className="text-sm">{message ?? t('state.empty')}</p>
    </div>
  );
}
