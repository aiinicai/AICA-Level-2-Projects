import { LineChart, Line, ResponsiveContainer } from 'recharts';

export default function Sparkline({ data, dataKey = 'value', color = '#4C8577' }) {
  const hasAny = data.some((d) => d[dataKey] != null);
  if (!hasAny) return <div className="h-10" />;
  return (
    <div className="h-10 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
