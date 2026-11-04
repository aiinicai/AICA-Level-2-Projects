// Layouts seen in real test invoices (Tally e-invoice, marketplace, travel aggregator, ride-hailing, thermal receipt photo),
// reproduced with INVENTED names, numbers and GSTINs so no real data is stored in the code.
import { describe, expect, it } from 'vitest';
import { parseInvoiceText, repairGstin } from './extract';
import { gstinCheckChar } from './validators';

const g = (first14: string) => first14 + gstinCheckChar(first14);
const SELLER = g('27AAKFS4821M1Z'), BUYER = g('27AABFT1234K1Z'), MKT = g('24AAKCR7310Q1Z'), AGG = g('06AAKCM5146R1Z'), RIDE = g('07AAKCU6223H1Z');

describe('on-device invoice reading — real-world layouts', () => {
  it('Tally e-invoice: interleaved columns, "Total Inv Amt", tax-summary row ignored, wrapped IRN', () => {
    const t = [
      'e-Invoice', 'IRN   :   aaaaaaaaaabbbbbbbbbbccccccccccdddddddddd1111111111222222-', '22223333', 'Invoice No.    Dated', 'e-Way Bill No.',
      'SAMPLE STEEL WORKS PVT. LTD.', 'SSW/101/25-26   202149870000  27-Feb-26', `GSTIN/UIN: ${SELLER}`, `Buyer GSTIN/UIN : ${BUYER}`,
      'HSN/SAC   Taxable CGST SGST/UTGST Total', 'Total   10,00,000.00 90,000.00 90,000.00 1,80,000.00',
      'Tot.Taxable Amt   :   10,00,000.00   Other Amt   :   Total Inv Amt   : 11,80,000.00'
    ].join('\n');
    const r = parseInvoiceText(t, BUYER);
    expect(r).toMatchObject({ vendorGstin: SELLER, vendorName: 'SAMPLE STEEL WORKS PVT. LTD.', invoiceNo: 'SSW/101/25-26', invoiceDate: '2026-02-27', totalAmount: 1180000 });
    expect(r.irn).toBe('aaaaaaaaaabbbbbbbbbbccccccccccdddddddddd111111111122222222223333');
  });

  it('marketplace: "Grand Total" beats the gross column; "Sold By:" names the seller', () => {
    const t = ['Tax Invoice', 'Sold By: Sample Retail Private Limited , Ship-from Address: Plot 1, Ahmedabad', `GSTIN - ${MKT}`, 'Invoice Number # FAXX0000000001',
      'Invoice Date: 29-07-2025', 'Total   1   429.00   -50.00   321.18   28.90   28.90   379.00', 'Grand Total   ₹   379.00'].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ vendorName: 'Sample Retail Private Limited', totalAmount: 379, invoiceNo: 'FAXX0000000001' });
  });

  it('travel aggregator: label row / value row columns; CIN digits are not an amount', () => {
    const t = ['SAMPLETRIP (INDIA) PRIVATE LIMITED', 'TAX INVOICE', 'Invoice No.  HSN/SAC', 'M06XX26I00000001  998551', 'Date  GSTIN', `01 Jul 2025  ${AGG}`,
      'Place of Supply  CIN', 'Haryana  U63040HR2000PTC000000', 'Service Fees ₹135.59', 'CGST @9% ₹12.2', 'SGST @9% ₹12.2', 'Grand Total   ₹2875.0'].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ invoiceNo: 'M06XX26I00000001', hsnSac: '998551', totalAmount: 2875, invoiceDate: '2025-07-01', vendorName: 'SAMPLETRIP (INDIA) PRIVATE LIMITED' });
  });

  it('ride-hailing: the e-commerce operator named in "Invoice issued by … on behalf of"', () => {
    const t = ['Tax Invoice', 'Rider Name  Invoice issued by Sample Rides India Private', 'Limited on behalf of: DRIVER NAME', 'Invoice number:   FHXX0000000001',
      'Invoice date:   10 Sept 2025', 'Total net amount   ₹ 766.65', 'Total IGST 5%   ₹ 38.33', 'Total amount payable   ₹ 804.98', `GST: ${RIDE}`].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ vendorName: 'Sample Rides India Private Limited', totalAmount: 804.98, invoiceNo: 'FHXX0000000001', gstRatePct: 5 });
  });

  it('receipt photo: OCR look-alikes in the GSTIN are repaired only when the check digit then passes', () => {
    const misread = SELLER.slice(0, 13) + '2' + SELLER[14]; // "Z" read as "2"
    const r = parseInvoiceText(['Sample Sweets', `GSTIN : ${misread}`, 'Date: 18/03/26', '8ill No.: 255726', 'Grand Total ¥766.00'].join('\n'));
    expect(r).toMatchObject({ vendorGstin: SELLER, gstinRepaired: true, invoiceNo: '255726', totalAmount: 766 });
    // a wrong letter that is not a look-alike cannot be repaired — left unread, never guessed
    expect(repairGstin(SELLER.slice(0, 3) + 'M' + SELLER.slice(4))).toBeUndefined();
  });
});
