import React from 'react';
import { Input } from '@/components/ui/input';
import type { UnitMode } from '../types/cma';
import { fromUnit, toUnit } from '../lib/format';

interface NumInputProps {
  value: number;                    // raw rupees (or plain number when raw=true)
  onChange: (rawValue: number) => void;
  unit?: UnitMode;                  // display unit; omit for plain numbers (rates, days)
  raw?: boolean;                    // value is already in display terms (%, days, counts)
  className?: string;
  step?: number;
  disabled?: boolean;
  placeholder?: string;
}

/** Numeric input that displays values in the selected unit (Rs / '000 / Lakhs) */
export const NumInput: React.FC<NumInputProps> = ({ value, onChange, unit = 'lakhs' as UnitMode, raw, className, step, disabled, placeholder }) => {
  const display = raw ? value : toUnit(value || 0, unit);
  const [text, setText] = React.useState<string>(String(round(display)));
  const [focused, setFocused] = React.useState(false);

  React.useEffect(() => {
    if (!focused) setText(String(round(display)));
  }, [display, focused]);

  return (
    <Input
      type="number"
      value={text}
      step={step}
      disabled={disabled}
      placeholder={placeholder}
      className={className}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      onChange={e => {
        setText(e.target.value);
        const n = parseFloat(e.target.value);
        if (!Number.isNaN(n)) onChange(raw ? n : fromUnit(n, unit));
        else if (e.target.value === '') onChange(0);
      }}
    />
  );
};

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
