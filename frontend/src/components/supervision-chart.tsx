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

import type { ReadingPoint } from '@/types/api';

interface SupervisionChartProps {
  points: ReadingPoint[];
  unit?: string | null;
  threshold?: number | null;
  color?: string;
}

export function SupervisionChart({
  points,
  unit,
  threshold,
  color = '#22D3EE',
}: SupervisionChartProps) {
  const data = [...points]
    .reverse()
    .map((point) => ({ t: new Date(point.recorded_at).getTime(), value: point.value }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={['dataMin', 'dataMax']}
          scale="time"
          tickFormatter={(value) => format(new Date(value), 'HH:mm')}
          stroke="var(--color-fg-muted)"
          fontSize={12}
        />
        <YAxis
          stroke="var(--color-fg-muted)"
          fontSize={12}
          width={44}
          unit={unit ? ` ${unit}` : ''}
        />
        {threshold != null && (
          <ReferenceLine y={threshold} stroke="var(--color-critical)" strokeDasharray="4 4" />
        )}
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
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
