import { format } from 'date-fns';
import { subDays, subHours } from 'date-fns';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { MultiSensorChart } from '@/components/multi-sensor-chart';
import { EmptyState, ErrorState, LoadingState } from '@/components/states';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectItem } from '@/components/ui/select';
import { TBody, TD, TH, THead, TR, Table } from '@/components/ui/table';
import { useReadings, useSensors } from '@/hooks/queries';
import { formatValue } from '@/lib/format';
import { categorizeSensor, CATEGORIES } from '@/lib/sensor-categories';
import { useSettings } from '@/stores/settings';

const RANGES = [
  { key: '1h', hours: 1 },
  { key: '6h', hours: 6 },
  { key: '24h', hours: 24 },
  { key: '7d', hours: 24 * 7 },
  { key: '30d', hours: 24 * 30 },
  { key: 'custom', hours: 0 },
] as const;

const PAGE_SIZES = [50, 100, 200, 500] as const;

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
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<number>(200);

  const { start, end } = useMemo(() => {
    const now = new Date();
    if (rangeKey === 'custom') {
      return {
        start: customStart ? new Date(customStart).toISOString() : subHours(now, 1).toISOString(),
        end: customEnd ? new Date(customEnd).toISOString() : now.toISOString(),
      };
    }
    const hours = RANGES.find((r) => r.key === rangeKey)?.hours ?? 24;
    const from = hours >= 24 ? subDays(now, hours / 24) : subHours(now, hours);
    return { start: from.toISOString(), end: now.toISOString() };
  }, [rangeKey, customStart, customEnd]);

  const selectedCategorySensors = useMemo(() => {
    if (categoryFilter === 'all') return sensorList;
    return sensorList.filter((s) => categorizeSensor(s) === categoryFilter);
  }, [sensorList, categoryFilter]);

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : [...current, id],
    );

  const selectCategory = () => {
    const ids = selectedCategorySensors.map((s) => s.id);
    const allSelected = ids.every((id) => selected.includes(id));
    if (allSelected) {
      setSelected((current) => current.filter((id) => !ids.includes(id)));
    } else {
      setSelected((current) => {
        const next = new Set(current);
        for (const id of ids) next.add(id);
        return [...next];
      });
    }
  };

  const visibleIds = selected.length > 0 ? selected : selectedCategorySensors.map((s) => s.id);
  const visibleSensors = sensorList.filter((s) => visibleIds.includes(s.id));

  const readings = useReadings({ start, end, limit: 5000 }, { refetchInterval: 10_000 });

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

  const sorted = useMemo(
    () =>
      [...filteredReadings].sort(
        (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
      ),
    [filteredReadings],
  );

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages - 1);
  const pageStart = safePage * pageSize;
  const pageData = sorted.slice(pageStart, pageStart + pageSize);

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
          <div className="flex flex-wrap items-center gap-3">
            <Select
              className="w-28"
              value={categoryFilter}
              onValueChange={(value) => {
                setCategoryFilter(value);
                setPage(0);
              }}
            >
              <SelectItem value="all">{t('history.allCategories')}</SelectItem>
              {CATEGORIES.map((cat) => (
                <SelectItem key={cat.id} value={cat.id}>
                  {t(cat.labelKey)}
                </SelectItem>
              ))}
            </Select>
            <Select
              className="w-32"
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
        <CardContent className="flex flex-col gap-4">
          {rangeKey === 'custom' && (
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="hist-from" className="text-xs text-fg-muted">
                  {t('history.from')}
                </Label>
                <Input
                  id="hist-from"
                  type="datetime-local"
                  className="w-52"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="hist-to" className="text-xs text-fg-muted">
                  {t('history.to')}
                </Label>
                <Input
                  id="hist-to"
                  type="datetime-local"
                  className="w-52"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </div>
            </div>
          )}

          {selectedCategorySensors.length > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-2">
              <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-fg-muted">
                <Checkbox
                  checked={selectedCategorySensors.every((s) => selected.includes(s.id))}
                  onCheckedChange={selectCategory}
                />
                {t('settings.allSensors')}
              </label>
              {selectedCategorySensors.map((sensor) => (
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
                  {sensor.unit && <span className="text-fg-subtle text-xs">({sensor.unit})</span>}
                </label>
              ))}
            </div>
          )}
          {selectedCategorySensors.length === 0 && (
            <p className="text-sm text-fg-muted">{t('history.noMatchingCategory')}</p>
          )}

          {readings.isLoading ? (
            <LoadingState />
          ) : filteredReadings.length > 0 ? (
            <>
              <MultiSensorChart
                sensors={visibleSensors}
                readings={filteredReadings}
                thresholds={thresholds}
                height={360}
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {visibleSensors.map((sensor) => {
                  const s = statsBySensor[sensor.id];
                  if (!s) return null;
                  return (
                    <Card key={sensor.id} className="p-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 shrink-0 rounded-full"
                          style={{ backgroundColor: sensor.color || 'var(--color-fg)' }}
                        />
                        <span className="text-xs font-medium text-fg-muted">{sensor.label}</span>
                      </div>
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
              <div className="flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-fg-muted">{t('history.rowsPerPage')}</span>
                    <Select
                      className="w-20"
                      value={String(pageSize)}
                      onValueChange={(value) => {
                        setPageSize(Number(value));
                        setPage(0);
                      }}
                    >
                      {PAGE_SIZES.map((s) => (
                        <SelectItem key={s} value={String(s)}>
                          {s}
                        </SelectItem>
                      ))}
                    </Select>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-fg-muted">
                      {t('history.page', { page: safePage + 1, total: totalPages })}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={safePage <= 0}
                      onClick={() => setPage(safePage - 1)}
                    >
                      {t('history.prevPage')}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={safePage >= totalPages - 1}
                      onClick={() => setPage(safePage + 1)}
                    >
                      {t('history.nextPage')}
                    </Button>
                  </div>
                </div>
                <div className="max-h-80 overflow-y-auto rounded-lg border border-border">
                  <Table>
                    <THead>
                      <TR>
                        <TH>{t('alerts.time')}</TH>
                        <TH>{t('settings.sensor')}</TH>
                        <TH className="text-end">{t('alerts.value')}</TH>
                      </TR>
                    </THead>
                    <TBody>
                      {pageData.map((point, i) => {
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
