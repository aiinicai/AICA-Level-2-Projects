# Accounting assumptions, policy choices and sources

## Sources used
* IFRS 16 *Leases* (IFRS Foundation) – the authoritative text is on <https://www.ifrs.org>. The illustrative examples were consulted at [IFRS 16 Illustrative Examples](https://ifrs.org/content/dam/ifrs/publications/html-standards/english/2022/issued/ifrs16-ie.html).
* [IFRS Foundation – IFRS 16 lease modifications for lessees (webcast slides, 2017)](https://www.ifrs.org/content/dam/ifrs/supporting-implementation/ifrs-16/ifrs-16-supporting-implementation-webcast-slides/ifrs-16-lease-modifications-lessees-webcast-march-2017.pdf)
* [KPMG – Lease modifications (2018)](https://assets.kpmg.com/content/dam/kpmg/xx/pdf/2018/09/lease-modifications-2018.pdf) (secondary source)
* TallyPrime developer documentation: [XML integration](https://help.tallysolutions.com/xml-integration/), [XML method-specific integration](https://help.tallysolutions.com/developer-reference/integration-capabilities/method-specific-integration/xml/), [Getting started with Tally integrations](https://help.tallysolutions.com/getting-started-with-tally-integrations/), [Importing XML into TallyPrime](https://help.tallysolutions.com/how-to-import-data-from-xml-into-tallyprime-tallyhelp/), [JSON integration](https://help.tallysolutions.com/tally-prime-integration-using-json-1/).

**Verification status.** The IFRS 16 paragraph text for paras 24–46 could not be retrieved verbatim in the build environment, so paragraph numbers quoted in the app and here (e.g. 16.39–16.46) come from the author's knowledge of the standard and must be **checked against the IFRS Foundation text** before use in financial statements. Not every Tally tag was confirmed against the documentation (see "Tally" below).

## Scope
In scope: lessee accounting; right-of-use model; short-term and low-value exemption workflow; initial measurement; effective-interest liability; depreciation; reassessments; modifications; full/partial terminations; journals; local posting to TallyPrime.
**Deliberately out of scope (first release)** – the app does not silently apply a wrong treatment; it simply has no input path for them:
* Lessor accounting (finance/operating lease classification, net investment in the lease).
* Sale-and-leaseback transactions (IFRS 16.98–103).
* Subleases (intermediate lessor), lease/non-lease component separation (all payments entered are treated as lease payments – exclude non-lease components yourself, or apply the practical expedient as a policy).
* Variable payments not based on an index/rate (expensed as incurred; do not enter them).
* Foreign-currency remeasurement of lease liabilities (IAS 21): the lease currency is converted at **one fixed rate** on input.
* Unwinding of the restoration provision (IAS 37) and its remeasurement; the provision is recognised at initial measurement only.
* Impairment of ROU assets (IAS 36), COVID-19 rent-concession expedient, and disclosures.
* Investment property / revalued ROU assets (cost model only).

## Conventions (stated assumptions)
1. **Amounts** are `Decimal`, rounded half-up (configurable) to 2 decimals (configurable) at each posting; the final-period interest absorbs the cumulative rounding difference and the amount is shown in the *Rounding* column and in the row trace. If the residual exceeds a small tolerance the app stops with an error rather than hiding it.
2. **Payment dates.** Arrears payments fall on the first day after each period (e.g. January rent on 1 February); advance payments fall on the first day of each period. Payments dated on or before commencement are treated as paid at commencement (they are excluded from the liability and added to the ROU asset). Edited/irregular payments override the generated pattern. The last day of the lease term is *inclusive* (term boundary = end date + 1 day).
3. **Interest** accrues on actual dates using the chosen day count (ACT/365, ACT/360, 30E/360) and compounding (annual, semi-annual, quarterly, monthly): growth factor = (1 + r/m)^(m·t). Interest is posted monthly by default (policy choice) or only at payment dates.
4. **Depreciation** is straight-line by days (or declining balance switching to straight-line) over the shorter of lease term and useful life, or over the useful life where ownership transfers or a purchase option is reasonably certain (IFRS 16.32).
5. **Events take effect at the start of their effective date.** A payment falling due on the effective date is therefore a *future* payment and takes the revised amount.
6. **Discount rates.** The rate (implicit or IBR) is an input. Revised rates are required – and enforced – for lease-term/purchase-option reassessments and for modifications that are not separate leases or scope decreases, and for payment changes caused by floating-rate movements. Index-linked payment changes and residual value guarantee changes keep the original rate. For a partial termination the original rate is used to derecognise the portion; a revised rate is demanded only if you also change remaining payments or term.
7. **Reassessment vs modification.** Reassessments (term, purchase option, index/rate, RVG) apply the existing contract; modifications are changes to terms. Every modification first runs the *separate lease* test (adds a right of use **and** price commensurate with stand-alone price; the tolerance and stand-alone price are your judgments). A separate lease leaves the existing lease untouched and gives you the data for a new lease.
8. **ROU floor.** A liability decrease reduces the ROU asset to nil at most; the remainder is recognised in profit or loss (account `GAIN_LOSS`).
9. **Termination.** Liability and ROU (cost and accumulated depreciation) are derecognised in proportion to the reduction in scope; gain/loss = liability derecognised − ROU derecognised − cash paid. Full termination zeroes the balances and stops all future schedule rows and journals.
10. **History.** Events are append-only. Original terms lock once an event or any approved/posted journal exists. An event cannot be effective on/before a journal already posted to (or awaiting confirmation from) Tally. Unposted later journals are marked *superseded*, never deleted. Posted/approved journal content is never rewritten (a conflict is audited instead).
11. **Exemptions.** Eligibility tests are shown but the election is yours (policy choice). Exempt leases are expensed straight-line over the term with accrual/payment journals.

## Tally
* Transport: HTTP POST of an XML envelope (`TALLYREQUEST=Import`, `TYPE=Data`, `ID=Vouchers`) to the configured host/port (default 9000); company set through `SVCURRENTCOMPANY`. Debit lines use `ISDEEMEDPOSITIVE=Yes` with a negative amount; credit lines `No` with a positive amount.
* Idempotency: voucher number, reference and `REMOTEID` all carry the stable journal reference `LEASE/V<version>/<SOURCE>/<date>/<n>`; the app also refuses to resend journals that are `posted` or `unconfirmed`.
* Success is declared **only** when Tally's response reports a created voucher (`CREATED` ≥ 1, no `LINEERROR`, `ERRORS`/`EXCEPTIONS` = 0). HTTP 200 alone is `unconfirmed`; the user must check the Day Book and resolve it.
* **Not verified against the official documentation:** the semantics of `REMOTEID`, the exact response tags (`CREATED`, `ERRORS`, `LASTVCHID`) across all TallyPrime releases, and the TDL ledger-collection request used by *Validate ledgers*. Test against your TallyPrime release with a test company first.
* JSON: TallyPrime 7.0 documents JSON integration, but the voucher JSON schema was not verified, so the option is disabled; XML is used.
* **Live Tally was not available during development;** connector behaviour was tested against a mock HTTP server only.
