import React, { useState, useMemo, useRef } from 'react';
import { ChartDataPoint } from '../../types';
import { formatINR, formatDisplayDate, formatPercent } from '../../utils/formatters';

interface PortfolioChartProps {
  data: ChartDataPoint[];
  selectedDate: string;
}

type RangeOption = '1M' | '6M' | '1Y' | '3Y' | '5Y' | 'ALL';

export const PortfolioChart: React.FC<PortfolioChartProps> = ({ data, selectedDate }) => {
  const [range, setRange] = useState<RangeOption>('ALL');
  const [isLog, setIsLog] = useState<boolean>(false);
  const [showMetalLines, setShowMetalLines] = useState<boolean>(true);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // Filter data based on range
  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];
    if (range === 'ALL') return data;

    const lastDate = new Date(selectedDate);
    const monthsBack = range === '1M' ? 1 : range === '6M' ? 6 : range === '1Y' ? 12 : range === '3Y' ? 36 : 60;
    const cutoff = new Date(lastDate);
    cutoff.setMonth(cutoff.getMonth() - monthsBack);
    const cutoffStr = cutoff.toISOString().split('T')[0];

    const sliced = data.filter(d => d.date >= cutoffStr);
    return sliced.length > 0 ? sliced : data;
  }, [data, range, selectedDate]);

  // Compute domain bounds
  const { minVal, maxVal, validPoints } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    const valid: ChartDataPoint[] = [];

    for (const d of filteredData) {
      const vals = [d.investedCost, d.resaleValue];
      if (showMetalLines) {
        if (d.goldResaleValue > 0) vals.push(d.goldResaleValue);
        if (d.silverResaleValue > 0) vals.push(d.silverResaleValue);
      }

      for (const v of vals) {
        if (isLog) {
          if (v > 0) {
            min = Math.min(min, v);
            max = Math.max(max, v);
          }
        } else {
          min = Math.min(min, v);
          max = Math.max(max, v);
        }
      }
      valid.push(d);
    }

    if (!isFinite(min) || min === Infinity) min = 1000;
    if (!isFinite(max) || max === -Infinity) max = 10000;

    if (!isLog) {
      min = Math.max(0, min * 0.95);
    } else {
      min = Math.max(1, min * 0.9);
    }
    max = max * 1.05;

    return { minVal: min, maxVal: max, validPoints: valid };
  }, [filteredData, isLog, showMetalLines]);

  // Dimensions
  const width = 800;
  const height = 360;
  const padLeft = 70;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 40;

  const innerWidth = width - padLeft - padRight;
  const innerHeight = height - padTop - padBottom;

  const getY = (val: number): number => {
    if (isLog) {
      if (val <= 0) return height - padBottom;
      const logMin = Math.log10(minVal);
      const logMax = Math.log10(maxVal);
      const logVal = Math.log10(val);
      const norm = (logVal - logMin) / (logMax - logMin);
      return height - padBottom - norm * innerHeight;
    }
    const norm = (val - minVal) / (maxVal - minVal);
    return height - padBottom - norm * innerHeight;
  };

  const getX = (index: number): number => {
    if (validPoints.length <= 1) return padLeft + innerWidth / 2;
    return padLeft + (index / (validPoints.length - 1)) * innerWidth;
  };

  // Generate SVG path strings
  const investedPath = useMemo(() => {
    if (validPoints.length === 0) return '';
    return validPoints
      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(d.investedCost).toFixed(1)}`)
      .join(' ');
  }, [validPoints, isLog, minVal, maxVal]);

  const resalePath = useMemo(() => {
    if (validPoints.length === 0) return '';
    return validPoints
      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(d.resaleValue).toFixed(1)}`)
      .join(' ');
  }, [validPoints, isLog, minVal, maxVal]);

  const goldPath = useMemo(() => {
    if (!showMetalLines || validPoints.length === 0) return '';
    return validPoints
      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(d.goldResaleValue).toFixed(1)}`)
      .join(' ');
  }, [validPoints, showMetalLines, isLog, minVal, maxVal]);

  const silverPath = useMemo(() => {
    if (!showMetalLines || validPoints.length === 0) return '';
    return validPoints
      .map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(d.silverResaleValue).toFixed(1)}`)
      .join(' ');
  }, [validPoints, showMetalLines, isLog, minVal, maxVal]);

  // Area under resale value
  const resaleArea = useMemo(() => {
    if (validPoints.length === 0) return '';
    const bottomY = height - padBottom;
    return `${resalePath} L ${getX(validPoints.length - 1).toFixed(1)} ${bottomY} L ${getX(0).toFixed(1)} ${bottomY} Z`;
  }, [resalePath, validPoints]);

  // Y-axis grid ticks
  const yTicks = useMemo(() => {
    const ticks: number[] = [];
    const count = 5;
    if (isLog) {
      const logMin = Math.log10(minVal);
      const logMax = Math.log10(maxVal);
      for (let i = 0; i <= count; i++) {
        const val = Math.pow(10, logMin + (i / count) * (logMax - logMin));
        ticks.push(val);
      }
    } else {
      const step = (maxVal - minVal) / count;
      for (let i = 0; i <= count; i++) {
        ticks.push(minVal + i * step);
      }
    }
    return ticks;
  }, [minVal, maxVal, isLog]);

  // X-axis date labels
  const xTicks = useMemo(() => {
    if (validPoints.length === 0) return [];
    const count = Math.min(5, validPoints.length);
    const indices: number[] = [];
    for (let i = 0; i < count; i++) {
      const idx = Math.round((i / (count - 1)) * (validPoints.length - 1));
      if (!indices.includes(idx)) indices.push(idx);
    }
    return indices.map(idx => ({ index: idx, date: validPoints[idx].date }));
  }, [validPoints]);

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!validPoints.length) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const svgX = (clientX / rect.width) * width;
    const clampedX = Math.max(padLeft, Math.min(width - padRight, svgX));
    const ratio = (clampedX - padLeft) / innerWidth;
    const nearestIndex = Math.min(validPoints.length - 1, Math.max(0, Math.round(ratio * (validPoints.length - 1))));
    setHoverIndex(nearestIndex);
  };

  const hoveredPoint = hoverIndex !== null && validPoints[hoverIndex] ? validPoints[hoverIndex] : null;

  return (
    <div className="bg-white border border-ivory-300 rounded-xl p-5 shadow-sm space-y-4" ref={containerRef}>
      {/* Header controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ivory-200 pb-3">
        <div className="flex items-center gap-2">
          <span className="font-serif font-bold text-charcoal-900 tracking-wide text-base">
            Portfolio Capital & Valuation Progression
          </span>
          {isLog && (
            <span className="text-xs px-2 py-0.5 rounded bg-gold-100 text-gold-800 font-medium">
              Log Scale
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Range Buttons */}
          <div className="inline-flex rounded-lg border border-ivory-300 p-0.5 bg-ivory-50 text-xs">
            {(['1M', '6M', '1Y', '3Y', '5Y', 'ALL'] as RangeOption[]).map(r => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  range === r
                    ? 'bg-charcoal-900 text-ivory-50 shadow-xs'
                    : 'text-charcoal-700 hover:text-charcoal-950 hover:bg-ivory-200'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          {/* Log / Linear Toggle */}
          <button
            type="button"
            onClick={() => setIsLog(!isLog)}
            className={`px-3 py-1 text-xs font-medium rounded-lg border transition-all ${
              isLog
                ? 'bg-gold-500 text-white border-gold-600'
                : 'bg-ivory-100 text-charcoal-800 border-ivory-300 hover:bg-ivory-200'
            }`}
            title="Toggle Logarithmic Y-Axis"
          >
            {isLog ? 'Log Y' : 'Linear Y'}
          </button>

          {/* Toggle Gold/Silver lines */}
          <button
            type="button"
            onClick={() => setShowMetalLines(!showMetalLines)}
            className={`px-3 py-1 text-xs font-medium rounded-lg border transition-all ${
              showMetalLines
                ? 'bg-ivory-200 text-charcoal-900 border-ivory-400'
                : 'bg-ivory-100 text-charcoal-500 border-ivory-300'
            }`}
          >
            {showMetalLines ? 'Hide Gold/Silver' : 'Show Gold/Silver'}
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      {validPoints.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-charcoal-500 text-sm">
          <p>No historical purchase data recorded on or before {formatDisplayDate(selectedDate)}.</p>
          <p className="text-xs text-charcoal-400 mt-1">Add a purchase or load the demo portfolio to see the valuation progression.</p>
        </div>
      ) : (
        <div className="relative">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto overflow-visible select-none cursor-crosshair"
            onMouseMove={handleMouseMove}
            onMouseLeave={() => setHoverIndex(null)}
          >
            <defs>
              <linearGradient id="resaleGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#B88B2A" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#B88B2A" stopOpacity="0.01" />
              </linearGradient>
            </defs>

            {/* Y-axis grid lines */}
            {yTicks.map((tick, i) => {
              const y = getY(tick);
              return (
                <g key={`y-${i}`}>
                  <line
                    x1={padLeft}
                    y1={y}
                    x2={width - padRight}
                    y2={y}
                    stroke="#E8E2D5"
                    strokeDasharray="3 3"
                    strokeWidth="0.8"
                  />
                  <text
                    x={padLeft - 8}
                    y={y + 3.5}
                    textAnchor="end"
                    fontSize="10"
                    fill="#78716C"
                    fontFamily="Inter, sans-serif"
                  >
                    {formatINR(tick, { decimals: 0 })}
                  </text>
                </g>
              );
            })}

            {/* X-axis ticks */}
            {xTicks.map(({ index, date }) => {
              const x = getX(index);
              return (
                <g key={`x-${index}`}>
                  <line
                    x1={x}
                    y1={height - padBottom}
                    x2={x}
                    y2={height - padBottom + 5}
                    stroke="#78716C"
                    strokeWidth="1"
                  />
                  <text
                    x={x}
                    y={height - padBottom + 18}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#78716C"
                    fontFamily="Inter, sans-serif"
                  >
                    {formatDisplayDate(date)}
                  </text>
                </g>
              );
            })}

            {/* Shaded Area for Resale Value */}
            {resaleArea && <path d={resaleArea} fill="url(#resaleGrad)" />}

            {/* Benchmark transition marker line (NSE to IBJA on 2026-06-16) */}
            {validPoints.map((pt, i) => {
              if (pt.isSourceTransition) {
                const x = getX(i);
                return (
                  <g key={`marker-${i}`}>
                    <line
                      x1={x}
                      y1={padTop}
                      x2={x}
                      y2={height - padBottom}
                      stroke="#99701E"
                      strokeWidth="1.2"
                      strokeDasharray="4 2"
                    />
                    <text
                      x={x + 4}
                      y={padTop + 14}
                      fontSize="9"
                      fill="#7A5618"
                      fontWeight="600"
                    >
                      NSE ➔ IBJA
                    </text>
                  </g>
                );
              }
              return null;
            })}

            {/* Optional Gold Line */}
            {goldPath && (
              <path
                d={goldPath}
                fill="none"
                stroke="#D1AC56"
                strokeWidth="1.5"
                strokeDasharray="2 2"
                opacity="0.85"
              />
            )}

            {/* Optional Silver Line */}
            {silverPath && (
              <path
                d={silverPath}
                fill="none"
                stroke="#9BA2AA"
                strokeWidth="1.5"
                strokeDasharray="2 2"
                opacity="0.85"
              />
            )}

            {/* Cumulative Invested Amount Line (Charcoal dashed) */}
            {investedPath && (
              <path
                d={investedPath}
                fill="none"
                stroke="#3F3C3A"
                strokeWidth="2"
                strokeDasharray="4 3"
              />
            )}

            {/* Estimated Resale Value Line (Muted Gold Solid) */}
            {resalePath && (
              <path
                d={resalePath}
                fill="none"
                stroke="#B88B2A"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Hover vertical crosshair & dots */}
            {hoverIndex !== null && hoveredPoint && (
              <g>
                <line
                  x1={getX(hoverIndex)}
                  y1={padTop}
                  x2={getX(hoverIndex)}
                  y2={height - padBottom}
                  stroke="#2A2725"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />

                {/* Resale Dot */}
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(hoveredPoint.resaleValue)}
                  r="5"
                  fill="#B88B2A"
                  stroke="#FFFFFF"
                  strokeWidth="2"
                />

                {/* Invested Dot */}
                <circle
                  cx={getX(hoverIndex)}
                  cy={getY(hoveredPoint.investedCost)}
                  r="4"
                  fill="#2A2725"
                  stroke="#FFFFFF"
                  strokeWidth="2"
                />
              </g>
            )}
          </svg>

          {/* Interactive Tooltip Callout */}
          {hoveredPoint && hoverIndex !== null && (
            <div
              className="absolute z-20 top-2 pointer-events-none bg-charcoal-900 text-ivory-50 p-3 rounded-lg shadow-lg text-xs space-y-1.5 border border-charcoal-700 min-w-56"
              style={{
                left: `${Math.min(70, Math.max(10, (getX(hoverIndex) / width) * 100))}%`,
                transform: 'translateX(-50%)'
              }}
            >
              <div className="flex items-center justify-between border-b border-charcoal-700 pb-1 font-medium">
                <span>{formatDisplayDate(hoveredPoint.date)}</span>
                <span className="text-gold-300">{hoveredPoint.activeHoldings} lot(s) held</span>
              </div>
              <div className="grid grid-cols-2 gap-x-2 gap-y-1 pt-0.5">
                <span className="text-ivory-400">Invested Cost:</span>
                <span className="text-right font-mono font-medium">{formatINR(hoveredPoint.investedCost)}</span>

                <span className="text-gold-300">Resale Value:</span>
                <span className="text-right font-mono font-semibold text-gold-200">
                  {formatINR(hoveredPoint.resaleValue)}
                </span>

                {showMetalLines && (
                  <>
                    <span className="text-amber-200/80">Gold Value:</span>
                    <span className="text-right font-mono text-amber-100">{formatINR(hoveredPoint.goldResaleValue)}</span>

                    <span className="text-slate-300">Silver Value:</span>
                    <span className="text-right font-mono text-slate-100">{formatINR(hoveredPoint.silverResaleValue)}</span>
                  </>
                )}

                <span className="text-ivory-400">Unrealized Gain:</span>
                <span
                  className={`text-right font-mono font-semibold ${
                    hoveredPoint.resaleValue >= hoveredPoint.investedCost ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {formatINR(hoveredPoint.resaleValue - hoveredPoint.investedCost)} (
                  {formatPercent(
                    hoveredPoint.investedCost > 0
                      ? ((hoveredPoint.resaleValue - hoveredPoint.investedCost) / hoveredPoint.investedCost) * 100
                      : 0
                  )}
                  )
                </span>
              </div>

              {hoveredPoint.isSourceTransition && (
                <div className="pt-1 text-[10px] text-gold-300 border-t border-charcoal-700 italic">
                  Benchmark: Transitioned from NSE spot to IBJA closing rates.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Legend & Explanatory footnote */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-xs text-charcoal-600 border-t border-ivory-200">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5 bg-gold-600 rounded"></span>
            <span className="font-medium text-charcoal-800">Estimated Resale Value</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-4 h-0.5 bg-charcoal-800 border-b border-dashed border-charcoal-800"></span>
            <span className="font-medium text-charcoal-800">Cumulative Invested Cost</span>
          </div>
          {showMetalLines && (
            <>
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-4 h-0.5 bg-gold-400 border-b border-dotted border-gold-400"></span>
                <span>Gold Component</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="inline-block w-4 h-0.5 bg-silver-400 border-b border-dotted border-silver-400"></span>
                <span>Silver Component</span>
              </div>
            </>
          )}
        </div>

        <p className="text-[11px] text-charcoal-500 max-w-xl">
          Note: New purchases increase portfolio value and invested capital. This chart shows wealth progression rather
          than pure return. Chart range controls adjust visible window without altering inception-to-date XIRR.
        </p>
      </div>
    </div>
  );
};
