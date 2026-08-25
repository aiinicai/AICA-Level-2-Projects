import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import EmptyState from '../common/EmptyState';

const COLORS = ['#4C8577', '#B5654A', '#6B7280'];

/**
 * Generic multi-series trend line chart.
 * `series`: [{ key, label, data: [{period, value}], dashed }]
 */
export default function TrendChart({ periods, series, valueFormatter = (v) => v, height = 300, emptyMessage }) {
  const anySeries = series.some((s) => s.data.some((d) => d.value != null));
  if (!periods?.length || !anySeries) {
    return <EmptyState message={emptyMessage || 'Data not available for this chart.'} />;
  }

  const merged = periods.map((period) => {
    const row = { period };
    for (const s of series) {
      const point = s.data.find((d) => d.period === period);
      row[s.key] = point ? point.value : null;
    }
    return row;
  });

  return (
    <div style={{ height }} className="font-mono-figures text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={merged} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#DCD7CB" vertical={false} />
          <XAxis dataKey="period" stroke="#6B7280" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
          <YAxis
            stroke="#6B7280"
            tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }}
            tickFormatter={valueFormatter}
            width={64}
          />
          <Tooltip
            formatter={(value) => valueFormatter(value)}
            contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 12, borderRadius: 8, border: '1px solid #DCD7CB' }}
          />
          {series.length > 1 && <Legend wrapperStyle={{ fontFamily: 'Inter', fontSize: 12 }} />}
          {series.map((s, i) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color || COLORS[i % COLORS.length]}
              strokeWidth={2}
              strokeDasharray={s.dashed ? '5 4' : undefined}
              dot={{ r: 3 }}
              connectNulls
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
