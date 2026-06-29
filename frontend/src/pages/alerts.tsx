import { useTranslation } from 'react-i18next';

import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useAcknowledgeAlert, useAlerts } from '@/hooks/queries';
import { formatDateTime, formatValue } from '@/lib/format';
import { useSettings } from '@/stores/settings';
import type { AlertSeverity, BadgeTone } from '@/types/api';

const SEVERITY_TONE: Record<AlertSeverity, BadgeTone> = {
  INFO: 'neutral',
  WARNING: 'warning',
  CRITICAL: 'critical',
  EMERGENCY: 'critical',
};

export default function AlertsPage() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const alerts = useAlerts();
  const acknowledge = useAcknowledgeAlert();

  if (alerts.isLoading) {
    return <LoadingState />;
  }
  if (alerts.isError) {
    return <ErrorState onRetry={() => alerts.refetch()} />;
  }
  const list = alerts.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('nav.alerts')}</h1>
      <Card>
        {list.length === 0 ? (
          <EmptyState message={t('alerts.empty')} />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>{t('alerts.severity')}</TH>
                <TH>{t('alerts.value')}</TH>
                <TH>{t('alerts.time')}</TH>
                <TH>{t('alerts.status')}</TH>
                <TH />
              </TR>
            </THead>
            <TBody>
              {list.map((alert) => (
                <TR key={alert.id}>
                  <TD>
                    <Badge tone={SEVERITY_TONE[alert.severity]}>
                      {t(`severity.${alert.severity}`)}
                    </Badge>
                  </TD>
                  <TD className="tabular-nums">{formatValue(alert.value, locale)}</TD>
                  <TD className="text-fg-muted">{formatDateTime(alert.triggered_at, locale)}</TD>
                  <TD>{t(`alertStatus.${alert.status}`)}</TD>
                  <TD className="text-end">
                    {alert.status === 'ACTIVE' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={acknowledge.isPending}
                        onClick={() => acknowledge.mutate(alert.id)}
                      >
                        {t('alerts.ack')}
                      </Button>
                    )}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}
