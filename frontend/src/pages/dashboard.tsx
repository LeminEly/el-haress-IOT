import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { MultiSensorChart } from '@/components/multi-sensor-chart';
import { SensorCard } from '@/components/sensor-card';
import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { SupervisionChart } from '@/components/supervision-chart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { StatusDot } from '@/components/ui/status-dot';
import { useDashboardSummary, useReadings, useSensors } from '@/hooks/queries';
import { useLiveReadings } from '@/hooks/use-live';
import { formatValue } from '@/lib/format';
import { formatSensorValue, isDetected, sensorName } from '@/lib/sensor-display';
import { useSettings } from '@/stores/settings';
import type { ReadingPoint, Sensor, SensorStatus } from '@/types/api';

// Fenetre de fraicheur par defaut si le resume n'est pas encore charge (secondes).
const DEFAULT_OFFLINE_AFTER_SECONDS = 10;

interface LiveEntry {
  value: number;
  recorded_at: string;
}

// Connectivite reelle : capteur actif dont la derniere mesure tient dans la
// fenetre de fraicheur. Un capteur muet sort tout seul (reevalue par le tick).
function isOnline(entry: LiveEntry | undefined, sensor: Sensor, windowMs: number): boolean {
  return (
    sensor.is_active &&
    entry !== undefined &&
    Date.now() - new Date(entry.recorded_at).getTime() <= windowMs
  );
}

function sensorStatus(entry: LiveEntry | undefined, sensor: Sensor): SensorStatus {
  if (!entry) {
    return 'normal';
  }
  if (sensor.is_binary) {
    return isDetected(entry.value) ? 'critical' : 'normal';
  }
  if (sensor.critical_threshold != null && entry.value > sensor.critical_threshold) {
    return 'critical';
  }
  return 'normal';
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const sensors = useSensors();
  const summary = useDashboardSummary();
  const allReadings = useReadings({ limit: 1000 });

  const [live, setLive] = useState<Record<string, LiveEntry>>({});
  const [points, setPoints] = useState<ReadingPoint[]>([]);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [detailId, setDetailId] = useState<string | null>(null);

  useEffect(() => {
    if (summary.data) {
      const seed: Record<string, LiveEntry> = {};
      for (const reading of summary.data.latest) {
        seed[reading.sensor_id] = { value: reading.value, recorded_at: reading.recorded_at };
      }
      setLive((previous) => ({ ...seed, ...previous }));
    }
  }, [summary.data]);

  useEffect(() => {
    if (allReadings.data) {
      setPoints(allReadings.data);
    }
  }, [allReadings.data]);

  const { connected } = useLiveReadings((reading) => {
    setLive((previous) => ({
      ...previous,
      [reading.sensor_id]: { value: reading.value, recorded_at: reading.recorded_at },
    }));
    setPoints((previous) => [reading as ReadingPoint, ...previous].slice(0, 3000));
  });

  // Reevalue la connectivite a intervalle regulier : un capteur qui cesse
  // d'emettre (donc sans evenement live) doit disparaitre de lui-meme.
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const sensorList = useMemo(() => sensors.data ?? [], [sensors.data]);
  const thresholds = useMemo(() => {
    const map: Record<string, number | null> = {};
    for (const sensor of sensorList) {
      map[sensor.id] = sensor.critical_threshold;
    }
    return map;
  }, [sensorList]);

  if (sensors.isLoading || summary.isLoading) {
    return <LoadingState />;
  }
  if (sensors.isError) {
    return <ErrorState onRetry={() => sensors.refetch()} />;
  }

  // Capteurs reellement connectes : seuls eux sont affiches sur le tableau de
  // bord. Les capteurs hors-ligne restent consultables dans l'historique.
  const offlineAfterMs =
    (summary.data?.offline_after_seconds ?? DEFAULT_OFFLINE_AFTER_SECONDS) * 1000;
  const onlineSensors = sensorList.filter((sensor) =>
    isOnline(live[sensor.id], sensor, offlineAfterMs),
  );
  // Le graphe lineaire ne represente que les capteurs continus : un capteur
  // binaire (0/1) ecraserait l'axe Y et serait illisible. Il reste visible via
  // sa carte (Detecte / Normal).
  const chartSensors = onlineSensors.filter((sensor) => !sensor.is_binary);
  const visibleSensors = chartSensors.filter((sensor) => !hidden.has(sensor.id));
  const detailSensor = sensorList.find((sensor) => sensor.id === detailId);
  const detailPoints = detailSensor
    ? points.filter((point) => point.sensor_id === detailSensor.id)
    : [];

  const toggle = (id: string) =>
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">{t('nav.dashboard')}</h1>
        <div className="flex items-center gap-1.5 text-xs text-fg-muted">
          <StatusDot status={connected ? 'normal' : 'offline'} />
          {connected ? t('dashboard.live') : t('dashboard.offline')}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:max-w-md">
        <Card className="p-4">
          <span className="text-sm text-fg-muted">{t('dashboard.sensorsTotal')}</span>
          <p className="mt-1 text-3xl font-semibold tabular-nums">{sensorList.length}</p>
        </Card>
        <Card className="p-4">
          <span className="text-sm text-fg-muted">{t('dashboard.sensorsActive')}</span>
          <p className="mt-1 text-3xl font-semibold tabular-nums">{onlineSensors.length}</p>
        </Card>
      </div>

      {sensorList.length === 0 ? (
        <EmptyState message={t('dashboard.noSensors')} />
      ) : onlineSensors.length === 0 ? (
        <EmptyState message={t('dashboard.noConnected')} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {onlineSensors.map((sensor) => {
              const entry = live[sensor.id];
              return (
                <SensorCard
                  key={sensor.id}
                  label={sensorName(sensor)}
                  value={entry?.value}
                  unit={sensor.unit}
                  isBinary={sensor.is_binary}
                  recordedAt={entry?.recorded_at}
                  status={sensorStatus(entry, sensor)}
                  onClick={() => setDetailId(sensor.id)}
                />
              );
            })}
          </div>

          {chartSensors.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t('dashboard.evolution')}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {/* Legende : capteurs continus connectes ; cocher pour afficher la courbe. */}
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  {chartSensors.map((sensor) => {
                    const entry = live[sensor.id];
                    return (
                      <label
                        key={sensor.id}
                        className="flex cursor-pointer items-center gap-2 text-sm"
                      >
                        <Checkbox
                          checked={!hidden.has(sensor.id)}
                          onCheckedChange={() => toggle(sensor.id)}
                        />
                        <span
                          className="h-0.5 w-4 rounded-full"
                          style={{ backgroundColor: sensor.color || 'var(--color-fg)' }}
                        />
                        <span className="text-fg">{sensorName(sensor)}</span>
                        {entry && (
                          <span className="tabular-nums text-fg-muted">
                            {formatSensorValue(sensor, entry.value, locale, t)}
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>

                {points.length > 0 && visibleSensors.length > 0 ? (
                  <MultiSensorChart
                    sensors={visibleSensors}
                    readings={points}
                    thresholds={thresholds}
                  />
                ) : (
                  <EmptyState message={t('dashboard.noData')} />
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Dialog open={detailId !== null} onOpenChange={(open) => !open && setDetailId(null)}>
        {detailSensor && (
          <DialogContent>
            <DialogTitle>{sensorName(detailSensor)}</DialogTitle>
            <div className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-sm text-fg-muted">
              <span>
                {t('dashboard.current')} :{' '}
                <span className="font-medium text-fg">
                  {formatSensorValue(detailSensor, live[detailSensor.id]?.value, locale, t)}
                </span>
              </span>
              <span>
                {t('dashboard.threshold')} :{' '}
                <span className="font-medium text-fg">
                  {thresholds[detailSensor.id] != null
                    ? formatValue(thresholds[detailSensor.id] as number, locale)
                    : t('dashboard.noThreshold')}
                </span>
              </span>
            </div>
            <div className="mt-4">
              {detailPoints.length > 0 ? (
                <SupervisionChart
                  points={detailPoints}
                  unit={detailSensor.unit}
                  threshold={thresholds[detailSensor.id]}
                />
              ) : (
                <EmptyState message={t('dashboard.noData')} />
              )}
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
