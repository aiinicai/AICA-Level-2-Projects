import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import EmptyState from '../common/EmptyState';

const PALETTE = ['#4C8577', '#B5654A', '#9AA1AC', '#2B3038', '#6B7280', '#DCD7CB'];

/** `series`: [{ key, label, data: [{period, value}] }] — stacked per period. */
export default function StackedBreakupChart({ periods, series, valueFormatter = (v) => v, height = 320, emptyMessage }) {
  const anySeries = series.some((s) => s.data.some((d) => d.value != null));
  if (!periods?.length || !anySeries) {
    return <EmptyState message={emptyMessage || 'Data not available for this chart.'} />;
  }

  const merged = periods.map((period) => {
    const row = { period };
    for (const s of series) {
      const point = s.data.find((d) => d.period === period);
      row[s.key] = point && point.value != null ? point.value : 0;
    }
    return row;
  });

  return (
    <div style={{ height }} className="font-mono-figures text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={merged} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#DCD7CB" vertical={false} />
          <XAxis dataKey="period" stroke="#6B7280" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }} />
          <YAxis stroke="#6B7280" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }} tickFormatter={valueFormatter} width={64} />
          <Tooltip
            formatter={(value) => valueFormatter(value)}
            contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 12, borderRadius: 8, border: '1px solid #DCD7CB' }}
          />
          <Legend wrapperStyle={{ fontFamily: 'Inter', fontSize: 12 }} />
          {series.map((s, i) => (
            <Bar key={s.key} dataKey={s.key} name={s.label} stackId="a" fill={PALETTE[i % PALETTE.length]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
