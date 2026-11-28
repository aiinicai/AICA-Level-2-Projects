# Tally XML reference (starting templates – verify on the user's Tally)

**Most reliable method:** in a TEST company, enter one voucher of each kind manually,
export it (TallyPrime: Alt+E → Export → XML) and make the builder reproduce that
structure. Tag names for GST details differ between TallyPrime releases and Tally.ERP 9,
which is why `services/tally/adapters/` exists.

**Setup:** TallyPrime → F1 Help → Settings → Connectivity → Client/Server configuration →
"TallyPrime acts as" = Both, Port 9000. Tally.ERP 9: F12 → Advanced Configuration.
The company must be open. All requests: HTTP POST of XML to `http://<host>:<port>`.

## List open companies (inline TDL collection)
```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
          <TYPE>Collection</TYPE><ID>IPTCompanies</ID></HEADER>
  <BODY><DESC>
    <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <COLLECTION NAME="IPTCompanies"><TYPE>Company</TYPE>
        <FETCH>NAME, GUID, STARTINGFROM, BOOKSFROM</FETCH></COLLECTION>
    </TDLMESSAGE></TDL>
  </DESC></BODY>
</ENVELOPE>
```

## Ledgers of one company
```xml
<ENVELOPE>
  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST>
          <TYPE>Collection</TYPE><ID>IPTLedgers</ID></HEADER>
  <BODY><DESC>
    <STATICVARIABLES>
      <SVCURRENTCOMPANY>ABC Enterprises</SVCURRENTCOMPANY>
      <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
    </STATICVARIABLES>
    <TDL><TDLMESSAGE>
      <COLLECTION NAME="IPTLedgers"><TYPE>Ledger</TYPE>
        <FETCH>NAME, PARENT, GUID, ALTERID, PARTYGSTIN, LEDGSTREGDETAILS.LIST</FETCH>
      </COLLECTION>
    </TDLMESSAGE></TDL>
  </DESC></BODY>
</ENVELOPE>
```
Same pattern with TYPE = StockItem, StockGroup, Unit, Godown, VoucherType, Group,
CostCentre. Ledger GSTIN: older builds use `PARTYGSTIN`; newer TallyPrime keeps it inside
`LEDGSTREGDETAILS.LIST` – the adapter must read both.

## Import: accounting-mode purchase (₹10,000 + 9% CGST + 9% SGST = ₹11,800)
```xml
<ENVELOPE>
 <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
 <BODY><IMPORTDATA>
  <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME>
   <STATICVARIABLES><SVCURRENTCOMPANY>ABC Enterprises</SVCURRENTCOMPANY></STATICVARIABLES>
  </REQUESTDESC>
  <REQUESTDATA><TALLYMESSAGE xmlns:UDF="TallyUDF">
   <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
    <DATE>20260415</DATE>
    <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
    <VOUCHERNUMBER>IPT-000123</VOUCHERNUMBER>
    <REFERENCE>INV/2026/045</REFERENCE>          <!-- supplier invoice no -->
    <REFERENCEDATE>20260412</REFERENCEDATE>
    <PARTYLEDGERNAME>XYZ Traders</PARTYLEDGERNAME>
    <PARTYGSTIN>08ABCDE1234F1Z5</PARTYGSTIN>
    <PLACEOFSUPPLY>Rajasthan</PLACEOFSUPPLY>
    <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
    <ISINVOICE>Yes</ISINVOICE>
    <NARRATION>Imported by IPT | Doc #123 | Inv INV/2026/045</NARRATION>
    <LEDGERENTRIES.LIST>                          <!-- party: Credit -->
      <LEDGERNAME>XYZ Traders</LEDGERNAME>
      <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><ISPARTYLEDGER>Yes</ISPARTYLEDGER>
      <AMOUNT>11800.00</AMOUNT>
      <BILLALLOCATIONS.LIST><NAME>INV/2026/045</NAME><BILLTYPE>New Ref</BILLTYPE>
        <AMOUNT>11800.00</AMOUNT></BILLALLOCATIONS.LIST>
    </LEDGERENTRIES.LIST>
    <LEDGERENTRIES.LIST>                          <!-- purchase: Debit -->
      <LEDGERNAME>Purchase @18%</LEDGERNAME>
      <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-10000.00</AMOUNT>
    </LEDGERENTRIES.LIST>
    <LEDGERENTRIES.LIST>
      <LEDGERNAME>Input CGST @9%</LEDGERNAME>
      <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-900.00</AMOUNT>
    </LEDGERENTRIES.LIST>
    <LEDGERENTRIES.LIST>
      <LEDGERNAME>Input SGST @9%</LEDGERNAME>
      <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-900.00</AMOUNT>
    </LEDGERENTRIES.LIST>
   </VOUCHER>
  </TALLYMESSAGE></REQUESTDATA>
 </IMPORTDATA></BODY>
</ENVELOPE>
```
Sign rule: debits negative with ISDEEMEDPOSITIVE=Yes; credits positive with No.
Before sending, assert the sum of all AMOUNT values is exactly 0.00.

## Inventory mode: item lines instead of the purchase ledger entry
```xml
<ALLINVENTORYENTRIES.LIST>
  <STOCKITEMNAME>Copper Wire 2.5mm</STOCKITEMNAME>
  <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
  <RATE>500.00/Mtr</RATE>
  <AMOUNT>-10000.00</AMOUNT>
  <ACTUALQTY> 20 Mtr</ACTUALQTY><BILLEDQTY> 20 Mtr</BILLEDQTY>
  <BATCHALLOCATIONS.LIST><GODOWNNAME>Main Location</GODOWNNAME>
    <AMOUNT>-10000.00</AMOUNT><ACTUALQTY> 20 Mtr</ACTUALQTY><BILLEDQTY> 20 Mtr</BILLEDQTY>
  </BATCHALLOCATIONS.LIST>
  <ACCOUNTINGALLOCATIONS.LIST><LEDGERNAME>Purchase @18%</LEDGERNAME>
    <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-10000.00</AMOUNT>
  </ACCOUNTINGALLOCATIONS.LIST>
</ALLINVENTORYENTRIES.LIST>
```
Unit symbols and quantity format must match the Tally unit master exactly. A supplier's
credit note is recorded as a Debit Note voucher in the buyer's books (signs reversed);
confirm the firm's voucher-type convention.

## Response parsing
```xml
<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><DELETED>0</DELETED>
  <LASTVCHID>4521</LASTVCHID><LASTMID>0</LASTMID><COMBINED>0</COMBINED>
  <IGNORED>0</IGNORED><ERRORS>0</ERRORS><CANCELLED>0</CANCELLED></RESPONSE>
```
Success only if CREATED ≥ 1 and ERRORS = 0. Store any `<LINEERROR>` text verbatim and show
it. After success, query the voucher again by party + REFERENCE before marking the invoice
imported. Before every import, query for an existing voucher with the same party and
REFERENCE to block duplicates.
