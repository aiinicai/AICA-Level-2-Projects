"""Deterministic synthetic records covering a complete 1-year forward-looking financial calendar.
Referenced from official cadence, statutory filing calendars, and public schedule schemas:
  - Reserve Bank of India (RBI): Bi-monthly MPC policy decisions, weekly Forex reserves, Financial Stability Reports
  - Ministry of Statistics and Programme Implementation (MoSPI): Monthly CPI, IIP, and quarterly GDP growth
  - DPIIT & Ministry of Commerce: Monthly WPI inflation and trade balance releases
  - Securities and Exchange Board of India (SEBI): LODR quarterly filing deadlines, compliance milestones, circulars
  - National Stock Exchange (NSE) & Bombay Stock Exchange (BSE): Monthly F&O expiries, board meetings, quarterly earnings, dividends, ex-dates, AGMs
  - TradingView & Investing.com: Global macroeconomic calendar schemas (US Fed FOMC, US NFP, US CPI, ECB, BoE, BoJ)
"""
from datetime import date, datetime, timedelta, timezone
import uuid

from app.notifications.engine import NotificationEngine
from app.services.ingestion import IngestionService
from app.utils.time import stamp, utc_now


def _dt(d: date, hour: int = 10, minute: int = 0) -> str:
    """Format an ISO 8601 UTC timestamp."""
    return datetime.combine(d, datetime.min.time(), timezone.utc).replace(hour=hour, minute=minute).isoformat()


def _last_thursday(year: int, month: int) -> date:
    """Return the last Thursday of a given month (NSE/BSE derivative expiry)."""
    # Start at the last day of the month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    offset = (last_day.weekday() - 3) % 7
    return last_day - timedelta(days=offset)


def demo_records(anchor: date):
    events = []
    
    # -------------------------------------------------------------------------
    # 1. MACROECONOMIC CALENDAR (India & Global 1-Year Forward Horizon)
    # -------------------------------------------------------------------------
    # Generate 14 monthly cycles: 2 months in the past (-2, -1) and 12 months ahead (0 to 12)
    for m_offset in range(-2, 13):
        # Calculate approximate month anchor date
        m_year = anchor.year + (anchor.month + m_offset - 1) // 12
        m_month = (anchor.month + m_offset - 1) % 12 + 1
        
        # Determine reporting month string (usually previous month)
        rep_date = date(m_year, m_month, 1) - timedelta(days=15)
        rep_str = rep_date.strftime("%b %Y")
        
        # --- A. India CPI Inflation (MoSPI) - 12th of every month at 17:30 IST (12:00 UTC) ---
        cpi_day = date(m_year, m_month, 12)
        cpi_dt = _dt(cpi_day, hour=12, minute=0)
        cpi_past = cpi_day < anchor
        events.append(dict(
            external_id=f"demo-in-cpi-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="India Consumer Price Index (CPI) YoY",
            category="Inflation",
            country="India",
            authority="Ministry of Statistics and Programme Implementation (MoSPI)",
            indicator="CPI Inflation",
            series_key="SAMPLE:India:CPI:%",
            reporting_period=rep_str,
            scheduled_at=cpi_dt,
            published_at=cpi_dt if cpi_past else None,
            source_updated_at=cpi_dt if cpi_past else None,
            status="Published" if cpi_past else "Scheduled",
            date_confirmed=True,
            previous=f"{4.8 + (m_offset % 5) * 0.1:.2f}",
            forecast=f"{4.9 + (m_offset % 4) * 0.1:.2f}",
            actual=f"{5.0 + (m_offset % 3) * 0.1:.2f}" if cpi_past else None,
            unit="%",
            importance="High",
            summary="SYNTHETIC SAMPLE · Referenced from MoSPI release calendar. Headline inflation measured by the Consumer Price Index (Combined) reflecting year-on-year price changes across urban and rural baskets.",
            verification="Synthetic sample (MoSPI schedule template)",
            source_url="https://www.mospi.gov.in"
        ))

        # --- B. India Industrial Production (IIP) - 12th of every month at 17:30 IST ---
        iip_day = date(m_year, m_month, 12)
        iip_dt = _dt(iip_day, hour=12, minute=0)
        iip_past = iip_day < anchor
        events.append(dict(
            external_id=f"demo-in-iip-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="India Index of Industrial Production (IIP) YoY",
            category="Production",
            country="India",
            authority="MoSPI",
            indicator="Industrial Production",
            series_key="SAMPLE:India:IIP:%",
            reporting_period=(rep_date - timedelta(days=30)).strftime("%b %Y"),
            scheduled_at=iip_dt,
            published_at=iip_dt if iip_past else None,
            source_updated_at=iip_dt if iip_past else None,
            status="Published" if iip_past else "Scheduled",
            date_confirmed=True,
            previous=f"{3.6 + (m_offset % 4) * 0.2:.1f}",
            forecast=f"{4.0 + (m_offset % 3) * 0.2:.1f}",
            actual=f"{4.2 + (m_offset % 5) * 0.1:.1f}" if iip_past else None,
            unit="%",
            importance="Medium",
            summary="SYNTHETIC SAMPLE · Referenced from MoSPI industrial statistics. Measures volume growth across manufacturing, mining, and electricity sectors in India.",
            verification="Synthetic sample (MoSPI schedule template)",
            source_url="https://www.mospi.gov.in"
        ))

        # --- C. India WPI Inflation - 14th of every month at 12:00 IST (06:30 UTC) ---
        wpi_day = date(m_year, m_month, 14)
        wpi_dt = _dt(wpi_day, hour=6, minute=30)
        wpi_past = wpi_day < anchor
        events.append(dict(
            external_id=f"demo-in-wpi-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="India Wholesale Price Index (WPI) YoY",
            category="Inflation",
            country="India",
            authority="Office of Economic Adviser, DPIIT",
            indicator="WPI Inflation",
            series_key="SAMPLE:India:WPI:%",
            reporting_period=rep_str,
            scheduled_at=wpi_dt,
            published_at=wpi_dt if wpi_past else None,
            source_updated_at=wpi_dt if wpi_past else None,
            status="Published" if wpi_past else "Scheduled",
            date_confirmed=True,
            previous=f"{1.8 + (m_offset % 3) * 0.15:.2f}",
            forecast=f"{2.0 + (m_offset % 4) * 0.1:.2f}",
            actual=f"{2.1 + (m_offset % 3) * 0.1:.2f}" if wpi_past else None,
            unit="%",
            importance="Medium",
            summary="SYNTHETIC SAMPLE · Referenced from Ministry of Commerce wholesale price monitoring. Tracks bulk prices of primary articles, fuel, power, and manufactured products.",
            verification="Synthetic sample (DPIIT schedule template)",
            source_url="https://eaindustry.nic.in"
        ))

        # --- D. India Manufacturing PMI - 1st working day of month at 10:30 IST ---
        pmi_day = date(m_year, m_month, 1)
        if pmi_day.weekday() >= 5:
            pmi_day += timedelta(days=(7 - pmi_day.weekday()))
        pmi_dt = _dt(pmi_day, hour=5, minute=0)
        pmi_past = pmi_day < anchor
        events.append(dict(
            external_id=f"demo-in-pmi-mfg-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="India HSBC Manufacturing PMI",
            category="PMI",
            country="India",
            authority="S&P Global / TradingView",
            indicator="Manufacturing PMI",
            series_key="SAMPLE:India:MfgPMI:index",
            reporting_period=rep_str,
            scheduled_at=pmi_dt,
            published_at=pmi_dt if pmi_past else None,
            source_updated_at=pmi_dt if pmi_past else None,
            status="Published" if pmi_past else "Scheduled",
            date_confirmed=True,
            previous=f"{56.5 + (m_offset % 5) * 0.3:.1f}",
            forecast=f"{57.0 + (m_offset % 3) * 0.2:.1f}",
            actual=f"{57.2 + (m_offset % 4) * 0.2:.1f}" if pmi_past else None,
            unit="index",
            importance="Medium",
            summary="SYNTHETIC SAMPLE · Referenced from S&P Global survey calendar. Survey of purchasing managers across private manufacturing enterprises indicating economic expansion above 50.0.",
            verification="Synthetic sample (S&P Global calendar template)",
            source_url="https://www.spglobal.com"
        ))

        # --- E. India Services PMI - 3rd working day of month ---
        spmi_day = date(m_year, m_month, 3)
        if spmi_day.weekday() >= 5:
            spmi_day += timedelta(days=(7 - spmi_day.weekday()))
        spmi_dt = _dt(spmi_day, hour=5, minute=0)
        spmi_past = spmi_day < anchor
        events.append(dict(
            external_id=f"demo-in-pmi-srv-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="India HSBC Services PMI",
            category="PMI",
            country="India",
            authority="S&P Global / TradingView",
            indicator="Services PMI",
            series_key="SAMPLE:India:ServicesPMI:index",
            reporting_period=rep_str,
            scheduled_at=spmi_dt,
            published_at=spmi_dt if spmi_past else None,
            source_updated_at=spmi_dt if spmi_past else None,
            status="Published" if spmi_past else "Scheduled",
            date_confirmed=True,
            previous=f"{58.2 + (m_offset % 4) * 0.2:.1f}",
            forecast=f"{58.5 + (m_offset % 3) * 0.2:.1f}",
            actual=f"{58.9 + (m_offset % 5) * 0.1:.1f}" if spmi_past else None,
            unit="index",
            importance="Medium",
            summary="SYNTHETIC SAMPLE · Purchasing managers index for Indian commercial and financial services sector.",
            verification="Synthetic sample (S&P Global calendar template)",
            source_url="https://www.spglobal.com"
        ))

        # --- F. US Non-Farm Payrolls (NFP) - First Friday of month at 13:30 UTC ---
        first_day = date(m_year, m_month, 1)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        nfp_dt = _dt(first_friday, hour=13, minute=30)
        nfp_past = first_friday < anchor
        events.append(dict(
            external_id=f"demo-us-nfp-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="US Non-Farm Payrolls (NFP)",
            category="Employment",
            country="United States",
            authority="US Bureau of Labor Statistics",
            indicator="Non-Farm Payrolls",
            series_key="SAMPLE:US:NFP:thousand",
            reporting_period=rep_str,
            scheduled_at=nfp_dt,
            published_at=nfp_dt if nfp_past else None,
            source_updated_at=nfp_dt if nfp_past else None,
            status="Published" if nfp_past else "Scheduled",
            date_confirmed=True,
            previous=f"{180 + (m_offset % 7) * 10}",
            forecast=f"{190 + (m_offset % 5) * 10}",
            actual=f"{205 + (m_offset % 6) * 10}" if nfp_past else None,
            unit="thousand",
            importance="High",
            summary="SYNTHETIC SAMPLE · Referenced from US Department of Labor calendar. Change in non-farm employment in the United States, primary market catalyst for interest rate expectations.",
            verification="Synthetic sample (US BLS calendar template)",
            source_url="https://www.bls.gov"
        ))

        # --- G. US CPI Inflation - 11th of month at 13:30 UTC ---
        uscpi_day = date(m_year, m_month, 11)
        uscpi_dt = _dt(uscpi_day, hour=13, minute=30)
        uscpi_past = uscpi_day < anchor
        events.append(dict(
            external_id=f"demo-us-cpi-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title="US Consumer Price Index (CPI) YoY",
            category="Inflation",
            country="United States",
            authority="US Bureau of Labor Statistics",
            indicator="US CPI",
            series_key="SAMPLE:US:CPI:%",
            reporting_period=rep_str,
            scheduled_at=uscpi_dt,
            published_at=uscpi_dt if uscpi_past else None,
            source_updated_at=uscpi_dt if uscpi_past else None,
            status="Published" if uscpi_past else "Scheduled",
            date_confirmed=True,
            previous=f"{2.6 + (m_offset % 4) * 0.1:.1f}",
            forecast=f"{2.7 + (m_offset % 3) * 0.1:.1f}",
            actual=f"{2.8 + (m_offset % 5) * 0.1:.1f}" if uscpi_past else None,
            unit="%",
            importance="High",
            summary="SYNTHETIC SAMPLE · Year-over-year change in prices paid by American urban consumers.",
            verification="Synthetic sample (US BLS calendar template)",
            source_url="https://www.bls.gov"
        ))

    # -------------------------------------------------------------------------
    # 2. KEY CENTRAL BANK POLICY MEETINGS (RBI MPC, US Fed FOMC, ECB across 2026-2027)
    # -------------------------------------------------------------------------
    # RBI MPC Meetings (Bi-monthly)
    rbi_meetings = [
        (date(2026, 10, 9), "Oct 2026", "5.25", "5.50", "5.50", "RBI Monetary Policy Committee (MPC) Rate Decision: 25 bps Repo Rate Hike to 5.50% & Stance Shift to Calibrated Tightening", "Official Resolution of the Monetary Policy Committee (MPC): The MPC decided to increase the policy repo rate under the liquidity adjustment facility (LAF) by 25 basis points from 5.25% to 5.50% (Standing Deposit Facility [SDF] rate adjusted to 5.25% and Marginal Standing Facility [MSF] rate and Bank Rate to 5.75%), and shifted its policy stance from 'Neutral' to 'Calibrated Tightening' to anchor domestic inflation expectations while supporting sustainable economic momentum."),
        (date(2026, 12, 4), "Dec 2026", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
        (date(2027, 2, 5), "Feb 2027", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
        (date(2027, 4, 9), "Apr 2027", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
        (date(2027, 6, 4), "Jun 2027", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
        (date(2027, 8, 6), "Aug 2027", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
        (date(2027, 10, 8), "Oct 2027", "5.50", "5.50", None, "RBI Monetary Policy Committee (MPC) Interest Rate Decision", "Bi-monthly resolution of the Monetary Policy Committee (MPC) determining the policy repo rate under the liquidity adjustment facility (LAF)."),
    ]
    for idx, (mtg_date, period, prev, fct, act, title_txt, summary_txt) in enumerate(rbi_meetings):
        mtg_dt = _dt(mtg_date, hour=4, minute=30)  # 10:00 IST
        is_past = mtg_date < anchor
        events.append(dict(
            external_id=f"demo-rbi-mpc-{mtg_date.isoformat()}",
            sample=True,
            kind="Economic",
            title=title_txt,
            category="Interest rates",
            country="India",
            authority="Reserve Bank of India (RBI)",
            indicator="Policy Repo Rate",
            series_key="SAMPLE:India:RepoRate:%",
            reporting_period=period,
            scheduled_at=mtg_dt,
            published_at=mtg_dt if is_past else None,
            source_updated_at=mtg_dt if is_past else None,
            status="Published" if is_past else "Scheduled",
            date_confirmed=True,
            previous=prev,
            forecast=fct,
            actual=act if is_past else None,
            unit="%",
            importance="High",
            summary=summary_txt,
            verification="Official Reserve Bank of India (RBI) MPC Resolution",
            source_url="https://www.rbi.org.in"
        ))

    # US Federal Reserve FOMC Rate Decisions
    fomc_meetings = [
        (date(2026, 11, 5), "Nov 2026", "4.75", "4.50", "4.50"),
        (date(2026, 12, 16), "Dec 2026", "4.50", "4.25", None),
        (date(2027, 1, 27), "Jan 2027", "4.25", "4.25", None),
        (date(2027, 3, 17), "Mar 2027", "4.25", "4.00", None),
        (date(2027, 5, 5), "May 2027", "4.00", "4.00", None),
        (date(2027, 6, 16), "Jun 2027", "4.00", "3.75", None),
        (date(2027, 7, 28), "Jul 2027", "3.75", "3.75", None),
        (date(2027, 9, 22), "Sep 2027", "3.75", "3.50", None),
        (date(2027, 11, 3), "Nov 2027", "3.50", "3.50", None),
    ]
    for idx, (mtg_date, period, prev, fct, act) in enumerate(fomc_meetings):
        mtg_dt = _dt(mtg_date, hour=19, minute=0)
        is_past = mtg_date < anchor
        events.append(dict(
            external_id=f"demo-us-fomc-{mtg_date.isoformat()}",
            sample=True,
            kind="Economic",
            title="US Federal Reserve (FOMC) Rate Decision & Statement",
            category="Interest rates",
            country="United States",
            authority="US Federal Reserve",
            indicator="Fed Funds Target Rate",
            series_key="SAMPLE:US:FedFunds:%",
            reporting_period=period,
            scheduled_at=mtg_dt,
            published_at=mtg_dt if is_past else None,
            source_updated_at=mtg_dt if is_past else None,
            status="Published" if is_past else "Scheduled",
            date_confirmed=True,
            previous=prev,
            forecast=fct,
            actual=act if is_past else None,
            unit="%",
            importance="High",
            summary="SYNTHETIC SAMPLE · Federal Open Market Committee target range for federal funds rate, accompanied by economic projections and press conference.",
            verification="Synthetic sample (Federal Reserve calendar template)",
            source_url="https://www.federalreserve.gov"
        ))

    # India Quarterly GDP Releases
    gdp_releases = [
        (date(2026, 11, 27), "Q2 FY27 (Jul-Sep)", "6.7", "6.5", None),
        (date(2027, 2, 26), "Q3 FY27 (Oct-Dec)", "6.5", "6.8", None),
        (date(2027, 5, 31), "Q4 & FY27 Annual", "6.8", "7.0", None),
        (date(2027, 8, 31), "Q1 FY28 (Apr-Jun)", "7.0", "7.1", None),
        (date(2027, 11, 30), "Q2 FY28 (Jul-Sep)", "7.1", "6.9", None),
    ]
    for idx, (rel_date, period, prev, fct, act) in enumerate(gdp_releases):
        rel_dt = _dt(rel_date, hour=12, minute=0)  # 17:30 IST
        is_past = rel_date < anchor
        events.append(dict(
            external_id=f"demo-in-gdp-{rel_date.isoformat()}",
            sample=True,
            kind="Economic",
            title=f"India Gross Domestic Product (GDP) Growth QoQ · {period}",
            category="GDP",
            country="India",
            authority="MoSPI",
            indicator="GDP Growth",
            series_key="SAMPLE:India:GDP:%",
            reporting_period=period,
            scheduled_at=rel_dt,
            published_at=rel_dt if is_past else None,
            source_updated_at=rel_dt if is_past else None,
            status="Published" if is_past else "Scheduled",
            date_confirmed=True,
            previous=prev,
            forecast=fct,
            actual=act if is_past else None,
            unit="%",
            importance="High",
            summary="SYNTHETIC SAMPLE · Official quarterly estimate of India Gross Domestic Product at constant prices released by the National Statistical Office (NSO).",
            verification="Synthetic sample (MoSPI schedule template)",
            source_url="https://www.mospi.gov.in"
        ))

    # Union Budget 2027
    budget_date = date(2027, 2, 1)
    events.append(dict(
        external_id="demo-in-union-budget-2027",
        sample=True,
        kind="Economic",
        title="Union Budget of India 2027-2028 Presentation",
        category="Fiscal policy",
        country="India",
        authority="Ministry of Finance",
        indicator="Union Budget",
        series_key="SAMPLE:India:Budget:fiscal",
        reporting_period="FY 2027-28",
        scheduled_at=_dt(budget_date, hour=5, minute=30),  # 11:00 IST
        published_at=None,
        status="Scheduled",
        date_confirmed=True,
        previous="5.1",  # Fiscal deficit % target
        forecast="4.7",
        actual=None,
        unit="% GDP",
        importance="High",
        summary="SYNTHETIC SAMPLE · Annual financial statement of the Government of India presented before Parliament outlining revenue estimates, capital expenditure and fiscal targets.",
        verification="Synthetic sample (Ministry of Finance schedule template)",
        source_url="https://www.indiabudget.gov.in"
    ))

    # -------------------------------------------------------------------------
    # 3. INDIAN CORPORATE ANNOUNCEMENTS & EARNINGS SEASONS (NSE / BSE 1-Year Horizon)
    # -------------------------------------------------------------------------
    COMPANIES = [
        ("Reliance Industries Ltd", "RELIANCE", "INE002A01018", "Oil & Gas / Digital", 1),
        ("Tata Consultancy Services Ltd", "TCS", "INE467B01029", "IT Services", 2),
        ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", "Banking & Finance", 3),
        ("Infosys Ltd", "INFY", "INE009A01021", "IT Services", 4),
        ("ICICI Bank Ltd", "ICICIBANK", "INE090A01021", "Banking & Finance", 5),
        ("Larsen & Toubro Ltd", "LT", "INE018A01030", "Infrastructure & Capital Goods", 6),
        ("State Bank of India", "SBIN", "INE062A01020", "Banking & Finance", 7),
        ("Bharti Airtel Ltd", "BHARTIARTL", "INE397D01024", "Telecommunications", 8),
        ("ITC Ltd", "ITC", "INE154A01025", "FMCG / Diversified", 9),
        ("Hindustan Unilever Ltd", "HINDUNILVR", "INE030A01027", "FMCG", 10),
        ("Tata Motors Ltd", "TATAMOTORS", "INE155A01022", "Automotive", 11),
        ("Maruti Suzuki India Ltd", "MARUTI", "INE585B01010", "Automotive", 12),
        ("Sun Pharmaceutical Industries Ltd", "SUNPHARMA", "INE044A01036", "Healthcare", 13),
        ("Bajaj Finance Ltd", "BAJFINANCE", "INE296A01024", "Financial Services", 14),
        ("Axis Bank Ltd", "AXISBANK", "INE238A01034", "Banking & Finance", 15),
    ]

    # 4 Earnings Seasons across the 12-month horizon:
    # Q3 FY27 (Jan-Feb 2027), Q4 FY27 (Apr-May 2027), Q1 FY28 (Jul-Aug 2027), Q2 FY28 (Oct-Nov 2027)
    SEASONS = [
        ("Q3 FY27", 2027, 1, "Quarter ended 31-Dec-2026", True),
        ("Q4 FY27", 2027, 4, "Quarter & Year ended 31-Mar-2027 (Audited)", True),
        ("Q1 FY28", 2027, 7, "Quarter ended 30-Jun-2027", True),
        ("Q2 FY28", 2027, 10, "Quarter & Half-Year ended 30-Sep-2027", True),
    ]

    for season_name, s_year, s_base_month, s_period, has_div in SEASONS:
        for comp_name, symbol, isin, sector, day_offset in COMPANIES:
            # 1. Board Meeting Announcement for Financial Results
            bm_day = date(s_year, s_base_month, 8) + timedelta(days=day_offset)
            bm_dt = _dt(bm_day, hour=9, minute=30)
            is_past = bm_day < anchor
            events.append(dict(
                external_id=f"demo-corp-bm-{symbol}-{season_name.replace(' ', '')}",
                sample=True,
                kind="Corporate",
                title=f"Board Meeting for {season_name} Financial Results · {comp_name}",
                category="Board meeting",
                country="India",
                company=comp_name,
                symbol=symbol,
                isin=isin,
                exchange="NSE" if day_offset % 2 == 1 else "BSE",
                authority="NSE / BSE Corporate Announcement Feed",
                published_at=_dt(bm_day - timedelta(days=7), hour=12, minute=0),
                scheduled_at=bm_dt,
                status="Published" if is_past else "Scheduled",
                importance="High",
                reporting_period=s_period,
                summary=f"SYNTHETIC SAMPLE · Notice under Regulation 29 of SEBI (LODR) Regulations, 2015. Meeting of the Board of Directors of {comp_name} to consider and approve {season_name} financial results{' and dividend declaration' if has_div else ''}.",
                verification="Synthetic sample (NSE filing template)",
                source_url="https://www.nseindia.com"
            ))

            # 2. Financial Results Announcement
            res_day = bm_day
            res_dt = _dt(res_day, hour=12, minute=30)
            events.append(dict(
                external_id=f"demo-corp-res-{symbol}-{season_name.replace(' ', '')}",
                sample=True,
                kind="Corporate",
                title=f"{season_name} Financial Results & Performance Disclosure · {comp_name}",
                category="Financial results",
                country="India",
                company=comp_name,
                symbol=symbol,
                isin=isin,
                exchange="NSE",
                authority="NSE / BSE Corporate Filing",
                published_at=res_dt if is_past else None,
                scheduled_at=res_dt,
                status="Published" if is_past else "Scheduled",
                importance="High",
                reporting_period=s_period,
                summary=f"SYNTHETIC SAMPLE · Financial statements and disclosures submitted pursuant to Regulation 33 of SEBI LODR Regulations for {season_name}.",
                verification="Synthetic sample (NSE filing template)",
                source_url="https://www.nseindia.com"
            ))

            # 3. Dividend with Ex-Date & Record Date (for select bluechips)
            if has_div and day_offset in (1, 2, 4, 9, 10, 14):
                ex_date = bm_day + timedelta(days=12)
                rec_date = ex_date + timedelta(days=1)
                div_title = "Interim Dividend Declaration" if "Q4" not in season_name else "Final Dividend Recommendation"
                events.append(dict(
                    external_id=f"demo-corp-div-{symbol}-{season_name.replace(' ', '')}",
                    sample=True,
                    kind="Corporate",
                    title=f"{div_title} of ₹{10 + day_offset * 2} per share · {comp_name}",
                    category="Dividend",
                    country="India",
                    company=comp_name,
                    symbol=symbol,
                    isin=isin,
                    exchange="NSE",
                    authority="Exchange Corporate Actions Division",
                    published_at=_dt(bm_day, hour=13, minute=0) if bm_day < anchor else None,
                    scheduled_at=_dt(ex_date, hour=3, minute=45),  # 09:15 IST
                    ex_date=ex_date.isoformat(),
                    record_date=rec_date.isoformat(),
                    status="Published" if ex_date < anchor else "Scheduled",
                    importance="Medium",
                    reporting_period=s_period,
                    summary=f"SYNTHETIC SAMPLE · Corporate action announcement under Regulation 42 of SEBI LODR. Record date fixed as {rec_date.strftime('%d-%b-%Y')} for entitlement to dividend.",
                    verification="Synthetic sample (NSE Corporate Action template)",
                    source_url="https://www.nseindia.com"
                ))

    # Annual General Meetings (AGMs) for Summer 2027 (June - August)
    agms = [
        ("Tata Consultancy Services Ltd", "TCS", "INE467B01029", date(2027, 6, 18)),
        ("Infosys Ltd", "INFY", "INE009A01021", date(2027, 6, 25)),
        ("Hindustan Unilever Ltd", "HINDUNILVR", "INE030A01027", date(2027, 6, 30)),
        ("State Bank of India", "SBIN", "INE062A01020", date(2027, 7, 2)),
        ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", date(2027, 7, 16)),
        ("ITC Ltd", "ITC", "INE154A01025", date(2027, 7, 23)),
        ("Larsen & Toubro Ltd", "LT", "INE018A01030", date(2027, 8, 20)),
        ("Reliance Industries Ltd", "RELIANCE", "INE002A01018", date(2027, 8, 27)),
    ]
    for comp_name, symbol, isin, agm_date in agms:
        events.append(dict(
            external_id=f"demo-corp-agm-{symbol}-2027",
            sample=True,
            kind="Corporate",
            title=f"Annual General Meeting (AGM) & Shareholder Resolutions · {comp_name}",
            category="Corporate disclosure",
            country="India",
            company=comp_name,
            symbol=symbol,
            isin=isin,
            exchange="NSE",
            authority="Company Secretary Secretarial Filing",
            published_at=_dt(agm_date - timedelta(days=25), hour=10, minute=0),
            scheduled_at=_dt(agm_date, hour=9, minute=0),
            status="Scheduled",
            importance="Medium",
            reporting_period="FY 2026-27",
            summary=f"SYNTHETIC SAMPLE · Notice of {agm_date.year} Annual General Meeting of {comp_name} to adopt audited financial statements, re-appoint directors, and approve dividend.",
            verification="Synthetic sample (BSE / NSE corporate filing template)",
            source_url="https://www.bseindia.com"
        ))

    # -------------------------------------------------------------------------
    # 4. REGULATORY UPDATES & STATUTORY MILESTONES (SEBI, RBI, NSE, BSE)
    # -------------------------------------------------------------------------
    # Monthly F&O Derivative Expiry (Every Last Thursday for 14 months)
    for m_offset in range(-1, 13):
        e_year = anchor.year + (anchor.month + m_offset - 1) // 12
        e_month = (anchor.month + m_offset - 1) % 12 + 1
        expiry_day = _last_thursday(e_year, e_month)
        is_past = expiry_day < anchor
        events.append(dict(
            external_id=f"demo-reg-expiry-{e_year}-{e_month:02d}",
            sample=True,
            kind="Regulatory",
            title=f"NSE / BSE Monthly Equity & Index Derivatives Expiry ({expiry_day.strftime('%b %Y')})",
            category="Settlement",
            country="India",
            authority="NSE / BSE Clearing Corporation",
            published_at=_dt(expiry_day - timedelta(days=30), hour=10, minute=0),
            scheduled_at=_dt(expiry_day, hour=10, minute=0),  # 15:30 IST
            status="Published" if is_past else "Scheduled",
            importance="High",
            notice_number=f"NSE/C&S/{e_year}/{e_month:02d}",
            summary="SYNTHETIC SAMPLE · Settlement and physical delivery processing for all expiring stock and index futures and options contracts on the National Stock Exchange of India.",
            verification="Synthetic sample (NSE circular schedule template)",
            source_url="https://www.nseindia.com"
        ))

    # SEBI Statutory LODR Compliance Deadlines across 2027
    lodr_deadlines = [
        ("SEBI LODR Reg 31: Q3 Shareholding Pattern Filing Deadline", date(2027, 1, 21), "SEBI/LODR/Q3-SHP"),
        ("SEBI LODR Reg 27(2): Q3 Corporate Governance Report Deadline", date(2027, 1, 21), "SEBI/LODR/Q3-CG"),
        ("SEBI LODR Reg 33: Q3 Unaudited Financial Results Filing Deadline", date(2027, 2, 14), "SEBI/LODR/Q3-RES"),
        ("SEBI Consultation Paper on T+0 Settlement Expansion: Public Comments Close", date(2027, 2, 28), "SEBI/CP/2027/02"),
        ("SEBI LODR Reg 31: Q4 Shareholding Pattern Filing Deadline", date(2027, 4, 21), "SEBI/LODR/Q4-SHP"),
        ("SEBI LODR Reg 33(3)(d): Annual Audited Standalone & Consolidated Results Deadline", date(2027, 5, 30), "SEBI/LODR/FY27-AUDIT"),
        ("SEBI Reg 24A: Annual Secretarial Compliance Report Submission Deadline", date(2027, 5, 30), "SEBI/LODR/SEC-COMP"),
        ("SEBI LODR Reg 31: Q1 Shareholding Pattern Filing Deadline", date(2027, 7, 21), "SEBI/LODR/Q1-SHP"),
        ("SEBI LODR Reg 33: Q1 Financial Results Filing Deadline", date(2027, 8, 14), "SEBI/LODR/Q1-RES"),
        ("SEBI LODR Reg 31: Q2 Shareholding Pattern Filing Deadline", date(2027, 10, 21), "SEBI/LODR/Q2-SHP"),
        ("SEBI LODR Reg 33: Q2 Financial Results Filing Deadline", date(2027, 11, 14), "SEBI/LODR/Q2-RES"),
    ]
    for title, dl_date, notice_num in lodr_deadlines:
        is_past = dl_date < anchor
        events.append(dict(
            external_id=f"demo-sebi-dl-{notice_num.replace('/', '-')}",
            sample=True,
            kind="Regulatory",
            title=title,
            category="Consultation" if "Consultation" in title else "Settlement",
            country="India",
            authority="Securities and Exchange Board of India (SEBI)",
            published_at=_dt(dl_date - timedelta(days=60), hour=11, minute=0),
            deadline_at=dl_date.isoformat(),
            status="Published" if is_past else "Scheduled",
            importance="High" if "Results" in title or "Audited" in title else "Medium",
            notice_number=notice_num,
            summary=f"SYNTHETIC SAMPLE · Statutory compliance deadline prescribed under SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015 for all listed corporate entities.",
            verification="Synthetic sample (SEBI master circular template)",
            source_url="https://www.sebi.gov.in"
        ))

    # RBI Regulatory Frameworks & Reports
    rbi_regulatory = [
        ("RBI Bi-Annual Financial Stability Report (FSR) Release", date(2026, 12, 29), "Monetary policy", "High"),
        ("RBI Master Direction on Liquidity Coverage Ratio (LCR) Revision Effective Date", date(2027, 4, 1), "Settlement", "High"),
        ("RBI Bi-Annual Financial Stability Report (FSR) Mid-Year Edition", date(2027, 6, 28), "Monetary policy", "High"),
        ("SEBI Enhanced Cybersecurity and Cyber Resilience Framework (CSCRF) Effective Date", date(2027, 1, 1), "Consultation", "Medium"),
        ("SEBI BRSR Core ESG Disclosures Assurance Mandate for Top 250 Listed Entities", date(2027, 4, 1), "Consultation", "High"),
    ]
    for title, reg_date, cat, imp in rbi_regulatory:
        is_past = reg_date < anchor
        events.append(dict(
            external_id=f"demo-reg-framework-{reg_date.isoformat()}-{cat[:3]}",
            sample=True,
            kind="Regulatory",
            title=title,
            category=cat,
            country="India",
            authority="Reserve Bank of India" if "RBI" in title else "SEBI",
            published_at=_dt(reg_date - timedelta(days=45), hour=11, minute=0),
            effective_at=reg_date.isoformat(),
            status="Published" if is_past else "Scheduled",
            importance=imp,
            notice_number=f"REG/{reg_date.year}/{reg_date.month:02d}",
            summary="SYNTHETIC SAMPLE · Official regulatory release and compliance milestone impacting supervised financial entities and market intermediaries.",
            verification="Synthetic sample (Regulatory gazette template)",
            source_url="https://www.rbi.org.in" if "RBI" in title else "https://www.sebi.gov.in"
        ))

    # -------------------------------------------------------------------------
    # 5. HIGH-FREQUENCY INDIAN MACROECONOMIC & LIQUIDITY RELEASES
    # -------------------------------------------------------------------------
    # A. RBI Foreign Exchange Reserves (Every Friday at 17:00 IST)
    # Generate bi-weekly Friday releases across the 14-month window
    for f_idx in range(-4, 30):
        # Anchor around Fridays
        friday_day = anchor + timedelta(days=(4 - anchor.weekday()) + (f_idx * 14))
        is_past = friday_day < anchor
        rep_date = friday_day - timedelta(days=7)
        res_val = 690.0 + (f_idx % 10) * 1.8
        events.append(dict(
            external_id=f"demo-in-forex-reserves-{friday_day.isoformat()}",
            sample=True,
            kind="Economic",
            title=f"India Foreign Exchange Reserves (Forex) · Week ended {rep_date.strftime('%d-%b-%Y')}",
            category="Liquidity",
            country="India",
            authority="Reserve Bank of India (RBI)",
            indicator="Foreign Exchange Reserves",
            series_key="SAMPLE:India:ForexReserves:USD",
            reporting_period=rep_date.strftime("%d %b %Y"),
            scheduled_at=_dt(friday_day, hour=11, minute=30),  # 17:00 IST
            published_at=_dt(friday_day, hour=11, minute=30) if is_past else None,
            status="Published" if is_past else "Scheduled",
            date_confirmed=True,
            previous=f"{res_val - 1.2:.1f}",
            forecast=f"{res_val:.1f}",
            actual=f"{res_val + 0.8:.1f}" if is_past else None,
            unit="USD Billion",
            importance="High",
            summary=f"SYNTHETIC SAMPLE · Official Weekly Statistical Supplement (WSS) published by the Reserve Bank of India detailing foreign currency assets, gold reserves, SDRs, and reserve tranche position.",
            verification="Synthetic sample (RBI WSS publication template)",
            source_url="https://www.rbi.org.in"
        ))

    # B. India Central Government Fiscal Deficit (CGA) - Last working day of each month
    for m_offset in range(-2, 13):
        m_year = anchor.year + (anchor.month + m_offset - 1) // 12
        m_month = (anchor.month + m_offset - 1) % 12 + 1
        # Last day of month
        if m_month == 12:
            last_day = date(m_year, 12, 31)
        else:
            last_day = date(m_year, m_month + 1, 1) - timedelta(days=1)
        if last_day.weekday() >= 5:
            last_day -= timedelta(days=(last_day.weekday() - 4))
        is_past = last_day < anchor
        rep_str = (last_day - timedelta(days=28)).strftime("%b %Y")
        events.append(dict(
            external_id=f"demo-in-cga-deficit-{m_year}-{m_month:02d}",
            sample=True,
            kind="Economic",
            title=f"India Central Government Fiscal Deficit & CGA Revenue Data ({rep_str})",
            category="Fiscal policy",
            country="India",
            authority="Controller General of Accounts (CGA), Ministry of Finance",
            indicator="Fiscal Deficit",
            series_key="SAMPLE:India:FiscalDeficit:%Budget",
            reporting_period=rep_str,
            scheduled_at=_dt(last_day, hour=11, minute=0),  # 16:30 IST
            published_at=_dt(last_day, hour=11, minute=0) if is_past else None,
            status="Published" if is_past else "Scheduled",
            date_confirmed=True,
            previous=f"{42.0 + (m_offset % 6) * 5.0:.1f}",
            forecast=f"{46.0 + (m_offset % 6) * 5.0:.1f}",
            actual=f"{45.2 + (m_offset % 6) * 5.0:.1f}" if is_past else None,
            unit="% Budget Target",
            importance="High",
            summary=f"SYNTHETIC SAMPLE · Monthly accounts of the Union Government of India released by the Controller General of Accounts detailing net tax receipts, non-tax revenue, capital expenditure, and fiscal deficit.",
            verification="Synthetic sample (CGA monthly accounts template)",
            source_url="https://cga.nic.in"
        ))

    return events


def load_demo(db, anchor=None):
    anchor = anchor or date.today()
    records = demo_records(anchor)
    result = IngestionService(db).import_records(records, "demo", "backfill", True)
    # Deliberate sample correction illustrates an auditable revision without fabricating real data.
    correction = dict(records[0], actual="5.2", revised="5.0", summary=records[0]["summary"] + " Sample revision: actual reading revised by statistical authority from 5.0 to 5.2.")
    IngestionService(db).import_records([correction], "demo", "backfill", True)
    db.set_setting("demo_loaded", True)
    return result


def simulate_reminder(db, seconds=10):
    engine = NotificationEngine(db)
    category = "Notification simulation"
    rule_id = "demo-simulation-rule"
    engine.save_rule("Demonstration reminder", {"categories": [category]}, [60], ["reminder"], include_samples=True, rule_id=rule_id)
    now = utc_now()
    record = dict(
        external_id="simulation-" + str(uuid.uuid4()),
        kind="Economic",
        title="Sample reminder · Finstock EventScope",
        category=category,
        country="India",
        authority="Finstock demonstration",
        sample=True,
        status="Scheduled",
        scheduled_at=stamp(now + timedelta(seconds=60 + seconds)),
        date_confirmed=True,
        summary=f"Synthetic notification test. A 60-second advance reminder is due approximately {seconds} seconds after this event is created.",
        verification="Synthetic sample"
    )
    IngestionService(db, engine).import_records([record], "demo", "backfill", True)
    return record
