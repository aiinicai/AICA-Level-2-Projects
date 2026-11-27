import {
  CustomData,
  CustomSeriesOptions,
  CustomSeriesPricePlotValues,
  CustomSeriesWhitespaceData,
  ICustomSeriesPaneRenderer,
  ICustomSeriesPaneView,
  PaneRendererCustomData,
  PriceToCoordinateConverter,
  Time,
  customSeriesDefaultOptions,
} from 'lightweight-charts';

export interface VolumeCandleData extends CustomData<Time> {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  volRatio20?: number;
}

export interface VolumeCandlesSeriesOptions extends CustomSeriesOptions {
  upColor: string;
  downColor: string;
  wideUpColor: string;
  wideDownColor: string;
  borderUpColor: string;
  borderDownColor: string;
  wickUpColor: string;
  wickDownColor: string;
  minWidthScale: number;
  maxWidthScale: number;
}

type RenderTarget2D = Parameters<ICustomSeriesPaneRenderer['draw']>[0];

interface PreparedBar {
  x: number;
  data: VolumeCandleData;
  widthCss: number;
  scale: number;
}

class VolumeCandlesRenderer implements ICustomSeriesPaneRenderer {
  private _data: PaneRendererCustomData<Time, VolumeCandleData> | null = null;
  private _options: VolumeCandlesSeriesOptions | null = null;

  update(
    data: PaneRendererCustomData<Time, VolumeCandleData>,
    options: VolumeCandlesSeriesOptions
  ): void {
    this._data = data;
    this._options = options;
  }

  draw(
    target: RenderTarget2D,
    priceConverter: PriceToCoordinateConverter,
    _isHovered: boolean,
    _hitTestData?: unknown
  ): void {
    const data = this._data;
    const options = this._options;
    if (!data || !options || data.bars.length === 0 || !data.visibleRange) return;

    const from = Math.max(0, Math.floor(data.visibleRange.from));
    const to = Math.min(data.bars.length, Math.ceil(data.visibleRange.to));
    if (to <= from) return;

    const visibleBars = data.bars.slice(from, to);
    const count = visibleBars.length;
    if (count === 0) return;

    // 1. Use the visible MEDIAN volume (50th percentile) as the 1.0x baseline so a few
    //    massive spike days never skew the baseline upward and shrink normal/low-volume candles.
    const posVols: number[] = [];
    for (let i = 0; i < count; i++) {
      const v = visibleBars[i].originalData.volume;
      if (Number.isFinite(v) && v > 0) posVols.push(v);
    }
    posVols.sort((a, b) => a - b);
    const visMedianVol =
      posVols.length > 0
        ? posVols.length % 2 === 1
          ? posVols[Math.floor(posVols.length / 2)]
          : (posVols[posVols.length / 2 - 1] + posVols[posVols.length / 2]) / 2
        : 0;

    // 2. Anchor 1.0x volume to standard TradingView candlestick width (~72% of barSpacing).
    //    Low-to-normal volume bars stay near full normal candlestick width (minScale ~0.82)
    //    instead of shrinking into thin sticks, while high-volume bars expand visibly WIDER
    //    (up to maxScale ~2.8x normal width) to highlight institutional participation.
    const effectiveSpacing = Math.max(2, data.barSpacing * (data.conflationFactor || 1));
    const normalCandleWidth = Math.max(2, effectiveSpacing * 0.72);
    const minScale = Math.max(0.7, Math.min(1.0, options.minWidthScale));
    const maxScale = Math.max(1.5, options.maxWidthScale);
    const hardMaxWidthCss = Math.max(6, effectiveSpacing * 2.55);

    const prepared: PreparedBar[] = new Array(count);

    for (let i = 0; i < count; i++) {
      const bar = visibleBars[i];
      const orig = bar.originalData;

      let relVol = 1;
      if (visMedianVol > 0 && Number.isFinite(orig.volume) && orig.volume > 0) {
        relVol = orig.volume / visMedianVol;
      } else if (orig.volRatio20 && Number.isFinite(orig.volRatio20) && orig.volRatio20 > 0) {
        relVol = orig.volRatio20;
      }

      let scale: number;
      if (relVol <= 1.0) {
        // Gentle floor near standard candlestick size so low-volume bars never look crushed
        const t = Math.max(0, Math.min(1, relVol));
        scale = minScale + (1.0 - minScale) * Math.sqrt(t);
      } else {
        // Noticeable upward expansion for above-median volume bars (1.5x, 2x, 3x, 5x+)
        const excess = Math.min(1, Math.pow((relVol - 1.0) / 3.5, 0.68));
        scale = 1.0 + (maxScale - 1.0) * excess;
      }

      const widthCss = Math.min(hardMaxWidthCss, Math.max(1.6, normalCandleWidth * scale));
      prepared[i] = {
        x: bar.x,
        data: orig,
        widthCss,
        scale,
      };
    }

    // 3. Draw widest (highest-volume) candles FIRST and narrower/normal candles ON TOP so
    //    expanded high-volume candles visibly bloom wider without hiding neighboring bars.
    const drawOrder = prepared
      .map((item, idx) => ({ item, idx }))
      .sort((a, b) => b.item.widthCss - a.item.widthCss || a.idx - b.idx);

    target.useBitmapCoordinateSpace(({ context: ctx, horizontalPixelRatio: hpr, verticalPixelRatio: vpr }) => {
      const wickPixelWidth = Math.max(1, Math.floor(hpr));

      // Pass A: Draw volume-scaled bodies (widest first, normal/narrower cleanly on top)
      for (let k = 0; k < drawOrder.length; k++) {
        const { item } = drawOrder[k];
        const d = item.data;

        const openY = priceConverter(d.open);
        const highY = priceConverter(d.high);
        const lowY = priceConverter(d.low);
        const closeY = priceConverter(d.close);
        if (openY === null || highY === null || lowY === null || closeY === null) continue;

        const isUp = d.close >= d.open;
        const isExpanded = item.scale > 1.15;
        const fillColor = isExpanded
          ? isUp
            ? options.wideUpColor
            : options.wideDownColor
          : isUp
          ? options.upColor
          : options.downColor;
        const borderColor = isUp ? options.borderUpColor : options.borderDownColor;
        const wickColor = isUp ? options.wickUpColor : options.wickDownColor;

        const centerPx = Math.round(item.x * hpr);
        const halfPx = Math.max(1, Math.round((item.widthCss / 2) * hpr));
        const bodyLeft = centerPx - halfPx;
        const bodyWidth = halfPx * 2 + (wickPixelWidth % 2 === 1 ? 1 : 0);

        const highPx = Math.round(highY * vpr);
        const lowPx = Math.round(lowY * vpr);
        const topPx = Math.round(Math.min(openY, closeY) * vpr);
        const bottomPx = Math.round(Math.max(openY, closeY) * vpr);
        const minDojiHeight = Math.max(1, Math.round(1.5 * vpr));
        const bodyHeightPx = Math.max(minDojiHeight, bottomPx - topPx);

        // Centered high-low wick anchored exactly on bar.x
        ctx.fillStyle = wickColor;
        const wickLeft = centerPx - Math.floor(wickPixelWidth / 2);
        ctx.fillRect(wickLeft, highPx, wickPixelWidth, Math.max(1, lowPx - highPx));

        // Volume-scaled OHLC body
        ctx.fillStyle = fillColor;
        ctx.fillRect(bodyLeft, topPx, bodyWidth, bodyHeightPx);

        // Crisp 1px high-contrast border keeps overlapping expanded candles unmistakably legible
        if (bodyWidth >= 3 * hpr && bodyHeightPx >= 2 * vpr) {
          ctx.strokeStyle = borderColor;
          ctx.lineWidth = Math.max(1, Math.round(hpr * (isExpanded ? 1.05 : 0.85)));
          ctx.strokeRect(
            bodyLeft + 0.5,
            topPx + 0.5,
            Math.max(1, bodyWidth - 1),
            Math.max(1, bodyHeightPx - 1)
          );
        }
      }
    });
  }
}

export class VolumeCandlesSeries
  implements ICustomSeriesPaneView<Time, VolumeCandleData, VolumeCandlesSeriesOptions>
{
  private _renderer: VolumeCandlesRenderer = new VolumeCandlesRenderer();

  priceValueBuilder(plotRow: VolumeCandleData): CustomSeriesPricePlotValues {
    return [plotRow.high, plotRow.low, plotRow.close];
  }

  isWhitespace(
    data: VolumeCandleData | CustomSeriesWhitespaceData<Time>
  ): data is CustomSeriesWhitespaceData<Time> {
    return (
      !('open' in data) ||
      !('close' in data) ||
      !Number.isFinite((data as VolumeCandleData).close)
    );
  }

  renderer(): ICustomSeriesPaneRenderer {
    return this._renderer;
  }

  update(
    data: PaneRendererCustomData<Time, VolumeCandleData>,
    options: VolumeCandlesSeriesOptions
  ): void {
    this._renderer.update(data, options);
  }

  defaultOptions(): VolumeCandlesSeriesOptions {
    return {
      ...customSeriesDefaultOptions,
      upColor: '#10b981',
      downColor: '#ef4444',
      wideUpColor: 'rgba(16, 185, 129, 0.72)',
      wideDownColor: 'rgba(239, 68, 68, 0.72)',
      borderUpColor: '#059669',
      borderDownColor: '#dc2626',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
      minWidthScale: 0.82,
      maxWidthScale: 2.8,
      priceLineVisible: false,
    };
  }
}
