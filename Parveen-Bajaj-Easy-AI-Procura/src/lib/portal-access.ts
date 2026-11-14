export function supplierCanView(ownSupplier: string | null, active: boolean, documentSupplier: string, status: string, kind: 'lpo' | 'grn' | 'invoice') {
  return active && ownSupplier === documentSupplier && (kind === 'lpo' ? ['PENDING', 'APPROVED'] : ['PENDING', 'APPROVED', 'REJECTED']).includes(status);
}
