declare module 'bwip-js' {
  export interface ToCanvasOptions {
    bcid: string;
    text: string;
    scale?: number;
    height?: number;
    width?: number;
    includetext?: boolean;
    textxalign?: 'left' | 'center' | 'right' | 'justify' | 'off';
    eclevel?: 'L' | 'M' | 'Q' | 'H';
    [key: string]: any;
  }

  export function toCanvas(canvas: HTMLCanvasElement | string, opts: ToCanvasOptions): HTMLCanvasElement;
  export function toBuffer(opts: ToCanvasOptions): Promise<Buffer>;
}
