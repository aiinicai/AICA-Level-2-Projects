import os
import tempfile
import unittest
import math
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

TEMP=tempfile.TemporaryDirectory()
os.environ['IPO_COMPASS_DATA_DIR']=TEMP.name
from app import db,scoring
from app.scrapers import base,nse,bse
from app.research import parse_statements,enrich_record
from app.refresh import run_refresh
from app.report import make_report
from app.prospectus import parse_mixed_page, parse_valuation_and_concentration
from app.research import derive,combine
from app.research import parse_chittorgarh_kpi

class CoreTests(unittest.TestCase):
    def setUp(self):
        db.init_db()
        for r in db.all_ipos():db.delete_ipo(r['id'])
    def test_scoring_missing_periods(self):
        self.assertIsNone(scoring.last([20,30,None]))
        self.assertIsNone(scoring.previous([20,None,40]))
        self.assertIsNone(scoring.total([20,None,40]))
        self.assertAlmostEqual(scoring.cagr([100,None,144]),20)
        self.assertIsNone(scoring.working_score({'inv_days':30}))
        self.assertIsNone(scoring.analyse(db.ensure_record({'cfo':[5,6,7],'pat':[5,6,None]}))['ratio'])
        self.assertIsNone(scoring.cash_score(-5,10,None,None,None))
    def test_score_gates(self):
        r=db.ensure_record({'name':'A','business_score':10,'anchor':10,'liquidity':10,'revenue':[10,20,30],'pat':[2,4,6],'ebitda':[4,8,12],'sub_qib':100,'sub_nii':100,'gmp_pct':50,'gmp_trend':'Rising','de':0,'pe':10,'peer_pe':20,'roe':30,'top_cust':10,'fresh':100,'issue_size':100})
        self.assertGreater(scoring.analyse(r)['coverage'],60)
        self.assertEqual(scoring.analyse(r)['auto'],'Research needed')
    def test_parsers(self):
        self.assertEqual(base.number_text('(1,234.5)'),-1234.5)
        self.assertEqual(base.normalize_status('Forthcoming'),'Upcoming')
        self.assertEqual(base.rows_to_records([['Metric','2025'],['Profit',10]]),[])
        r=base.rows_to_records([['IPO Name','GMP %','Issue Size (Shares)'],['ABC Limited','10','100000']])[0]
        self.assertNotIn('gmp_amount',r); self.assertNotIn('issue_size',r)
        r=nse.map_rows([{'companyName':'ABC Limited','issuePrice':'Rs.40 to Rs.43','noOfTime':'0','issueSize':'1000000','status':'Active'}],'Open')[0]
        self.assertEqual(r['price_high'],43);self.assertEqual(r['sub_total'],0);self.assertNotIn('issue_size',r)
        self.assertEqual(bse.parse_api({'Table':[{'Scrip_Name':'ABC','IR_FLAG_FULL':'RI'}]}),[])
        self.assertIsNone(bse.parse_api({'Table':[{'Scrip_Name':'ABC','IR_FLAG_FULL':'IPO','Price_Band':'100 - 120'}]})[0]['sub_total'])
    def test_migration_adds_every_new_column_to_a_pre_existing_database(self):
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH)
        conn.execute('DROP TABLE ipos')
        conn.execute('''CREATE TABLE ipos (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, symbol TEXT, exchange TEXT, board TEXT, status TEXT,
            sector TEXT, location TEXT, open_date TEXT, close_date TEXT, listing_date TEXT,
            price_low REAL, price_high REAL, lot INTEGER, sme_lots INTEGER,
            issue_size REAL, fresh REAL, ofs REAL, market_cap REAL,
            years TEXT, revenue TEXT, ebitda TEXT, pat TEXT, cfo TEXT, fcf TEXT,
            de REAL, post_de REAL, roe REAL, roce REAL, pe REAL, peer_pe REAL,
            inv_days REAL, deb_days REAL, cred_days REAL, top_cust REAL, top_supp REAL, business_score REAL,
            anchor REAL, liquidity REAL, sub_total REAL, sub_qib REAL, sub_nii REAL, sub_shni REAL, sub_bhni REAL,
            sub_retail REAL, sub_retail_apps REAL, sub_shni_apps REAL, sub_bhni_apps REAL,
            gmp_amount REAL, gmp_pct REAL, gmp_trend TEXT, gmp_at TEXT,
            override_verdict TEXT, override_reason TEXT, notes TEXT, updated_at TEXT
        )''')
        conn.execute("INSERT INTO ipos (id,name,updated_at) VALUES ('pre-existing','Old Record','2026-01-01')")
        conn.commit();conn.close()
        db.init_db()
        r = db.get('pre-existing')
        for field in ('promoter_pledge','net_worth','net_worth_previous','borrowings','cutoff_price',
                      'sub_qib_anchor','ipo_debt_repayment','post_issue_eps','post_issue_shares',
                      'wc_days_change','key_risks','business_description'):
            r[field] = 1
            db.upsert_ipo(r)  # must not raise "no such column"
        self.assertEqual(db.get('pre-existing')['promoter_pledge'], 1)

    def test_database_merge(self):
        def put(r,src='nse',official=True):return db.merge_incoming(r,src,src,'https://example.com','test',official)
        a=put({'name':'ABC India Limited','open_date':'11-Sep-2026','board':'SME','price_high':100,'sub_total':0})
        b=put({'name':'ABC Limited','open_date':'11-Sep-2026'})
        # "India" / "Limited" are naming noise between websites, not identity,
        # so these are one IPO (unrelated companies that only share a generic
        # first word are still kept apart - see the Om Galaxy / Om Industries
        # check in test_duplicate_short_vs_full_legal_name_are_merged).
        self.assertEqual(a,b)
        self.assertEqual(put({'name':'ABC India Ltd','open_date':'2026-09-11','price_high':900},'moneycontrol',False),a)
        self.assertEqual(db.get(a)['price_high'],100);self.assertEqual(db.get(a)['board'],'SME')
        self.assertEqual(db.get(a)['sub_total'],0)
        c=put({'name':'ABC India Limited','open_date':'2027-09-11','exchange':'BSE'})
        self.assertEqual(a,c)
        put({'name':'Research Limited','cfo':[None,None,None]},'manual',False)
        rid=put({'name':'Research Limited','cfo':[1,2,3]},'ipo360',False)
        self.assertEqual(db.get(rid)['cfo'],[1,2,3])
        put({'name':'Research Limited','cfo':[2,3,4]},'ipo360',False)
        self.assertEqual(db.get(rid)['cfo'],[2,3,4])
    def test_input_validation(self):
        with self.assertRaises(ValueError):db.validate_incoming({'name':'A','price_high':'Rs40 to43'})
        with self.assertRaises(ValueError):db.validate_incoming({'name':'A','cfo':[1,math.nan,2]})
        self.assertEqual(db.validate_incoming({'name':'A','sub_total':'0'})['sub_total'],0)
        with self.assertRaises(ValueError):db.validate_incoming({'name':'A','years':['2023','2025','2026']})
    def test_refresh_staleness_check(self):
        with db._lock, db.connect() as conn: conn.execute('DELETE FROM refresh_log')
        self.assertTrue(db.refresh_is_stale(),'no refresh yet recorded, should be considered stale')
        db.log_refresh('NSE',True,'ok',5)
        self.assertFalse(db.refresh_is_stale(),'just refreshed, should not be stale')
        self.assertTrue(db.refresh_is_stale(max_age_seconds=-1),'forcing a negative window should always read as stale')
    def test_gmp_source_priority(self):
        def put(source,amount):return db.merge_incoming({'name':'GMP Limited','price_high':100,'gmp_amount':amount},source,source,'https://example.com','GMP')
        rid=put('chittorgarh',10)
        put('investorgain',12)
        self.assertEqual(db.get(rid)['gmp_amount'],10)
        self.assertEqual(db.gmp_history(rid)[0]['amount'],12)
        self.assertEqual(db.gmp_history(rid)[0]['pct'],12)
    def test_listing_date_extracted_from_source_tables(self):
        # Previously no scraper/table-parser mapped a "listing date" column
        # at all, so an IPO could never move into the "Listed" status
        # bucket from an automatic refresh — see the listing_date alias in
        # scrapers/base.py.
        table=[['Name','Status','Listing Date'],['Listed Example Ltd','Listed','15-Sep-2026']]
        recs=base.rows_to_records(table)
        self.assertEqual(len(recs),1)
        self.assertEqual(recs[0]['listing_date'],'15-Sep-2026')
    def test_gmp_diagnostics_records_available_and_missing_quotes(self):
        # A GMP-diagnostic source's fetch() is synced into the per-source
        # gmp_quotes table independently of the merged gmp_amount: a company
        # it quotes gets 'available' with the figure, a company it simply
        # doesn't mention gets 'no_quote_published' rather than nothing.
        quoted=db.merge_incoming({'name':'Diagnostics Quoted Ltd','open_date':'2026-09-01'},'nse','NSE India','https://example.com','issue terms',True)
        unquoted=db.merge_incoming({'name':'Diagnostics Unquoted Ltd','open_date':'2026-09-01'},'nse','NSE India','https://example.com','issue terms',True)
        db.sync_gmp_quotes('ipowatch','IPOWatch','https://ipowatch.in/ipo-grey-market-premium/',
                            [{'name':'Diagnostics Quoted Ltd','gmp_amount':18,'gmp_pct':12.5}])
        quotes_for_quoted={q['source_key']:q for q in db.gmp_quotes_for(quoted)}
        quotes_for_unquoted={q['source_key']:q for q in db.gmp_quotes_for(unquoted)}
        self.assertEqual(quotes_for_quoted['ipowatch']['fetch_status'],'available')
        self.assertEqual(quotes_for_quoted['ipowatch']['gmp_amount'],18)
        self.assertEqual(quotes_for_unquoted['ipowatch']['fetch_status'],'no_quote_published')
    def test_gmp_diagnostics_records_failed_fetch_for_every_ipo(self):
        rid=db.merge_incoming({'name':'Diagnostics Failure Ltd','open_date':'2026-09-01'},'nse','NSE India','https://example.com','issue terms',True)
        db.sync_gmp_quotes_failed('ipo_index','IPO Index','https://ipoindex.in/ipo-gmp','HTTP 404')
        quote=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipo_index')
        self.assertEqual(quote['fetch_status'],'unavailable')
        self.assertIn('404',quote['note'])
    def test_chittorgarh_marked_as_directory_redirect_not_independent_quote(self):
        # Chittorgarh's GMP report is, in practice, the same InvestorGain
        # feed under its own branding, so it must never show up as a second
        # independent corroborating quote in the diagnostics table even
        # when its own scrape genuinely returns a number.
        rid=db.merge_incoming({'name':'Redirect Example Ltd','open_date':'2026-09-01'},'nse','NSE India','https://example.com','issue terms',True)
        db.sync_gmp_quotes('chittorgarh','Chittorgarh','https://www.chittorgarh.com/report/ipo-gmp-grey-market-premium/93/',
                            [{'name':'Redirect Example Ltd','gmp_amount':30}],
                            redirect_note='Directory links to InvestorGain; same publisher/feed, so it is not counted twice')
        quote=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='chittorgarh')
        self.assertEqual(quote['fetch_status'],'directory_redirect')
        self.assertIsNone(quote['gmp_amount'])
    def test_refresh_syncs_gmp_diagnostics_for_registered_sources(self):
        class GoodGmp:
            @staticmethod
            def fetch():return [{'name':'Synced Ltd','gmp_amount':9,'open_date':'2026-09-01'}],'fixture'
        class BadGmp:
            @staticmethod
            def fetch():raise RuntimeError('blocked by source')
        import threading
        with patch('app.refresh.REGISTRY',{'nse':(GoodGmp,'nse',True,False),'ipowatch':(BadGmp,'IPOWatch',False,True)}), \
             patch('app.refresh.SOURCE_URLS',{'nse':'https://example.com','ipowatch':'https://ipowatch.in/ipo-grey-market-premium/'}), \
             patch('app.refresh.GMP_DIAGNOSTIC_SOURCES',['ipowatch']):
            run_refresh(lambda k,v:None,threading.Event())
        rid=db.find_by_name('Synced Ltd')['id']
        quote=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipowatch')
        self.assertEqual(quote['fetch_status'],'blocked')
    def test_duplicate_short_vs_full_legal_name_are_merged(self):
        # Reproduces a real bug: one source (e.g. an official BSE feed) uses
        # a shortened name while another (e.g. a GMP source) uses the full
        # legal name, and both were showing up as two separate IPO cards.
        stub=db.merge_incoming({'name':'Maharaja & Speedex','price_high':186,'close_date':'2026-09-15'},'bse','BSE','https://example.com','Issue terms',True)
        richer=db.merge_incoming({'name':'Maharaja & Speedex India Limited','price_high':186,'gmp_amount':24.2,'close_date':'2026-09-15'},'chittorgarh','Chittorgarh','https://example.com','GMP')
        self.assertEqual(stub,richer,'should resolve to the same record, not create a second one')
        self.assertEqual(len([r for r in db.all_ipos() if db.names_match(r['name'],'Maharaja & Speedex')]),1)
        # Unrelated companies sharing only one leading word must NOT merge.
        a=db.merge_incoming({'name':'Om Galaxy Limited','price_high':90},'bse','BSE','https://example.com','Issue terms',True)
        b=db.merge_incoming({'name':'Om Industries Limited','price_high':120},'bse','BSE','https://example.com','Issue terms',True)
        self.assertNotEqual(a,b)
    def test_ipoji_gmp_fallback_when_chittorgarh_fails(self):
        def put(source,amount,official=False):return db.merge_incoming({'name':'IJ Limited','price_high':100,'gmp_amount':amount},source,source,'https://example.com','GMP',official)
        rid=put('chittorgarh',10)
        db.log_refresh('Chittorgarh',True,'ok',1)
        put('ipoji',15)
        self.assertEqual(db.get(rid)['gmp_amount'],10,'Chittorgarh just succeeded, IPOJI should not override yet')
        db.log_refresh('Chittorgarh',False,'blocked',0)
        put('ipoji',20)
        self.assertEqual(db.get(rid)['gmp_amount'],20,'Chittorgarh failed this run, IPOJI should now step in as fallback')
    def test_new_record_without_dates_is_skipped_on_refresh(self):
        class NoDates:
            @staticmethod
            def fetch():return [{'name':'Dateless Limited','status':'Upcoming'}], 'fixture'
        import threading
        with patch('app.refresh.REGISTRY',{'nse':(NoDates,'nse',True,False)}):
            run_refresh(lambda k,v:None,threading.Event())
        self.assertIsNone(db.find_by_name('Dateless Limited'))
    # ---- company-name matching across IPO websites (app/names.py) ----------
    def test_names_ignore_limited_ipo_india_and_other_suffix_noise(self):
        same=[
            ('Vikran Engineering Limited','Vikran Engg Ltd (SME) IPO GMP'),
            ('Vikran Engineering Limited','Vikran Engineering IPO Date, Price Band, Review'),
            ('Maharaja & Speedex','Maharaja and Speedex (India) Ltd.'),
            ('Shree Ahimsa Naturals Limited','Shri Ahimsa Naturals Pvt. Ltd.'),
            ('Aequs Limited','Aequs India IPO'),
            ('Orient Technologies Limited','Orient Tech'),
            ('Xyz Corp','Xyz Corporation Limited'),
            ('Sri Lotus Developers','Srilotus Developers Ltd'),
            ('S.M. Foods Limited','SM Foods IPO'),
            ('Kalpataru Limited','Kalpataru Ltd NSE SME'),
            ('Xyz Industries Limited (formerly Abc Traders)','Xyz Industries'),
        ]
        for a,b in same:
            self.assertTrue(db.names_match(a,b),f'{a!r} should match {b!r}')
            self.assertTrue(db.names_match(b,a),f'{b!r} should match {a!r}')
    def test_names_match_abbreviations_and_initialisms(self):
        for full,short in [('National Stock Exchange of India Limited','NSE'),
                           ('National Stock Exchange of India Limited','NSE IPO'),
                           ('National Stock Exchange of India Limited','NSE India Ltd'),
                           ('National Securities Depository Limited','NSDL'),
                           ('Central Depository Services (India) Limited','CDSL'),
                           ('Larsen & Toubro Limited','L&T'),
                           ('State Bank of India','SBI'),
                           ('Life Insurance Corporation of India','LIC IPO'),
                           ('Oil and Natural Gas Corporation Limited','ONGC')]:
            self.assertTrue(db.names_match(full,short),f'{full!r} should match {short!r}')
    def test_names_matching_does_not_merge_different_companies(self):
        for a,b in [('Om Galaxy Limited','Om Industries Limited'),
                    ('Shree Ram Industries','Shree Ram Enterprises'),
                    ('Shree Ram Pharma','Shree Ram Industries'),
                    ('Sai Life Sciences','Sai Silks'),
                    ('Tata Motors','Tata Steel'),
                    ('Hexa Industries','Hexa Pharma'),
                    ('NSE','BSE'),
                    ('AB Limited','Alpha Beta Limited')]:
            self.assertFalse(db.names_match(a,b),f'{a!r} must NOT match {b!r}')
    def test_names_typo_tolerance_is_opt_in(self):
        self.assertFalse(db.names_match('Shreeji Shipping Global','Shreeji Shipping Globl'))
        self.assertTrue(db.names_match('Shreeji Shipping Global','Shreeji Shipping Globl',allow_typos=True))
        self.assertFalse(db.names_match('Shree Ram Steel 1','Shree Ram Steel 2',allow_typos=True),'differing numbers are never a typo')
    def test_user_alias_file_resolves_unmatchable_names(self):
        from app import names
        self.assertFalse(db.names_match('Pinnacle Consolidated Holdings Limited','PCH Group'))
        path=os.path.join(TEMP.name,'alias-test.json')
        with open(path,'w',encoding='utf-8') as f: f.write('{"Pinnacle Consolidated Holdings Limited":["Pinnacle Group","PCG"]}')
        old=names.ALIAS_FILE
        try:
            names.ALIAS_FILE=path
            self.assertTrue(db.names_match('Pinnacle Consolidated Holdings Limited','PCG IPO'))
            self.assertTrue(db.names_match('Pinnacle Consolidated Holdings','Pinnacle Group Ltd'))
        finally:
            names.ALIAS_FILE=old
        self.assertFalse(db.names_match('Pinnacle Consolidated Holdings Limited','PCG IPO'),'alias must stop applying once the file is gone')
    def test_gmp_is_found_when_source_uses_a_different_name_form(self):
        # The reported bug: the exchange feed names the company one way, the
        # GMP sites another (abbreviation / extra words), and the GMP quote was
        # shown as "No quote published" or the GMP-only row was thrown away.
        rid=db.merge_incoming({'name':'National Stock Exchange of India Limited','open_date':'2026-09-22','close_date':'2026-09-24','price_high':100},'nse','NSE','https://example.com','Issue terms',True)
        rid2=db.merge_incoming({'name':'Vikran Engineering Limited','open_date':'2026-09-22','close_date':'2026-09-24','price_high':100},'nse','NSE','https://example.com','Issue terms',True)
        rows=[{'name':'NSE IPO','gmp_amount':45,'gmp_source_time':'19 Sept, 17:10'},
              {'name':'Vikran Engg Ltd (SME) IPO GMP','gmp_amount':12}]
        db.sync_gmp_quotes('ipowatch','IPOWatch','https://ipowatch.in/',rows)
        q1=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipowatch')
        q2=next(q for q in db.gmp_quotes_for(rid2) if q['source_key']=='ipowatch')
        self.assertEqual((q1['fetch_status'],q1['gmp_amount'],q1['source_time']),('available',45,'19 Sept, 17:10'))
        self.assertIn('NSE IPO',q1['note'],'a looser match is disclosed in the GMP tab')
        self.assertEqual((q2['fetch_status'],q2['gmp_amount']),('available',12))
        # A company the source really does not list stays "no quote published".
        rid3=db.merge_incoming({'name':'Unlisted Widgets Limited','open_date':'2026-09-22','close_date':'2026-09-24'},'nse','NSE','https://example.com','Issue terms',True)
        db.sync_gmp_quotes('ipowatch','IPOWatch','https://ipowatch.in/',rows)
        q3=next(q for q in db.gmp_quotes_for(rid3) if q['source_key']=='ipowatch')
        self.assertEqual(q3['fetch_status'],'no_quote_published')
    def test_gmp_prefers_the_matching_row_that_actually_has_a_gmp(self):
        rid=db.merge_incoming({'name':'Dual Listed Limited','open_date':'2026-09-22','close_date':'2026-09-24'},'nse','NSE','https://example.com','Issue terms',True)
        db.sync_gmp_quotes('ipoji','IPOJI','https://www.ipoji.com/ipo-gmp',[{'name':'Dual Listed IPO'},{'name':'Dual Listed Ltd','gmp_amount':7}])
        q=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipoji')
        self.assertEqual((q['fetch_status'],q['gmp_amount']),('available',7))
    def test_refresh_keeps_gmp_only_row_whose_name_differs_from_the_tracked_ipo(self):
        class Exchange:
            @staticmethod
            def fetch():return [{'name':'Vikran Engineering Limited','open_date':'2026-09-22','close_date':'2026-09-24','price_high':100}],'fixture'
        class GmpSite:  # no dates at all (GMP-only table) and a different spelling
            @staticmethod
            def fetch():return [{'name':'Vikran Engg Ltd IPO','gmp_amount':30},{'name':'Some Closed Old IPO','gmp_amount':5}],'fixture'
        import threading
        with patch('app.refresh.REGISTRY',{'nse':(Exchange,'NSE',True,False),'ipowatch':(GmpSite,'IPOWatch',False,True)}), \
             patch('app.refresh.SOURCE_URLS',{'nse':'https://example.com','ipowatch':'https://ipowatch.in/'}), \
             patch('app.refresh.GMP_DIAGNOSTIC_SOURCES',['ipowatch']):
            run_refresh(lambda k,v:None,threading.Event())
        matches=[r for r in db.all_ipos() if 'vikran' in r['name'].lower()]
        self.assertEqual(len(matches),1,'the GMP-only row must join the tracked IPO, not be dropped or duplicated')
        self.assertEqual(matches[0]['gmp_amount'],30)
        self.assertIsNone(db.find_by_name('Some Closed Old Limited'),'an unknown, dateless row is still skipped')
        quote=next(q for q in db.gmp_quotes_for(matches[0]['id']) if q['source_key']=='ipowatch')
        self.assertEqual((quote['fetch_status'],quote['gmp_amount']),('available',30))
    # ---- IPOJI not being fetched: reasons, parsing, fallbacks --------------
    IPOJI_TABLE=('''<link rel="canonical" href="https://www.ipoji.com/ipo-gmp"><table><thead><tr><th>IPO</th><th>Type</th><th>Price Band (\u20b9)</th><th>GMP (\u20b9)</th><th>GMP %</th>
<th>Indicative Listing (\u20b9) = upper price band + GMP.</th><th>Open \u2013 Close</th><th>Status</th><th>Last Updated</th></tr></thead><tbody>
<tr><td><a href="/ipo/ss-retail-ipo">SS Retail IPO</a> <span>Mainboard Closed</span></td><td>Mainboard</td><td>\u20b9403-424</td><td><a href="/ipo-gmp/ss-retail-ipo">+\u20b9138 (+33%)</a></td><td>+33%</td><td>\u20b9562</td><td>Sep 16, 2026 \u2013 Sep 18, 2026</td><td>Closed</td><td>20 Sep 2026, 2:15 PM IST</td></tr>
<tr><td><a href="/ipo/weak-ipo">Weak IPO</a></td><td>Mainboard</td><td>\u20b9100</td><td><a href="/ipo-gmp/weak-ipo">-\u20b95 (-5%)</a></td><td>-5%</td><td>\u20b995</td><td>x</td><td>Open</td><td>x</td></tr>
<tr><td><a href="/ipo/kheria-autocomp-ipo">Kheria Autocomp IPO</a></td><td>NSE SME</td><td>\u20b996-101</td><td>\u2014</td><td>\u2014</td><td>\u2014</td><td>x</td><td>Open</td><td>\u2014</td></tr></tbody></table>''')
    def test_gmp_numbers_keep_their_sign(self):
        self.assertEqual(base.number_text('+\u20b9135 (+32%)'),135)
        self.assertEqual(base.number_text('-\u20b95 (-5%)'),-5,'a negative rupee GMP must not become positive')
        self.assertEqual(base.number_text('\u20b9-45'),-45)
        self.assertEqual(base.number_text('\u20b925 (27%)'),25,'a bracketed percentage is not an accounting negative')
        self.assertEqual(base.number_text('(1,234.5)'),-1234.5)
        self.assertEqual(math.copysign(1,base.number_text('\u20b90 (0%)')),1.0,'zero GMP is 0, never -0')
    def test_ipoji_table_and_link_layouts_both_parse(self):
        from app.scrapers import ipoji
        rows={r['name']:r for r in ipoji.parse_page(self.IPOJI_TABLE)}
        self.assertEqual(rows['SS Retail IPO Mainboard Closed']['gmp_amount'],138)
        self.assertEqual(rows['Weak IPO']['gmp_amount'],-5)
        self.assertNotIn('gmp_amount',rows['Kheria Autocomp IPO'])
        # No <table> at all (cards / divs): the /ipo-gmp/<slug> links still carry every quote.
        cards='''<div><a href="/ipo/ss-retail-ipo">SS Retail IPO</a><a href="/ipo-gmp/ss-retail-ipo">+\u20b9138 (+33%)</a></div>
        <a href="/ipo/current-ipo">Current IPO</a><div><a href="/ipo/weak-ipo">Weak IPO</a><a href="/ipo-gmp/weak-ipo">-\u20b95 (-5%)</a></div>'''
        got={r['name']:(r['gmp_amount'],r.get('gmp_pct')) for r in ipoji.parse_page(cards)}
        self.assertEqual(got,{'SS Retail IPO':(138,33),'Weak IPO':(-5,-5)})
        self.assertEqual(ipoji.parse_page('<html><body>Loading...</body></html>'),[])
    def test_names_ignore_investorgain_status_letter_suffix(self):
        for tracked,listed in [('SS Retail Limited','SS Retail IPOC'),('Aequs Limited','Aequs IPOC'),('Aequs Limited','Aequs IPOCT'),
                               ('Robokidz Eduventures Limited','Robokidz Eduventures Ltd. SMEU'),
                               ('Hero Motors Limited','Hero Motors IPO Mainboard Closed'),
                               ('Kheria Autocomp Limited','Kheria Autocomp IPO NSE SME Open')]:
            self.assertTrue(db.names_match(tracked,listed),f'{tracked!r} should match {listed!r}')
        self.assertFalse(db.names_match('Om Galaxy Limited','Om Industries IPOC'))
    def _ipoji_fetch(self,response,env_browser=None):
        from app.scrapers import ipoji
        class Resp:
            def __init__(s,status,text): s.status_code=status;s.text=text;s.content=text.encode();s.headers={}
        env={k:v for k,v in os.environ.items() if k!='IPO_COMPASS_BROWSER'}
        if env_browser: env['IPO_COMPASS_BROWSER']=env_browser
        with patch('app.network.get_page',return_value=Resp(*response)), patch.dict(os.environ,env,clear=True):
            return ipoji.fetch()
    def test_ipoji_fetch_succeeds_from_a_plain_request(self):
        records,message=self._ipoji_fetch((200,self.IPOJI_TABLE))
        self.assertEqual(len(records),3);self.assertIn('IPOJI',message)
    def test_ipoji_failure_message_states_the_actual_reason(self):
        # Page arrives without any data (JavaScript-filled) and no headless browser available.
        with self.assertRaises(RuntimeError) as cm: self._ipoji_fetch((200,'<html><body>Loading...</body></html>'))
        msg=str(cm.exception)
        for fragment in ('HTTP 200','0 table(s)','0 GMP link(s)','not enabled','Import saved GMP page'): self.assertIn(fragment,msg)
        # A refused request names its status, and is classed as blocked (not just "unavailable").
        with self.assertRaises(RuntimeError) as cm: self._ipoji_fetch((403,'<html>Just a moment...</html>'))
        self.assertIn('HTTP 403',str(cm.exception))
    def test_failure_reason_is_kept_for_the_gmp_tab(self):
        rid=db.merge_incoming({'name':'Reason Example Limited','open_date':'2026-09-22','close_date':'2026-09-24'},'nse','NSE','https://example.com','t',True)
        db.sync_gmp_quotes_failed('ipoji','IPOJI','https://www.ipoji.com/ipo-gmp','IPOJI page could not be read. Plain request: HTTP 200, 1 KB, 0 table(s) with data')
        q=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipoji')
        self.assertEqual(q['fetch_status'],'unavailable');self.assertIn('0 table(s)',q['note'])
        db.sync_gmp_quotes_failed('ipoji','IPOJI','https://www.ipoji.com/ipo-gmp','IPOJI page could not be read. Plain request: HTTP 403')
        q=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipoji')
        self.assertEqual(q['fetch_status'],'blocked')
    def test_saved_page_import_feeds_the_gmp_tab_when_live_fetch_is_impossible(self):
        from app.page_import import detect_source,import_saved_page
        rid=db.merge_incoming({'name':'SS Retail Limited','open_date':'2026-09-16','close_date':'2026-09-18','price_high':424},'nse','NSE','https://example.com','t',True)
        self.assertEqual(detect_source('IPO GMP Today _ IPO Ji.html',self.IPOJI_TABLE),'ipoji')
        self.assertIsNone(detect_source('notes.html','<html>nothing recognisable</html>'))
        message=import_saved_page('IPO GMP Today _ IPO Ji.html',self.IPOJI_TABLE)
        self.assertIn('1 of your 1',message)
        q=next(q for q in db.gmp_quotes_for(rid) if q['source_key']=='ipoji')
        self.assertEqual((q['fetch_status'],q['gmp_amount'],q['source_time']),('available',138,'20 Sep 2026, 2:15 PM IST'))
        # Rows for IPOs you do not track, with no dates, are not turned into new IPOs.
        self.assertEqual([r['name'] for r in db.all_ipos()],['SS Retail Limited'])
        with self.assertRaises(ValueError): import_saved_page('x.html','<html>nothing recognisable</html>')
        with self.assertRaises(ValueError): import_saved_page('ipoji.html','<link rel="canonical" href="https://www.ipoji.com/ipo-gmp"><p>Loading</p>')
    def test_export_escaping(self):
        # 'name' is now sanitised at the validation boundary (see
        # test_validate_incoming_strips_markup_from_name), so a raw '<script>'
        # tag there is stripped rather than reaching the report at all. 'notes'
        # is free text and isn't stripped, so it's still the defense-in-depth
        # case: report.py must HTML-escape it on the way out regardless.
        rid=db.merge_incoming({'name':'<script>alert(1)</script>Example Co','notes':'<img src=x onerror=x>'},'manual','manual','','test')
        record=db.get(rid)
        self.assertEqual(record['name'],'alert(1) Example Co')
        output=make_report(record)
        self.assertNotIn('<script>',output);self.assertNotIn('<img src=x',output)
        self.assertIn('&lt;img src=x onerror=x&gt;',output)
    def test_refresh_continues(self):
        class Bad:
            @staticmethod
            def fetch():raise RuntimeError('Fixture failure')
        class Good:
            @staticmethod
            def fetch():return [{'name':'New Limited','status':'Upcoming','open_date':'2026-09-20'}], 'fixture'
        import threading
        messages=[]
        with patch('app.refresh.REGISTRY',{'nse':(Bad,'bad',True,False),'bse':(Good,'good',True,False)}),patch('app.refresh.enrich_record',return_value='research fixture') as enrich:
            run_refresh(lambda k,v:messages.append((k,v)),threading.Event())
            self.assertEqual(enrich.call_count,1)
        self.assertTrue(any(k=='done' for k,v in messages));self.assertEqual(len(db.all_ipos()),1)

    def test_mixed_rhp_columns(self):
        text='''SUMMARY OF RESTATED CONSOLIDATED STATEMENT OF CASH FLOW (₹ in million)
        For the three month period ended June 30, 2025 For the year ended March 31, 2025
        For the year ended March 31, 2024 For the year ended March 31, 2023
        Net Cash Flow from Operating Activities (a) 99.00 300.00 (200.00) 100.00
        Purchase of Property, Plant & Equipment, Intangible Assets & CWIP (5.00) (80.00) (50.00) (30.00)'''
        ev=parse_mixed_page(text,10,'https://example.com/rhp.pdf')
        series={'series':{},'evidence':[],'conflicts':[]};combine(series,ev);derive(series)
        self.assertEqual(series['series'][2025]['cfo'],30)
        self.assertEqual(series['series'][2024]['cfo'],-20)
        self.assertEqual(series['series'][2025]['fcf'],22)
        self.assertEqual(len([e for e in ev if e['metric']=='cfo']),3)
        self.assertEqual(parse_mixed_page(text.replace('June 30','September 30'),10,'https://example.com/rhp.pdf'),[])

    def test_secondary_annual_columns_and_derivation(self):
        text='<h1>Example Limited IPO</h1><p>Rs. in Cr</p><table><tr><th>Metric</th><th>Jun-25</th><th>Mar-25</th><th>Mar-24</th><th>Mar-23</th></tr>'
        rows={'Profit Before Tax':[999,30,25,20],'Finance Costs':[999,5,4,3],'Depreciation':[999,4,3,2],'Other Income':[999,2,1,1],'Cash Flow from Operating Activities':[999,40,-10,20],'Cash Flow from Investing Activities':[999,-20,-30,-40]}
        for k,vals in rows.items():text+='<tr><td>'+k+'</td>'+''.join('<td>'+str(v)+'</td>' for v in vals)+'</tr>'
        text+='</table>'
        research=parse_statements(text,'Example Limited','https://example.com/company')
        self.assertEqual(research['series'][2025]['ebitda'],37)
        self.assertNotIn('fcf',research['series'][2025])
        self.assertNotIn('capex',research['series'][2025])
        with self.assertRaises(ValueError):parse_statements(text,'Different Limited','https://example.com/company')

    def test_chittorgarh_kpi_post_issue_pe_only(self):
        # Reproduces a real case (Raksan Transformers): Chittorgarh's KPI
        # table reports both "P/E Pre IPO" and "P/E Post IPO" — only the
        # post-issue (asking-price) figure should be picked up as 'pe',
        # since that's what scoring.valuation_score() compares to peers.
        html=('<table><tr><th>KPI</th><th>9 September, 2026</th></tr>'
              '<tr><td>ROE</td><td>32.5%</td></tr>'
              '<tr><td>P/E Pre IPO</td><td>13.39</td></tr>'
              '<tr><td>P/E Post IPO</td><td>16.98</td></tr></table>')
        evidence=parse_chittorgarh_kpi(html,'https://www.chittorgarh.com/ipo/raksan-transformers-ipo/2767/')
        by_metric={e['metric']:e['value'] for e in evidence}
        self.assertEqual(by_metric.get('pe'),16.98)
        self.assertEqual(by_metric.get('roe'),32.5)
        self.assertEqual(evidence[0]['year'],2026)

    def test_prospectus_valuation_and_concentration_clean_match(self):
        text=('QUANTITATIVE FACTORS P/E ratio in relation to the Price Band at the Cap Price is 23.50 times. '
              'Comparison with listed industry peers shows an Industry P/E of 27.10. '
              'Our top 10 customers accounted for 42.3% of our revenue from operations in fiscal 2026. '
              'Our top five suppliers accounted for 15.0% of our purchases in fiscal 2026.')
        evidence=parse_valuation_and_concentration(text,'https://example.com/rhp.pdf')
        values={e['metric']:e['value'] for e in evidence}
        self.assertEqual(values.get('pe'),23.5)
        self.assertEqual(values.get('peer_pe'),27.1)
        self.assertEqual(values.get('top_cust'),42.3)
        self.assertEqual(values.get('top_supp'),15.0)
        self.assertTrue(all(e['confidence']=='experimental' for e in evidence))

    def test_prospectus_valuation_ambiguous_matches_are_skipped(self):
        # Two different numbers claiming to be "P/E at Cap Price" -> genuinely
        # ambiguous from text alone, must not guess either one.
        text=('P/E ratio at the Cap Price is 23.50 times for the Company. '
              'A restated P/E ratio at the Cap Price of 19.00 times is also disclosed elsewhere.')
        evidence=parse_valuation_and_concentration(text,'https://example.com/rhp.pdf')
        self.assertNotIn('pe',{e['metric'] for e in evidence})

    def test_liquidity_score_thresholds(self):
        self.assertEqual(scoring.liquidity_score(2.5),9)
        self.assertEqual(scoring.liquidity_score(1.3),6.5)
        self.assertEqual(scoring.liquidity_score(.5),2)
        self.assertIsNone(scoring.liquidity_score(0))
        self.assertIsNone(scoring.liquidity_score(None))

    def test_gmp_trend_derived_from_history(self):
        rid=db.merge_incoming({'name':'Trend Limited','price_high':100,'gmp_amount':10},'chittorgarh','Chittorgarh','https://example.com','GMP')
        self.assertEqual(db.get(rid)['gmp_trend'],'Unknown','a single reading cannot show a trend yet')
        # Backdate that first reading so the next one clears min_gap_hours.
        with db._lock, db.connect() as conn:
            old_at=(datetime.now(timezone.utc)-timedelta(hours=20)).isoformat()
            conn.execute('UPDATE gmp_history SET at=? WHERE ipo_id=?',(old_at,rid))
            conn.commit()
        db.merge_incoming({'name':'Trend Limited','price_high':100,'gmp_amount':18},'chittorgarh','Chittorgarh','https://example.com','GMP')
        self.assertEqual(db.get(rid)['gmp_trend'],'Rising')

    def test_primary_priority_and_conflict(self):
        r={'series':{},'evidence':[],'conflicts':[]}
        combine(r,[{'metric':'cfo','year':2025,'value':10,'source':'https://example.com/secondary','primary':False}])
        combine(r,[{'metric':'cfo','year':2025,'value':-20,'source':'https://example.com/rhp','primary':True}])
        self.assertEqual(r['series'][2025]['cfo'],-20)
        self.assertEqual(len(r['conflicts']),1)

    def test_active_status_and_exchange_deduplication(self):
        from datetime import date
        today=date(2026,9,13)
        self.assertTrue(db.is_active({'status':'Check','open_date':'2026-09-15','close_date':'2026-09-17'},today))
        self.assertEqual(db.display_status({'status':'Check','open_date':'2026-09-15','close_date':'2026-09-17'},today),'Upcoming')
        self.assertFalse(db.is_active({'status':'Check','open_date':'2026-09-01','close_date':'2026-09-12'},today))
        self.assertFalse(db.is_active({'status':'Check','open_date':'2026-09-01'},today))
        first=db.merge_incoming({'name':'Dual Exchange Limited','exchange':'BSE','open_date':'2026-09-15','close_date':'2026-09-17'},'bse','BSE','https://example.com/bse','official',True)
        second=db.merge_incoming({'name':'Dual Exchange Ltd IPO','exchange':'NSE','open_date':'2026-09-16','close_date':'2026-09-18'},'nse','NSE','https://example.com/nse','official',True)
        self.assertEqual(first,second)
        self.assertEqual(db.get(first)['exchange'],'BSE / NSE')
        self.assertEqual(len([r for r in db.all_ipos() if db.slugify(r['name'])=='dual-exchange']),1)
        old_a=db.ensure_record({'id':'old-bse','name':'Existing Duplicate Limited','exchange':'BSE','notes':'Retain this note'})
        old_b=db.ensure_record({'id':'old-nse','name':'Existing Duplicate Ltd','exchange':'NSE','cfo':[1,2,3]})
        db.upsert_ipo(old_a);db.upsert_ipo(old_b);db.add_source(old_b['id'],'NSE','https://example.com/nse','issue data')
        mapping=db.consolidate_duplicates()
        merged=[r for r in db.all_ipos() if db.slugify(r['name'])=='existing-duplicate']
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['exchange'],'BSE / NSE')
        self.assertEqual(merged[0]['notes'],'Retain this note')
        self.assertEqual(merged[0]['cfo'],[1,2,3])
        self.assertTrue(db.sources_for(merged[0]['id']))
        self.assertEqual(len(mapping),1)

    def test_5pm_ist_closing_cutoff(self):
        from datetime import date,datetime,timezone
        today=date(2026,9,18)
        r={'status':'Open','close_date':'2026-09-18'}
        before=datetime(2026,9,18,11,0,tzinfo=timezone.utc)   # 4:30 PM IST
        after=datetime(2026,9,18,12,0,tzinfo=timezone.utc)    # 5:30 PM IST
        self.assertEqual(db.display_status(r,today,before),'Open')
        self.assertTrue(db.is_active(r,today,before))
        self.assertEqual(db.display_status(r,today,after),'Closed')
        self.assertFalse(db.is_active(r,today,after))

    def test_refresh_scope_covers_closed_and_recent_listings(self):
        from datetime import date
        today=date(2026,9,18)
        self.assertTrue(db.in_refresh_scope({'status':'Closed','close_date':'2026-09-14'},today))   # 4 days ago
        self.assertFalse(db.in_refresh_scope({'status':'Closed','close_date':'2026-09-10'},today))  # 8 days ago -> out of scope
        self.assertTrue(db.in_refresh_scope({'status':'Listed','listing_date':'2026-09-15'},today))
        self.assertFalse(db.in_refresh_scope({'status':'Listed','listing_date':'2026-08-19'},today))
        # No close_date at all: fall back to the open_date recency rule (15 days).
        self.assertTrue(db.in_refresh_scope({'status':'Closed','open_date':'2026-09-05'},today))    # 13 days ago
        self.assertFalse(db.in_refresh_scope({'status':'Closed','open_date':'2026-08-25'},today))   # 24 days ago -> out of scope

    def test_listed_status_display_expires_after_five_days(self):
        from datetime import date
        today=date(2026,9,20)
        # Listed today, and up to 5 days ago inclusive: still shown as Listed.
        self.assertEqual(db.display_status({'listing_date':'2026-09-20'},today),'Listed')
        self.assertEqual(db.display_status({'listing_date':'2026-09-15'},today),'Listed')
        # Older than 5 days: the "just listed" spotlight window has passed.
        self.assertEqual(db.display_status({'listing_date':'2026-09-14'},today),'Closed')
        self.assertEqual(db.display_status({'listing_date':'2026-08-10'},today),'Closed')

    def test_subscription_fields_take_freshest_value_regardless_of_official_flag(self):
        rid=db.merge_incoming({'name':'Sub Freshness Limited','sub_total':1.5},'nse','NSE','https://example.com','official',True)
        self.assertEqual(db.get(rid)['sub_total'],1.5)
        db.merge_incoming({'name':'Sub Freshness Limited','sub_total':2.3},'investorgain_subscription','InvestorGain Subscription','https://example.com','live',False)
        self.assertEqual(db.get(rid)['sub_total'],2.3)

    def test_closed_ipos_only_stay_visible_within_the_recency_window(self):
        import json,threading,urllib.request
        from app.webapp import DashboardServer
        from datetime import date,timedelta
        recent_close=(date.today()-timedelta(days=2)).isoformat()
        db.merge_incoming({'name':'Recently Closed Limited','status':'Closed','close_date':recent_close},'bse','BSE','https://example.com','official',True)
        db.merge_incoming({'name':'Long Closed Limited','status':'Closed','close_date':'2020-01-01'},'bse','BSE','https://example.com','official',True)
        server=DashboardServer();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            state=json.load(urllib.request.urlopen('http://127.0.0.1:'+str(server.server_port)+'/api/state',timeout=3))
            names={r['name'] for r in state['records']}
            self.assertIn('Recently Closed Limited',names,'a closed IPO within the recency window must still reach the browser')
            self.assertNotIn('Long Closed Limited',names,'a closed IPO well outside the recency window should no longer be shown')
        finally:server.shutdown();server.server_close()

    def test_purge_malformed_records_from_concatenated_cell_bug(self):
        good=db.merge_incoming({'name':'Sonaselection India Limited','open_date':'2026-09-17'},'bse','BSE','https://example.com','official',True)
        bad=db.upsert_ipo(db.ensure_record({'name':'Sonaselection IndiaIPOGMP:₹2 (2.02%)O'}))
        self.assertEqual(db.purge_malformed_records(db.all_ipos()),1)
        remaining={r['id'] for r in db.all_ipos()}
        self.assertIn(good,remaining)
        self.assertNotIn(bad,remaining)

    def test_purge_malformed_records_from_raw_markup_bug(self):
        # Reproduces the reported dashboard bug: a manually imported JSON
        # record kept a table cell's outerHTML (link + badge spans) instead
        # of its plain text as the company name.
        good=db.merge_incoming({'name':'Raksan Transformers','open_date':'2026-09-15'},'bse','BSE','https://example.com','official',True)
        bad=db.upsert_ipo(db.ensure_record({'name':(
            '<a href="/subscription/raksan-transformers-ipo/2022/" title="Raksan Transformers" '
            'target="_parent">Raksan Transformers</a> '
            '<span class="badge rounded-pill bg-secondary d-inline ms-2">BSE SME</span>'
        )}))
        self.assertEqual(db.purge_malformed_records(db.all_ipos()),1)
        remaining={r['id'] for r in db.all_ipos()}
        self.assertIn(good,remaining)
        self.assertNotIn(bad,remaining)

    def test_validate_incoming_strips_markup_from_name(self):
        # A future manual/JSON import can't reintroduce the raw-markup bug:
        # validate_incoming() now sanitises the name field up front.
        out=db.validate_incoming({'name':'<a href="/x/">Example Company</a> <span class="badge">SME</span>'})
        self.assertEqual(out['name'],'Example Company SME')

    def test_rows_to_records_rejects_concatenated_cell_garbage(self):
        from app.scrapers.base import rows_to_records
        self.assertEqual(rows_to_records([['IPO'],['Sonaselection IndiaIPOGMP:₹2 (2.02%)O']]),[])
        self.assertEqual(rows_to_records([['Name','Badge'],['NSEIPOGMP:₹61 (3.42%)O','x']]),[])
        clean=rows_to_records([['IPO','Price Band','GMP','GMP %','Status'],['Sonaselection India','99-99','2','2.02%','Open']])
        self.assertEqual(clean[0]['name'],'Sonaselection India')

    def test_local_dashboard_api(self):
        import json,threading,urllib.request,urllib.error
        from app.webapp import DashboardServer
        server=DashboardServer();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base_url='http://127.0.0.1:'+str(server.server_port)
        try:
            state=json.load(urllib.request.urlopen(base_url+'/api/state',timeout=3))
            self.assertEqual(state['records'],[])
            body=json.dumps({'records':[{'name':'API Test Limited'}]}).encode()
            request=urllib.request.Request(base_url+'/api/import',body,{'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request,timeout=3)
            request.add_header('X-Compass-Token',state['token'])
            self.assertTrue(json.load(urllib.request.urlopen(request,timeout=3))['ok'])
            records=json.load(urllib.request.urlopen(base_url+'/api/state',timeout=3))['records']
            self.assertEqual(records[0]['name'],'API Test Limited')
            self.assertIsInstance(records[0]['analysis']['factors'],list)
            request.add_header('Origin','https://example.com')
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request,timeout=3)
            self.assertIn(b'CA IPO Compass',urllib.request.urlopen(base_url+'/',timeout=3).read())
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
