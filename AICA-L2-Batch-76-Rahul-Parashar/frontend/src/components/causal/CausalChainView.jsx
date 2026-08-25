import { useEffect, useMemo, useState } from 'react';
import { ReactFlow, Background, Controls } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useFinancials } from '../../context/FinancialsContext';
import { getPeriods } from '../../lib/selectors';
import { explainVariance, isExplainable } from '../../lib/varianceEngine';
import { formatINR } from '../../lib/formatters';
import { radialLayout } from './causalLayout';
import EmptyState from '../common/EmptyState';
import { useLocation } from 'react-router-dom';

const DIRECTION_COLOR = {
  positive: { bg: '#E4EEEC', border: '#4C8577', text: '#20242B' },
  negative: { bg: '#F3E6DF', border: '#B5654A', text: '#20242B' },
  neutral: { bg: '#EDE8DD', border: '#9AA1AC', text: '#20242B' },
};

export default function CausalChainView({ metricKey }) {
  const { financials, displayUnit } = useFinancials();
  const location = useLocation();
  const periods = getPeriods(financials, 'annual');
  const periodB = periods[periods.length - 1];
  const periodA = periods[periods.length - 2];

  const [aiSentence, setAiSentence] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const result = useMemo(() => {
    if (!metricKey || !isExplainable(metricKey) || !periodA || !periodB) return null;
    return explainVariance(financials, metricKey, periodA, periodB);
  }, [financials, metricKey, periodA, periodB]);

  useEffect(() => {
    if (!result) return;
    let cancelled = false;
    setAiLoading(true);
    setAiSentence(null);
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: `In one plain-English sentence, explain why ${result.metricLabel} changed from ${periodA} to ${periodB} using only the node values shown: ${result.nodes.map((n) => `${n.label} ${n.value >= 0 ? '+' : ''}${n.value.toFixed(1)}`).join(', ')}. Total change: ${result.centerDelta?.toFixed(1)}.`,
        history: [],
        currentPage: location.pathname,
        financials,
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        setAiSentence(data.reply || null);
      })
      .catch(() => {
        if (!cancelled) setAiSentence(null);
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [result?.metric, periodA, periodB]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!result || result.nodes.length === 0) {
    return <EmptyState message="Not enough data to explain this metric's change." />;
  }

  const positions = radialLayout(result.nodes.length);
  const flowNodes = [
    {
      id: 'center',
      position: { x: 400 - 100, y: 260 - 30 },
      data: {
        label: (
          <div className="text-center">
            <div className="font-heading text-xs font-medium">{result.metricLabel}</div>
            <div className="font-mono-figures text-sm mt-0.5">
              {result.centerDelta >= 0 ? '+' : ''}
              {formatINR(result.centerDelta, { unit: displayUnit })}
            </div>
            <div className="text-[10px] text-slate">
              {periodA} → {periodB}
            </div>
          </div>
        ),
      },
      style: { background: '#20242B', color: '#EDE8DD', border: '2px solid #4C8577', borderRadius: 10, width: 200, padding: 8 },
    },
    ...result.nodes.map((n, i) => {
      const color = DIRECTION_COLOR[n.direction];
      return {
        id: n.id,
        position: positions[i],
        data: {
          label: (
            <div className="text-center">
              <div className="font-heading text-[11px] font-medium">{n.label}</div>
              <div className="font-mono-figures text-xs mt-0.5">
                {n.value >= 0 ? '+' : ''}
                {formatINR(n.value, { unit: displayUnit })}
              </div>
            </div>
          ),
        },
        style: { background: color.bg, color: color.text, border: `1.5px solid ${color.border}`, borderRadius: 8, width: 180, padding: 6 },
      };
    }),
  ];

  const flowEdges = result.nodes.map((n) => {
    const color = DIRECTION_COLOR[n.direction].border;
    return {
      id: `e-${n.id}`,
      source: n.id,
      target: 'center',
      label: `${n.value >= 0 ? '+' : ''}${formatINR(n.value, { unit: displayUnit })}`,
      style: { stroke: color },
      labelStyle: { fontFamily: 'IBM Plex Mono', fontSize: 10, fill: '#20242B' },
      animated: false,
    };
  });

  return (
    <div className="bg-paper rounded-lg border border-line p-4">
      <div className="mb-3 min-h-[1.25rem] text-sm font-body text-ink">
        {aiLoading && <span className="text-slate">Generating plain-English explanation…</span>}
        {!aiLoading && aiSentence && <span>{aiSentence}</span>}
        {!aiLoading && !aiSentence && (
          <span className="text-slate">
            {result.metricLabel} moved {result.centerDelta >= 0 ? 'up' : 'down'} by{' '}
            {formatINR(Math.abs(result.centerDelta), { unit: displayUnit })} between {periodA} and {periodB}.
          </span>
        )}
      </div>
      <div style={{ height: 480 }}>
        <ReactFlow nodes={flowNodes} edges={flowEdges} fitView proOptions={{ hideAttribution: true }} nodesDraggable={false} nodesConnectable={false}>
          <Background color="#DCD7CB" gap={20} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}
