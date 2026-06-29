import { format } from 'date-fns';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { ReadingPoint, Sensor } from '@/types/api';

const SERIES_FALLBACK = ['var(--color-fg)', '#a1a1aa', '#52525b', '#71717a', '#d4d4d8'];
const SERIES_DASH = ['0', '5 3', '2 2', '8 3', '4 4'];

interface MultiSensorChartProps {
  sensors: Sensor[];
  readings: ReadingPoint[];
  thresholds: Record<string, number | null | undefined>;
  height?: number;
}

export function MultiSensorChart({
  sensors,
  readings,
  thresholds,
  height = 300,
}: MultiSensorChartProps) {
  const byTime = new Map<number, Record<string, number>>();
  for (const reading of readings) {
    const t = new Date(reading.recorded_at).getTime();
    const row = byTime.get(t) ?? {};
    row[reading.sensor_id] = reading.value;
    byTime.set(t, row);
  }
  const data = [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([t, values]) => ({ t, ...values }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={['dataMin', 'dataMax']}
          scale="time"
          tickFormatter={(value) => format(new Date(value), 'HH:mm')}
          stroke="var(--color-fg-subtle)"
          fontSize={11}
        />
        <YAxis stroke="var(--color-fg-subtle)" fontSize={11} width={44} />
        <Tooltip
          contentStyle={{
            background: 'var(--color-elevated)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            color: 'var(--color-fg)',
            fontSize: 12,
          }}
          labelFormatter={(value) => format(new Date(Number(value)), 'Pp')}
        />
        {sensors.map((sensor, index) => (
          <Line
            key={sensor.id}
            type="monotone"
            dataKey={sensor.id}
            name={sensor.label}
            stroke={sensor.color || SERIES_FALLBACK[index % SERIES_FALLBACK.length]}
            strokeWidth={2}
            strokeDasharray={SERIES_DASH[index % SERIES_DASH.length]}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        ))}
        {sensors.map((sensor) =>
          thresholds[sensor.id] != null ? (
            <ReferenceLine
              key={`threshold-${sensor.id}`}
              y={thresholds[sensor.id] as number}
              stroke="var(--color-critical)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
          ) : null,
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}
