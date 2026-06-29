import { subDays, subHours } from 'date-fns';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { SupervisionChart } from '@/components/supervision-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectItem } from '@/components/ui/select';
import { useReadings, useSensors } from '@/hooks/queries';

const RANGES = [
  { key: '1h', hours: 1 },
  { key: '6h', hours: 6 },
  { key: '24h', hours: 24 },
  { key: '7d', hours: 24 * 7 },
  { key: '30d', hours: 24 * 30 },
] as const;

export default function HistoryPage() {
  const { t } = useTranslation();
  const sensors = useSensors();
  const sensorList = sensors.data ?? [];
  const [selected, setSelected] = useState<string | undefined>(undefined);
  const [rangeKey, setRangeKey] = useState<(typeof RANGES)[number]['key']>('24h');

  const selectedId = selected ?? sensorList[0]?.id;
  const start = useMemo(() => {
    const hours = RANGES.find((range) => range.key === rangeKey)?.hours ?? 24;
    const from = hours >= 24 ? subDays(new Date(), hours / 24) : subHours(new Date(), hours);
    return from.toISOString();
  }, [rangeKey]);

  const readings = useReadings(selectedId ? { sensor_id: selectedId, start, limit: 5000 } : {});
  const selectedSensor = sensorList.find((sensor) => sensor.id === selectedId);

  if (sensors.isLoading) {
    return <LoadingState />;
  }
  if (sensors.isError) {
    return <ErrorState onRetry={() => sensors.refetch()} />;
  }
  if (sensorList.length === 0) {
    return <EmptyState message={t('dashboard.noSensors')} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('nav.history')}</h1>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>{t('dashboard.evolution')}</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="w-44"
              aria-label={t('settings.sensor')}
              value={selectedId}
              onValueChange={setSelected}
            >
              {sensorList.map((sensor) => (
                <SelectItem key={sensor.id} value={sensor.id}>
                  {sensor.label}
                </SelectItem>
              ))}
            </Select>
            <Select
              className="w-28"
              value={rangeKey}
              onValueChange={(value) => setRangeKey(value as typeof rangeKey)}
            >
              {RANGES.map((range) => (
                <SelectItem key={range.key} value={range.key}>
                  {t(`history.range.${range.key}`)}
                </SelectItem>
              ))}
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {readings.isLoading ? (
            <LoadingState />
          ) : readings.data && readings.data.length > 0 ? (
            <SupervisionChart points={readings.data} unit={selectedSensor?.unit} />
          ) : (
            <EmptyState message={t('dashboard.noData')} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
