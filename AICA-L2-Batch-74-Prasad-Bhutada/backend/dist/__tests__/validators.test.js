"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const validators_1 = require("../modules/generation/validators");
describe('validatePlaceholderValue', () => {
    it('accepts a valid PAN', () => {
        expect((0, validators_1.validatePlaceholderValue)('PAN', 'ABCDE1234F').valid).toBe(true);
    });
    it('rejects an invalid PAN', () => {
        expect((0, validators_1.validatePlaceholderValue)('PAN', '12345').valid).toBe(false);
    });
    it('accepts a valid GSTIN', () => {
        expect((0, validators_1.validatePlaceholderValue)('GSTIN', '29ABCDE1234F1Z5').valid).toBe(true);
    });
    it('accepts a valid 10-digit mobile starting 6-9', () => {
        expect((0, validators_1.validatePlaceholderValue)('Mobile', '9876543210').valid).toBe(true);
    });
    it('rejects a mobile number starting with an invalid digit', () => {
        expect((0, validators_1.validatePlaceholderValue)('Mobile', '1234567890').valid).toBe(false);
    });
    it('accepts a valid email', () => {
        expect((0, validators_1.validatePlaceholderValue)('Email', 'a@b.com').valid).toBe(true);
    });
    it('rejects a malformed email', () => {
        expect((0, validators_1.validatePlaceholderValue)('Email', 'not-an-email').valid).toBe(false);
    });
    it('accepts a valid 6-digit PIN code', () => {
        expect((0, validators_1.validatePlaceholderValue)('PinCode', '560001').valid).toBe(true);
    });
    it('free-text fields are always valid', () => {
        expect((0, validators_1.validatePlaceholderValue)('Text', 'anything at all').valid).toBe(true);
    });
    it('requires a value for typed fields', () => {
        expect((0, validators_1.validatePlaceholderValue)('Email', '').valid).toBe(false);
    });
});
//# sourceMappingURL=validators.test.js.map