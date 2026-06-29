import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { SensorCard } from '@/components/sensor-card';
import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { SupervisionChart } from '@/components/supervision-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { StatusDot } from '@/components/ui/status-dot';
import { useDashboardSummary, useReadings, useSensors } from '@/hooks/queries';
import { useLiveReadings } from '@/hooks/use-live';
import type { SensorStatus } from '@/types/api';

const STALE_MS = 120_000;

interface LiveEntry {
  value: number;
  recorded_at: string;
}

function sensorStatus(entry: LiveEntry | undefined, isActive: boolean): SensorStatus {
  if (!isActive || !entry) {
    return 'offline';
  }
  return Date.now() - new Date(entry.recorded_at).getTime() > STALE_MS ? 'offline' : 'normal';
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const summary = useDashboardSummary();
  const sensors = useSensors();
  const [live, setLive] = useState<Record<string, LiveEntry>>({});
  const [selected, setSelected] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!summary.data) {
      return;
    }
    const seed: Record<string, LiveEntry> = {};
    for (const reading of summary.data.latest) {
      seed[reading.sensor_id] = { value: reading.value, recorded_at: reading.recorded_at };
    }
    setLive((previous) => ({ ...seed, ...previous }));
  }, [summary.data]);

  const { connected } = useLiveReadings((reading) =>
    setLive((previous) => ({
      ...previous,
      [reading.sensor_id]: { value: reading.value, recorded_at: reading.recorded_at },
    })),
  );

  const sensorList = sensors.data ?? [];
  const selectedId = selected ?? sensorList[0]?.id;
  const readings = useReadings(selectedId ? { sensor_id: selectedId, limit: 200 } : {});
  const selectedSensor = sensorList.find((sensor) => sensor.id === selectedId);

  if (sensors.isLoading || summary.isLoading) {
    return <LoadingState />;
  }
  if (sensors.isError) {
    return <ErrorState onRetry={() => sensors.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">{t('nav.dashboard')}</h1>
        <div className="flex items-center gap-1.5 text-xs text-fg-muted">
          <StatusDot status={connected ? 'normal' : 'offline'} />
          {connected ? t('dashboard.live') : t('dashboard.offline')}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="p-4">
          <span className="text-sm text-fg-muted">{t('dashboard.sensorsTotal')}</span>
          <p className="mt-2 text-3xl font-semibold tabular-nums">
            {summary.data?.sensors_total ?? 0}
          </p>
        </Card>
        <Card className="p-4">
          <span className="text-sm text-fg-muted">{t('dashboard.sensorsActive')}</span>
          <p className="mt-2 text-3xl font-semibold tabular-nums">
            {summary.data?.sensors_active ?? 0}
          </p>
        </Card>
      </div>

      {sensorList.length === 0 ? (
        <EmptyState message={t('dashboard.noSensors')} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {sensorList.map((sensor) => {
              const entry = live[sensor.id];
              return (
                <SensorCard
                  key={sensor.id}
                  label={sensor.label}
                  value={entry?.value}
                  unit={sensor.unit}
                  recordedAt={entry?.recorded_at}
                  status={sensorStatus(entry, sensor.is_active)}
                />
              );
            })}
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>{t('dashboard.evolution')}</CardTitle>
              <Select
                className="w-48"
                value={selectedId}
                onChange={(event) => setSelected(event.target.value)}
              >
                {sensorList.map((sensor) => (
                  <option key={sensor.id} value={sensor.id}>
                    {sensor.label}
                  </option>
                ))}
              </Select>
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
        </>
      )}
    </div>
  );
}
