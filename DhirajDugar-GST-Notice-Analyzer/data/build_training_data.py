"""Reproduce the small synthetic corpus. No taxpayer information is used."""
import csv
from pathlib import Path
EXAMPLES = {
 'itc_mismatch': [
  'Input tax credit claimed in GSTR-3B exceeds credit appearing in GSTR-2B.',
  'There is an ITC mismatch between supplier uploaded details and the return.',
  'Purchase credit is not reflected in the auto drafted inward supply statement.',
  'Excess input tax credit availed compared with GSTR-2A records.',
  'Invoices supporting the credit claim are missing from supplier filings.',
  'The inward supply statement shows lower eligible credit than that taken.',
  'Reconcile supplier reported invoices against credits claimed in monthly returns.',
  'Difference in input tax credit between books and the supplier statement.',
  'Credit availed in the return is higher than the auto populated purchase data.',
  'Supplier invoice reporting does not support the input credit claimed.',
 ],
 'liability_gap': [
  'Tax liability declared in GSTR-1 is more than tax discharged in GSTR-3B.',
  'Outward supplies have been under reported in the tax payment return.',
  'Output tax payable differs from the amount actually discharged.',
  'Sales disclosed in the outward statement are absent from monthly returns.',
  'Short payment of tax on outward taxable supplies was observed.',
  'Tax on sales invoices has not been paid through the return.',
  'A gap exists between outward supply declarations and output liability.',
  'Sales register tax exceeds tax paid in monthly returns.',
  'Reconcile GSTR-1 and GSTR-3B differences in output tax.',
  'Liability on outward transactions has been understated.',
 ],
 'rcm': [
  'Reverse charge liability on legal services remains unpaid.',
  'RCM tax has not been discharged on notified inward supplies.',
  'Tax payable by the recipient on reverse charge was omitted.',
  'The recipient is liable to pay GST on the notified service.',
  'Reverse charge tax on inward service invoices has been short paid.',
  'The reverse charge column of the return omits taxable expenses.',
  'Liability under section 9(3) on recipient side has not been paid.',
  'RCM was not deposited in cash for the specified transactions.',
  'Recipient tax on notified supplies is missing from the return.',
  'Reverse charge on imported services requires reconciliation.',
 ],
 'blocked_itc': [
  'Blocked input tax credit under section 17(5) has been availed.',
  'Ineligible ITC on passenger motor vehicles was claimed.',
  'Credit on personal consumption expenses is inadmissible.',
  'Input tax on food and beverages is alleged to be blocked.',
  'The disputed purchase falls under the blocked credit provisions.',
  'Credit claimed on a restricted inward supply needs reversal.',
  'Motor car credit is disallowed under section 17(5).',
  'Ineligible input credit on construction of immovable property is questioned.',
  'Credits on employee vacation travel are alleged to be inadmissible.',
  'The claim includes tax on supplies excluded from input credit.',
 ],
 'late_filing': [
  'Monthly returns were filed after the due dates and late fee is unpaid.',
  'Delay in furnishing returns attracts late filing fee.',
  'The taxpayer has failed to file GSTR-3B for the period.',
  'Annual return filing was delayed beyond the extended due date.',
  'Return non filing has been identified for several months.',
  'Late fee on overdue returns has not been discharged.',
  'Failure to furnish the return within the prescribed time was noticed.',
  'Return acknowledgements show delayed filing.',
  'Overdue monthly returns remain unfiled.',
  'Filing after the deadline requires verification of late fees.',
 ],
 'other': [
  'Please attend the personal hearing at the stated venue.',
  'Name address registration number and jurisdiction of the taxpayer.',
  'The officer requests supporting documents for further examination.',
  'This is a fictional educational sample only.',
  'Date of notice and reference number are given above.',
  'There is a dispute about the classification of the product.',
  'The place of supply and valuation of goods are questioned.',
  'Registration cancellation proceedings are being initiated.',
  'An appeal against the order has been submitted.',
  'All records shall be produced for inspection.',
 ],
}
if __name__ == '__main__':
 with Path(__file__).with_name('training_examples.csv').open('w', newline='', encoding='utf-8') as f:
  w = csv.writer(f); w.writerow(['label', 'text'])
  for label, rows in EXAMPLES.items():
   for text in rows: w.writerow([label, text])
