# Global Supply Chain P&L – Power BI Web Application
**AICA Level 2 Capstone Project – Durgesh Singh**

## 1. Business problem
Supply Chain SPOCs at OpCo / Country level (Country SC Heads, IHM, Logistics, Quality, Sourcing and Operation Heads) have limited visibility of Supply Chain P&L KPIs. They have no ERP report access and don't want to navigate the ERP for routine monitoring. There is no standard global SC P&L dashboard, and Finance spends significant effort each month preparing and emailing country packs. Management needs one consistent monthly view of **Actual vs Budget vs Last Year** across regions, countries and OpCos.

## 2. Solution
A single, secure, web-based **Power BI App** that publishes standardised monthly Global SC P&L KPIs from the ERP to authorised users, with no manual dashboard preparation. It is a quick win that also lays the foundation for automation and advanced analytics.

**End-to-end flow:**
ERP → monthly extract → SharePoint folder → Power Automate → Power Query validation → Admin approval → semantic model refresh → Power BI App → monthly email → users (row-level security applied)

## 3. Key features
- **Automated ingestion:** a monthly extract file (`SCPL_YYYYMM_vN`) dropped in SharePoint triggers the whole process.
- **Data quality before publication:** 15 validation rules (missing file, wrong format, missing columns, duplicates, missing OpCo/country/month, invalid values or currency, refresh failure, KPI calculation errors). Critical errors stop publication, and warnings need Admin approval.
- **28 KPIs**, taken only from the KPI definition file:
  - Financial: Net Turnover SC, Gross Profit, Gross Margin %, EBITDA, EBIT and margins
  - Cost analytics: Freight, Factory and Channel cost per pair, Cost of Sales %, factory (under)/over recovery
  - Factory and sourcing: Factory Personnel %, Other Factory Cost %, PPV %, Import / Local Sourcing mix, average cost per pair
  - Volume: Purchase, Production and Total Pairs
- **Actual / Budget / LY** with variance vs Budget and vs LY, for Monthly, Quarterly and YTD, all in **USD**, with a Unit / Thousand / Million toggle.
- **Exception alerts** (traffic lights): GP margin decline >1%, EBITDA negative, freight increase >10%, PPV adverse >5%, recovery variance >10%.
- **Security by design:** dynamic row-level security driven by an Admin-maintained `User_Access` list, with no hard-coded users or countries. Each user sees only their assigned Region, OpCo and SC Function.
- **Roles:**
  - *Administrator (Global SC Finance Controller):* manages users and access, approves each month's publication, and monitors data quality and refresh.
  - *Viewers:* can view, filter, drill down, bookmark and export permitted data. They cannot change the model, KPIs, security or report design.
- **Monthly email** (Power Automate): reporting month, key highlights for the user's scope, app link, refresh time and a data-quality disclaimer.

## 4. Report pages
| Page | Purpose |
|---|---|
| Summary | Mirrors the template's Summary tab: filter pane plus Sections A–D (Financial, Volume, Cost Analytics, Factory & Sourcing) with 12 KPI cards (Monthly and YTD, vs Bud, vs LY) and an alert strip |
| Detailed P&L | Full P&L in template row order: Actual, Budget, LY, vs Bud %, vs LY %; Monthly / Quarterly / YTD |
| OpCo Performance | KPIs and traffic-light alerts by OpCo, with margin vs Budget ranking |
| Trend Analysis | Actual vs Budget vs LY by month; margin and cost-per-pair trends |
| KPI Glossary | Definitions and formulas from the KPI file |
| Data Quality (Admin) | Refresh status, reporting month, validation checklist, OpCo load status, exceptions and refresh history |

## 5. Data model
Star schema with `Fact_SC_PL` (month × OpCo × SC Function × Account × Scenario; Amount USD and Volume Pairs) and dimensions Date, OpCo (Region / Country / BU), SC Function, Account (P&L line / cost category) and Scenario. It also has a KPI catalogue, a P&L layout table, two calculation groups (Scenario comparison and Period), and admin tables (Publish Control, DQ Exceptions, Refresh Log, User Access).

## 6. Tools used
Power BI Desktop and Service (PBIP / TMDL, DAX, calculation groups, RLS, Apps), Power Query (M), Power BI Dataflows, SharePoint Online, Power Automate (flows, approvals, email), Microsoft Entra ID groups.

## 7. Folder contents
| File / folder | Description |
|---|---|
| `Global_SC_PL_PowerBI_Capstone_Design.docx` / `.pdf` | Full design document covering all 14 deliverables: business problem, architecture, data model, KPI framework and DAX, Power Query, dashboard design, access model, operating process and RACI, automation and email template, error handling, benefits, roadmap, assumptions and open questions |
| `PowerBI_Prototype/Global_SC_PL.pbip` | Working Power BI project (Power BI Project format) |
| `SC_PL_Prototype_Sample_Data.xlsx` | Sample data set: 19,008 fact rows (Jan-2025 to Aug-2026) plus all dimension, security and control tables |
| `SCPL_202608_v1_SAMPLE.csv` | One monthly extract in the proposed ERP format |
| `SC_PL_DAX_Measures.dax` | DAX library: measures, calculation groups, RLS, data-quality measures |
| `SC_PL_PowerQuery_M.pq` | Power Query M: ingestion, validation, transformation |
| `SC_PL_PowerBI_Theme.json` | Report theme matching the template colours |
| `images/` | Architecture diagram, star schema, and Summary / Data Quality page mockups |

## 8. How to run the prototype
1. Open `PowerBI_Prototype/Global_SC_PL.pbip` in Power BI Desktop.
2. The project expects this folder at `D:\DurgeshSingh-GlobalSupplyChainPL-PowerBI`. If you saved it somewhere else, go to **Home → Transform data → Edit parameters** and set `SampleDataFile` to the full path of `SC_PL_Prototype_Sample_Data.xlsx` in this folder.
3. Click **Refresh**.
4. To test security: **Modeling → View as → SC Viewer**, with Other user `bd.schead@company.example` (sees Bangladesh only).

## 9. Business benefits (estimated)
- About **48 hours per month** of Finance effort saved (about 576 hours per year) by removing manual pack preparation and distribution.
- Publication moves from about working day 8 to **working day 5**.
- One version of the truth across all OpCos, with audit trail, data-quality gate and controlled access.

## 10. Future roadmap
Automated variance analysis, AI-generated commentary, anomaly detection, forecasting, savings identification (gap to best-quartile cost per pair), natural-language Q&A, mobile layout, and direct ERP-to-Fabric integration.

## 11. Known limitations
- The Detailed P&L, OpCo Performance, Trend Analysis and KPI Glossary pages use a basic layout. Only Summary and Data Quality match the design mockups.
- `SC_PL_DAX_Measures.dax` doesn't include the measures added in the Power BI prototype (SVG card images, Unit/Thousand/Million toggle, Data Quality page measures). The full measure set is in the project's `_Measures` table.

> **Note:** all figures are sample / dummy data for **XYZ Ltd**, used only to illustrate structure. The benefit figures are estimates based on stated assumptions.
