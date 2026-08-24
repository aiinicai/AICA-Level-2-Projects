import TrendChart from './TrendChart';

// Ratios/percentages/days trends share the exact same multi-line-over-periods shape as
// TrendChart — this wrapper just exists so page components can express intent clearly.
export default function RatioTrendChart(props) {
  return <TrendChart {...props} />;
}
