import { useTranslation } from 'react-i18next';

import { StatusDot } from '@/components/ui/status-dot';
import { cn } from '@/lib/utils';
import { formatRelative, formatValue } from '@/lib/format';
import { useSettings } from '@/stores/settings';
import type { SensorStatus } from '@/types/api';

interface SensorCardProps {
  label: string;
  value?: number;
  unit?: string | null;
  isBinary?: boolean;
  recordedAt?: string;
  status: SensorStatus;
  onClick?: () => void;
}

export function SensorCard({
  label,
  value,
  unit,
  isBinary = false,
  recordedAt,
  status,
  onClick,
}: SensorCardProps) {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);

  const binaryLabel = value != null ? t(value > 0.5 ? 'sensor.detected' : 'sensor.normal') : '--';

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col rounded-lg border border-border bg-elevated p-4 text-start transition-colors',
        'hover:border-fg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm text-fg-muted">{label}</span>
        <div className="flex items-center gap-1.5">
          <StatusDot status={status} />
          <span className="text-xs text-fg-subtle">{t(`status.${status}`)}</span>
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-1">
        {isBinary ? (
          <span className="text-2xl font-semibold">{binaryLabel}</span>
        ) : (
          <>
            <span className="text-3xl font-semibold tabular-nums">
              {value != null ? formatValue(value, locale) : '--'}
            </span>
            {unit && <span className="text-sm text-fg-muted">{unit}</span>}
          </>
        )}
      </div>
      <div className="mt-2 text-xs text-fg-subtle">
        {recordedAt ? formatRelative(recordedAt, locale) : t('status.offline')}
      </div>
    </button>
  );
}
