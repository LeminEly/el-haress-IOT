import { useTranslation } from 'react-i18next';

import { Card } from '@/components/ui/card';
import { StatusDot } from '@/components/ui/status-dot';
import { formatRelative, formatValue } from '@/lib/format';
import { useSettings } from '@/stores/settings';
import type { SensorStatus } from '@/types/api';

interface SensorCardProps {
  label: string;
  value?: number;
  unit?: string | null;
  recordedAt?: string;
  status: SensorStatus;
}

export function SensorCard({ label, value, unit, recordedAt, status }: SensorCardProps) {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm text-fg-muted">{label}</span>
        <div className="flex items-center gap-1.5">
          <StatusDot status={status} />
          <span className="text-xs text-fg-subtle">{t(`status.${status}`)}</span>
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-1">
        <span className="text-3xl font-semibold tabular-nums">
          {value != null ? formatValue(value, locale) : '--'}
        </span>
        {unit && <span className="text-sm text-fg-muted">{unit}</span>}
      </div>
      <div className="mt-2 text-xs text-fg-subtle">
        {recordedAt ? formatRelative(recordedAt, locale) : t('status.offline')}
      </div>
    </Card>
  );
}
