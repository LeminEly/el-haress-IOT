import { format } from 'date-fns';
import { subDays, subHours } from 'date-fns';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { MultiSensorChart } from '@/components/multi-sensor-chart';
import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectItem } from '@/components/ui/select';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useReadings, useSensors } from '@/hooks/queries';
import { formatValue } from '@/lib/format';
import { useSettings } from '@/stores/settings';

const RANGES = [
  { key: '1h', hours: 1 },
  { key: '6h', hours: 6 },
  { key: '24h', hours: 24 },
  { key: '7d', hours: 24 * 7 },
  { key: '30d', hours: 24 * 30 },
] as const;

function stats(values: number[]) {
  if (values.length === 0) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  return { min, max, avg };
}

export default function HistoryPage() {
  const { t } = useTranslation();
  const locale = useSettings((state) => state.locale);
  const sensors = useSensors();
  const sensorList = useMemo(() => sensors.data ?? [], [sensors.data]);
  const [selected, setSelected] = useState<string[]>([]);
  const [rangeKey, setRangeKey] = useState<(typeof RANGES)[number]['key']>('24h');

  const start = useMemo(() => {
    const hours = RANGES.find((range) => range.key === rangeKey)?.hours ?? 24;
    const from = hours >= 24 ? subDays(new Date(), hours / 24) : subHours(new Date(), hours);
    return from.toISOString();
  }, [rangeKey]);

  const readings = useReadings({ start, limit: 5000 }, { refetchInterval: 10_000 });

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : [...current, id],
    );

  const visibleIds = selected.length > 0 ? selected : sensorList.map((s) => s.id);

  const visibleSensors = sensorList.filter((s) => visibleIds.includes(s.id));

  const thresholds = useMemo(() => {
    const map: Record<string, number | null> = {};
    for (const sensor of sensorList) {
      map[sensor.id] = sensor.critical_threshold;
    }
    return map;
  }, [sensorList]);

  const filteredReadings = useMemo(
    () => readings.data?.filter((r) => visibleIds.includes(r.sensor_id)) ?? [],
    [readings.data, visibleIds],
  );

  const statsBySensor = useMemo(() => {
    const grouped: Record<string, number[]> = {};
    for (const r of filteredReadings) {
      (grouped[r.sensor_id] ??= []).push(r.value);
    }
    const result: Record<string, { min: number; max: number; avg: number } | null> = {};
    for (const [id, values] of Object.entries(grouped)) {
      result[id] = stats(values);
    }
    return result;
  }, [filteredReadings]);

  if (sensors.isLoading) {
    return <LoadingState />;
  }
  if (sensors.isError) {
    return <ErrorState onRetry={() => sensors.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">{t('nav.history')}</h1>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle>{t('dashboard.evolution')}</CardTitle>
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
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {sensorList.length > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              {sensorList.map((sensor) => (
                <label key={sensor.id} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox
                    checked={visibleIds.includes(sensor.id)}
                    onCheckedChange={() => toggle(sensor.id)}
                  />
                  <span
                    className="h-0.5 w-4 rounded-full"
                    style={{ backgroundColor: sensor.color || 'var(--color-fg)' }}
                  />
                  <span className="text-fg">{sensor.label}</span>
                </label>
              ))}
            </div>
          )}
          {readings.isLoading ? (
            <LoadingState />
          ) : filteredReadings.length > 0 ? (
            <>
              <MultiSensorChart
                sensors={visibleSensors}
                readings={filteredReadings}
                thresholds={thresholds}
                height={320}
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {visibleSensors.map((sensor) => {
                  const s = statsBySensor[sensor.id];
                  if (!s) return null;
                  return (
                    <Card key={sensor.id} className="p-3">
                      <span className="text-xs font-medium text-fg-muted">{sensor.label}</span>
                      <div className="mt-1 grid grid-cols-3 gap-2 text-center text-xs">
                        <div>
                          <div className="text-fg-subtle">Min</div>
                          <div className="font-medium tabular-nums text-fg">
                            {formatValue(s.min, locale)}
                          </div>
                        </div>
                        <div>
                          <div className="text-fg-subtle">Moy</div>
                          <div className="font-medium tabular-nums text-fg">
                            {formatValue(s.avg, locale)}
                          </div>
                        </div>
                        <div>
                          <div className="text-fg-subtle">Max</div>
                          <div className="font-medium tabular-nums text-fg">
                            {formatValue(s.max, locale)}
                          </div>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
              <div className="max-h-72 overflow-y-auto">
                <Table>
                  <THead>
                    <TR>
                      <TH>{t('alerts.time')}</TH>
                      <TH>{t('settings.sensor')}</TH>
                      <TH className="text-end">{t('alerts.value')}</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {[...filteredReadings]
                      .sort(
                        (a, b) =>
                          new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
                      )
                      .slice(0, 200)
                      .map((point, i) => {
                        const sensor = visibleSensors.find((s) => s.id === point.sensor_id);
                        return (
                          <TR key={`${point.sensor_id}-${point.recorded_at}-${i}`}>
                            <TD className="text-xs text-fg-muted" dir="ltr">
                              {format(new Date(point.recorded_at), 'Pp')}
                            </TD>
                            <TD className="text-xs">{sensor?.label ?? point.sensor_id}</TD>
                            <TD className="text-end text-xs tabular-nums">
                              {formatValue(point.value, locale)}
                              {sensor?.unit ? ` ${sensor.unit}` : ''}
                            </TD>
                          </TR>
                        );
                      })}
                  </TBody>
                </Table>
              </div>
            </>
          ) : (
            <EmptyState message={t('dashboard.noData')} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
