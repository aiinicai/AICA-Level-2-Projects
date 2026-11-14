import unittest, json, urllib.request, threading, urllib.error
from http.server import ThreadingHTTPServer
from tax_engine import assess, DB, InputError, find_rate
from server import Handler
BASE={'payer':'Indian Payer','recipient':'US Recipient','country':'USA','paymentType':'Interest','residentType':'Bank','amount':'1000000','payDate':'2026-11-07','grossUp':'No','businessProfitsClause':'No','trc':'Yes','form41':'Yes','nope':'Yes'}
class V51Tests(unittest.TestCase):
 def test_country_count(self):self.assertEqual(len(set(x['country'] for x in DB['rates'])),87)
 def test_rate_count(self):self.assertEqual(len(DB['rates']),362)
 def test_country_examples(self):self.assertIn('Albania',{x['country'] for x in DB['rates']});self.assertIn('USA',{x['country'] for x in DB['rates']})
 def test_uncapped_records(self):self.assertEqual(sum(x['rate_percent'] is None for x in DB['rates']),23)
 def test_backing_rows(self):self.assertTrue(all(x['excel_row']>=2 and x['source_text'] for x in DB['rates']))
 def test_domestic_categories(self):self.assertEqual(len(DB['domestic_rates']),4)
 def test_receiver_types(self):self.assertEqual(DB['recipient_types']['Interest'],['Bank','Any other recipient'])
 def test_US_bank_rate(self):self.assertEqual(assess(BASE)['applicable_rate_percent'],'10.0')
 def test_US_other_rate(self):self.assertEqual(assess(BASE|{'residentType':'Any other recipient'})['applicable_rate_percent'],'15.0')
 def test_US_bank_tax(self):self.assertEqual(assess(BASE)['withholding_amount_inr'],'100000.00')
 def test_missing_document_default(self):
  for key in ('trc','form41','nope'):
   d=assess(BASE|{key:'No'});self.assertEqual(d['mode'],'DOMESTIC');self.assertEqual(d['applicable_rate_percent'],'31.200000')
 def test_gross_up(self):self.assertEqual(assess(BASE|{'grossUp':'Yes'})['withholding_amount_inr'],'90909.09')
 def test_dividend(self):
  x=BASE|{'paymentType':'Dividend','residentType':'Any other recipient'}
  d=assess(x);self.assertEqual(d['applicable_rate_percent'],'25.0')
 def test_no_rate_cap_unresolved(self):
  candidates=[r for r in DB['rates'] if r['rate_percent'] is None and r['recipient_condition'].lower()=='any']
  self.assertTrue(candidates)
  for r in candidates:
   cat=r['category'];rtype={'Dividend':'Any other recipient','Interest':'Any other recipient','Royalty':'Any person','Fees for technical services':'Any person'}[cat]
   d=assess(BASE|{'country':r['country'],'paymentType':cat,'residentType':rtype})
   if d['treaty_rate_record'] and d['treaty_rate_record']['rate_percent'] is None:
    self.assertIsNone(d['applicable_rate_percent']);break
  else:self.fail('No unresolved nonnumeric sample')
 def test_nil_review(self):self.assertEqual(assess(BASE|{'businessProfitsClause':'Yes'})['mode'],'NIL_REVIEW')
 def test_paper_status(self):self.assertTrue(all('UNVERIFIED' in x['status'].upper() or 'unverified' in x['status'].lower() for x in DB['rates']))
 def test_api_get_and_post(self):
  srv=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
  try:
   base=f'http://127.0.0.1:{srv.server_port}'
   with urllib.request.urlopen(base+'/api/data') as r:payload=json.load(r)
   self.assertEqual(len(payload['countries']),87);self.assertEqual(len(payload['rates']),362)
   with urllib.request.urlopen(base+'/api/evidence?id=XLSX-REV-360') as r:self.assertEqual(json.load(r)['country'],'USA')
   req=urllib.request.Request(base+'/api/assess',data=json.dumps(BASE).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['withholding_amount_inr'],'100000.00')
  finally:srv.shutdown();srv.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
