import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import EmptyState from '../common/EmptyState';

const PALETTE = ['#4C8577', '#B5654A', '#9AA1AC', '#2B3038', '#6B7280', '#DCD7CB'];

/** `items`: [{ label, value }] for a single period's composition. */
export default function DonutComposition({ items, valueFormatter = (v) => v, height = 260, emptyMessage }) {
  const data = (items || []).filter((i) => i.value != null && i.value > 0);
  if (data.length === 0) {
    return <EmptyState message={emptyMessage || 'Data not available for this chart.'} />;
  }
  return (
    <div style={{ height }} className="font-mono-figures text-xs">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="label" innerRadius="55%" outerRadius="85%" paddingAngle={2} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => valueFormatter(value)}
            contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 12, borderRadius: 8, border: '1px solid #DCD7CB' }}
          />
          <Legend wrapperStyle={{ fontFamily: 'Inter', fontSize: 11 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
