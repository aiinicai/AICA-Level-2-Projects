import { validatePlaceholderValue } from '../modules/generation/validators';

describe('validatePlaceholderValue', () => {
  it('accepts a valid PAN', () => {
    expect(validatePlaceholderValue('PAN', 'ABCDE1234F').valid).toBe(true);
  });
  it('rejects an invalid PAN', () => {
    expect(validatePlaceholderValue('PAN', '12345').valid).toBe(false);
  });
  it('accepts a valid GSTIN', () => {
    expect(validatePlaceholderValue('GSTIN', '29ABCDE1234F1Z5').valid).toBe(true);
  });
  it('accepts a valid 10-digit mobile starting 6-9', () => {
    expect(validatePlaceholderValue('Mobile', '9876543210').valid).toBe(true);
  });
  it('rejects a mobile number starting with an invalid digit', () => {
    expect(validatePlaceholderValue('Mobile', '1234567890').valid).toBe(false);
  });
  it('accepts a valid email', () => {
    expect(validatePlaceholderValue('Email', 'a@b.com').valid).toBe(true);
  });
  it('rejects a malformed email', () => {
    expect(validatePlaceholderValue('Email', 'not-an-email').valid).toBe(false);
  });
  it('accepts a valid 6-digit PIN code', () => {
    expect(validatePlaceholderValue('PinCode', '560001').valid).toBe(true);
  });
  it('free-text fields are always valid', () => {
    expect(validatePlaceholderValue('Text', 'anything at all').valid).toBe(true);
  });
  it('requires a value for typed fields', () => {
    expect(validatePlaceholderValue('Email', '').valid).toBe(false);
  });
});
