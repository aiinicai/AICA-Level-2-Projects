import React, { useState, useEffect } from 'react';

interface NumberInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
  value: number | undefined;
  onChange: (val: number) => void;
  className?: string;
  allowEmpty?: boolean;
}

export const NumberInput: React.FC<NumberInputProps> = ({
  value,
  onChange,
  className = '',
  allowEmpty = true,
  placeholder,
  ...props
}) => {
  // Keep local string state to allow clean deleting without snapping to 0
  const [text, setText] = useState<string>(() => {
    if (value === undefined || value === null) return '';
    if (value === 0 && allowEmpty) return '';
    return String(value);
  });

  const [isFocused, setIsFocused] = useState(false);

  useEffect(() => {
    if (!isFocused) {
      if (value === undefined || value === null) {
        setText('');
      } else if (value === 0 && allowEmpty) {
        setText('');
      } else {
        setText(String(value));
      }
    }
  }, [value, isFocused, allowEmpty]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    setText(raw);

    if (raw === '' || raw === '-') {
      onChange(0);
      return;
    }

    const parsed = parseFloat(raw);
    if (!isNaN(parsed)) {
      onChange(parsed);
    }
  };

  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    if (text === '' || text === '-') {
      if (!allowEmpty) {
        setText('0');
        onChange(0);
      }
    } else {
      const parsed = parseFloat(text);
      if (!isNaN(parsed)) {
        setText(String(parsed));
        onChange(parsed);
      } else {
        setText(value ? String(value) : (allowEmpty ? '' : '0'));
      }
    }
    props.onBlur?.(e);
  };

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    props.onFocus?.(e);
  };

  return (
    <input
      type="number"
      value={text}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
      placeholder={placeholder || (allowEmpty ? '0' : undefined)}
      className={className}
      {...props}
    />
  );
};
