import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts';
import EmptyState from '../common/EmptyState';

/**
 * `steps`: [{ label, value, isTotal }]
 * Totals (isTotal: true) render as absolute bars from 0. Deltas render as a bridge segment
 * from the running total, colored verdigris (adds) or clay (subtracts).
 */
export default function WaterfallBridge({ steps, valueFormatter = (v) => v, height = 340, emptyMessage }) {
  const hasData = steps && steps.some((s) => s.value != null);
  if (!hasData) {
    return <EmptyState message={emptyMessage || 'Data not available for this chart.'} />;
  }

  let running = 0;
  const bars = steps.map((step) => {
    if (step.value == null) {
      return { label: step.label, base: 0, size: 0, color: '#9AA1AC', displayValue: null, isTotal: step.isTotal };
    }
    if (step.isTotal) {
      running = step.value;
      return { label: step.label, base: 0, size: step.value, color: '#20242B', displayValue: step.value, isTotal: true };
    }
    const start = running;
    running += step.value;
    const base = Math.min(start, running);
    const size = Math.abs(step.value);
    const color = step.value >= 0 ? '#4C8577' : '#B5654A';
    return { label: step.label, base, size, color, displayValue: step.value, isTotal: false };
  });

  return (
    <div style={{ height }} className="font-mono-figures text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={bars} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#DCD7CB" vertical={false} />
          <XAxis dataKey="label" stroke="#6B7280" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={70} />
          <YAxis stroke="#6B7280" tick={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }} tickFormatter={valueFormatter} width={64} />
          <Tooltip
            formatter={(_, __, item) => valueFormatter(item?.payload?.displayValue)}
            contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 12, borderRadius: 8, border: '1px solid #DCD7CB' }}
          />
          <Bar dataKey="base" stackId="wf" fill="transparent" isAnimationActive={false} />
          <Bar dataKey="size" stackId="wf" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {bars.map((b, i) => (
              <Cell key={i} fill={b.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
