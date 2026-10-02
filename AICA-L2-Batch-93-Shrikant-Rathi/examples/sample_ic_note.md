# Investment-committee note: is the family over-exposed to HDFC Bank?

*Drafted by Claude using the LookThrough MCP tools, and checked by `verify_note` before it was presented. Valuation date 31-Aug-2026. Dummy family, real market data.*

## 1. Question and scope
Whole family (all five entities). Direct holdings plus holdings through mutual funds, looked through to the underlying stocks.

## 2. Key facts
- [CALC] HDFC Bank is the largest look-through exposure: Rs 5.71 cr, or 12.56% of look-through equity (look_through_exposure).
- [CALC] Of that, Rs 3.84 cr is held directly and Rs 1.87 cr through mutual funds (look_through_exposure).
- [CALC] Look-through equity totals Rs 45.5 cr across 501 companies. Every held fund's portfolio disclosure is loaded, so no fund value is left un-looked-through (portfolio_summary).
- [CALC] Financial Services is 33.39% of equity, against a sector limit of 30% (policy_check).
- [CALC] ICICI Prudential Large Cap and Nippon India Large Cap overlap by 54.56%, against a limit of 50%. They share 38 stocks, and their monthly returns have a correlation of 0.976 (fund_overlap; limit from policy_check).
- [CALC] The UTI Nifty 50 Index Fund overlaps 63.95% with ICICI Prudential Large Cap and 61.02% with Nippon India Large Cap (policy_check).
- [FACT] HDFC Bank's price fell 25.49% over one year (company_report).

## 3. Analysis
- [CALC] The single-stock test is breached: 12.56% against a limit of 10% (policy_check).
- [VIEW] Most of the excess comes from the direct holding (Rs 3.84 cr). Trimming the direct position would therefore close the breach without changing the fund line-up.
- [VIEW] Two active large-cap funds and a Nifty 50 index fund hold largely the same stocks, HDFC Bank included, so part of the fund-route exposure is paid for more than once.

## 4. Policy position
Two breaches and three warnings (policy_check). Breaches: single stock (HDFC Bank 12.56% vs 10%) and sector (Financial Services 33.39% vs 30%). Warnings: three fund-overlap pairs above the 50% limit (ICICI Prudential Large Cap and Nippon India Large Cap 54.56%, ICICI Prudential Large Cap and UTI Nifty 50 Index 63.95%, Nippon India Large Cap and UTI Nifty 50 Index 61.02%), each meaning two expense ratios are paid for largely the same stocks. The weighted expense ratio test is NOT COMPUTABLE because expense ratios have not yet been loaded.

## 5. Risks and what would change the view
- [CALC] A 20% market fall would reduce equity by an estimated Rs 8.74 cr, or 19.21% of Rs 45.5 cr, at a portfolio beta of 0.96 (stress_test). [ASSUMPTION] Stocks without enough price history are taken to move with the market (beta 1).
- [VIEW] The conclusion would change if the committee raised the single-stock limit, or if the funds cut their HDFC Bank weights in the next monthly disclosures.
- [FACT] HDFC Bank's ROE is 14.14% and its P/B is 1.96 (company_report). Both rest on the bank's own audited standalone profit and net worth, which replaced a secondary-source net worth that was overstated (company_report caveat).

## 6. Options for the committee (no recommendation)
1. Reduce the direct HDFC Bank holding until look-through exposure is within the limit, after checking each entity's tax_position for the capital-gains cost.
2. Consolidate the large-cap exposure (two active large-cap funds and a Nifty 50 index fund), which cuts the three overlaps and the duplicated HDFC Bank exposure.
3. Record a time-bound policy exception, with the reason minuted.

## 7. Data limitations
Benchmarks are price indices, not total-return indices. The Nifty Smallcap benchmark is substituted by the Nifty 500. Company statements are from Yahoo Finance and have not been verified against annual reports, except HDFC Bank's profit, net worth, total assets and borrowings, which are its audited standalone figures (company_report). Fund look-through uses each AMC's month-end disclosure, so it does not show trades made since 31 August (data_provenance).

---
**verify_note: passed.** Every figure in this note traces to a tool output from the same session (see `sample_ic_note.verify.json`).
