"""Original educational summaries. Definitions are not forecasts or legal advice."""
import json

ARTICLES=[
 ("cpi","Consumer Price Index (CPI)","Inflation","Economic","CPI tracks changes in prices paid by consumers for a defined basket of goods and services. Basket coverage, weights and calculation methods depend on the publishing country. An index level and a percentage change are different measures.","Helps describe consumer-price inflation. Read the reference period, monthly/yearly basis and seasonal adjustment before comparing values.","Usually monthly; consult the country publisher",["https://www.bls.gov/cpi/questions-and-answers.htm"]),
 ("gdp","Gross Domestic Product (GDP)","GDP","Economic","GDP measures the value of final goods and services produced within an economy over a period. Nominal measures use current prices; real measures adjust for price changes. Growth rates may use different comparison periods.","Describes aggregate economic output. Preliminary estimates can be revised as information becomes available; do not mix annualized and non-annualized growth.","Country-specific; commonly quarterly and annual",["https://www.bea.gov/resources/learning-center/what-to-know-gdp"]),
 ("pmi","Purchasing Managers’ Index (PMI)","PMI","Economic","PMI is a survey-based measure of business conditions. A reading above or below 50 generally indicates expansion or contraction relative to the previous month for the measured activity. Manufacturing and services surveys are distinct.","Offers information about reported business conditions. Coverage, flash/final releases and licensed provider methodology matter.","Usually monthly",["https://www.spglobal.com/market-intelligence/en/solutions/products/resources/pmi-faq"]),
 ("economic","Economic releases and readings","Economic release","Economic","An economic release publishes a statistic for a specified reporting period. Previous, consensus, actual and revised readings describe different information and must remain separately labelled.","Compare like-for-like units and periods. Missing consensus does not mean zero. Source publication time may differ from a calendar’s planned release time.","As stated by the publishing authority",["https://docs.tradingeconomics.com/economic_calendar/country/"]),
 ("corporate","Understanding corporate disclosures","Corporate disclosure","Corporate","A corporate announcement records information disclosed by a listed issuer to an exchange. The filing title, company identity, publication date and original document establish what was disclosed. A later clarification may change the earlier record.","Read the filing to determine its subject and relevant dates. The application category is a navigation aid and does not establish investment consequences.","Event-driven",["https://www.nseindia.com/static/rss-feed"]),
 ("results","Financial results disclosures","Financial results","Corporate","This category groups issuer filings about periodic financial results. Reporting period, standalone/consolidated basis and the actual accompanying statements determine what can be compared.","A results-meeting announcement is not the results themselves. Use the original filing and retain subsequent corrections.","Periodic and event-driven",["https://www.nseindia.com/static/market-data/corporate-data-subscription"]),
 ("regulatory","Understanding regulatory notices","Regulatory notice","Regulatory","A notice communicates information issued by a regulator or exchange. Publication date, effective date and implementation deadlines serve different purposes. A consultation is a proposal and should not be treated as an enacted requirement.","Read the issuing authority’s full document, applicability clauses and subsequent amendments. This page does not determine legal obligations.","Event-driven",["https://www.sebi.gov.in/rss.html","https://www.sebi.gov.in/website-policy.html"]),
 ("policy","Monetary-policy publications","Monetary policy","Regulatory","This category groups monetary-policy announcements and related central-bank publications. A scheduled meeting, its decision and a subsequently published statement are distinguishable records.","Read the original central-bank publication for the decision, applicable date and context. A calendar classification does not predict a market reaction.","Published central-bank schedule and additional announcements",["https://www.rbi.org.in/Scripts/rss.aspx"]),
]


def seed_knowledge(db):
    for article in ARTICLES:
        db.execute("INSERT OR IGNORE INTO knowledge_articles VALUES(?,?,?,?,?,?,?,?,?)", (*article[:7],json.dumps(article[7]),"2026-11-13"))


def article_for(db,event):
    category=event.get("category","")
    title=event.get("title","").casefold()
    if "cpi" in title or "consumer price" in title:
        article_id="cpi"
    elif "gdp" in title:
        article_id="gdp"
    elif "pmi" in title:
        article_id="pmi"
    elif category=="Financial results":
        article_id="results"
    elif category=="Monetary policy":
        article_id="policy"
    else:
        article_id={"Economic":"economic","Corporate":"corporate","Regulatory":"regulatory"}.get(event["kind"],"economic")
    rows=db.rows("SELECT * FROM knowledge_articles WHERE id=?", (article_id,))
    return rows[0] if rows else None

