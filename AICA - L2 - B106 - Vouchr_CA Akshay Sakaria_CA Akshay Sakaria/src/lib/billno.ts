/** Bill numbers compared the way people write them, keeping their structure:
 *  "INV-0045" = "inv/45" = "INV 045" = "INV45", and "ka-26-0164" = "KA/26/164" — but "KA/2/6164" ≠ "KA/26/164".
 *  Steps: any separator → "/", a "/" between letters and digits, leading zeros dropped per number group. */
export function normBillNo(n?: string): string {
  return (n ?? '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '/')
    .replace(/([a-z])(?=\d)/g, '$1/')
    .replace(/(\d)(?=[a-z])/g, '$1/')
    .replace(/\d+/g, (d) => d.replace(/^0+(?=\d)/, ''))
    .replace(/^\/+|\/+$/g, '');
}
