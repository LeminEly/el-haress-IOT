import { useTranslation } from 'react-i18next';

import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Card } from '@/components/ui/card';
import { StatusDot } from '@/components/ui/status-dot';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useAdminOverview } from '@/hooks/queries';
import { formatDateTime } from '@/lib/format';
import { useSettings } from '@/stores/settings';
import type { CompanyHealth } from '@/types/api';

function Kpi({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <Card className="p-4">
      <span className="text-sm text-fg-muted">{label}</span>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      {hint && <span className="text-xs text-fg-subtle">{hint}</span>}
    </Card>
  );
}

function companyStatus(company: CompanyHealth): 'critical' | 'normal' | 'offline' {
  if (company.active_alerts > 0) return 'critical';
  if (company.sensors_online > 0) return 'normal';
  return 'offline';
}

export default function OverviewPage() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const overview = useAdminOverview();

  if (overview.isLoading) {
    return <LoadingState />;
  }
  if (overview.isError) {
    return <ErrorState onRetry={() => overview.refetch()} />;
  }

  const data = overview.data;
  if (!data) {
    return <EmptyState />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('overview.title')}</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi
          label={t('overview.companies')}
          value={data.companies_total}
          hint={`${data.companies_active} ${t('overview.activeLower')}`}
        />
        <Kpi
          label={t('overview.sensorsOnline')}
          value={data.sensors_online}
          hint={`${t('overview.ofTotal')} ${data.sensors_total}`}
        />
        <Kpi label={t('overview.activeAlerts')} value={data.active_alerts} />
        <Kpi
          label={t('overview.suspended')}
          value={data.companies_suspended}
          hint={t('overview.companiesLower')}
        />
      </div>

      <Card className="p-0">
        {data.companies.length === 0 ? (
          <EmptyState message={t('overview.empty')} />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <THead>
                <TR>
                  <TH>{t('overview.company')}</TH>
                  <TH>{t('overview.status')}</TH>
                  <TH className="text-end">{t('overview.sensors')}</TH>
                  <TH className="text-end">{t('overview.alerts')}</TH>
                  <TH>{t('overview.lastActivity')}</TH>
                </TR>
              </THead>
              <TBody>
                {data.companies.map((company) => (
                  <TR key={company.account_id}>
                    <TD>
                      <div className="flex items-center gap-2">
                        <StatusDot status={companyStatus(company)} />
                        <div className="flex flex-col">
                          <span className="font-medium text-fg">{company.company_name}</span>
                          <span dir="ltr" className="font-mono text-xs text-fg-subtle">
                            {company.phone_number}
                          </span>
                        </div>
                      </div>
                    </TD>
                    <TD>
                      <span
                        className={
                          company.status === 'ACTIVE'
                            ? 'text-xs font-medium text-normal'
                            : 'text-xs font-medium text-critical'
                        }
                      >
                        {t(`accountStatus.${company.status}`)}
                      </span>
                    </TD>
                    <TD className="text-end tabular-nums">
                      <span className={company.sensors_online > 0 ? 'text-fg' : 'text-fg-subtle'}>
                        {company.sensors_online}
                      </span>
                      <span className="text-fg-subtle"> / {company.sensors_total}</span>
                    </TD>
                    <TD className="text-end tabular-nums">
                      <span
                        className={company.active_alerts > 0 ? 'text-critical' : 'text-fg-subtle'}
                      >
                        {company.active_alerts}
                      </span>
                    </TD>
                    <TD className="whitespace-nowrap text-xs text-fg-muted">
                      {company.last_activity_at
                        ? formatDateTime(company.last_activity_at, locale)
                        : t('overview.noActivity')}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
