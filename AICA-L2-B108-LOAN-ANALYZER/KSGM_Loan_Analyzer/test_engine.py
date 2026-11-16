import unittest
from datetime import date
from decimal import Decimal as D
from engine import analyze, normalize, money, classify

class EngineTests(unittest.TestCase):
    def row(self,day,balance,debit=0,credit=0,category='Other',source=1):
        return dict(date=date(2026,4,day),balance=D(str(balance)),debit=D(str(debit)),credit=D(str(credit)),category=category,source=source,description='test')
    def run_analysis(self,rows=None,**kwargs):
        args=dict(start=date(2026,4,1),end=date(2026,4,30),opening=D(100000),annual_rate=D(12))
        args.update(kwargs);return analyze(rows or [],**args)
    def test_fixed_daily_product(self):
        self.assertAlmostEqual(self.run_analysis()['expected'],D(100000)*D('.12')*30/365,places=18)
    def test_repayment_and_weekend_carry(self):
        result=self.run_analysis([self.row(10,80000,credit=20000)])
        self.assertAlmostEqual(result['expected'],(D(100000)*9+D(80000)*21)*D('.12')/365,places=18)
        self.assertEqual(result['warnings'],[])
    def test_same_day_last_balance(self):
        r=self.run_analysis([self.row(1,90000,credit=10000,source=1),self.row(1,80000,credit=10000,source=2)])
        self.assertEqual(r['average'],80000)
    def test_rate_changes(self):
        r=self.run_analysis(rate_changes=[(date(2026,4,16),D(10))])
        self.assertAlmostEqual(r['expected'],D(100000)*(D('.12')*15+D('.10')*15)/365,places=18)
    def test_leap_and_year_transition(self):
        r=self.run_analysis(start=date(2023,12,31),end=date(2024,1,1),basis='Actual/Actual')
        self.assertAlmostEqual(r['expected'],D(12000)/365+D(12000)/366,places=18)
    def test_credit_reversals(self):
        r=self.run_analysis([self.row(2,100200,200,category='Bank charges'),self.row(3,100100,credit=100,category='Bank charges')])
        self.assertEqual(r['totals']['Bank charges'],100)
        self.assertEqual(r['totals']['Interest'],0)
    def test_fixed_mode_ignores_repayment(self):
        r=self.run_analysis([self.row(2,0,credit=100000)],mode='Fixed principal')
        self.assertEqual(r['average'],100000)
    def test_credit_balance_no_interest(self):
        self.assertEqual(self.run_analysis([self.row(1,-100,credit=100100)])['expected'],0)
    def test_reconciliation_flags_gap(self):
        self.assertEqual(len(self.run_analysis([self.row(1,90000)])['warnings']),1)
    def test_missing_balance_blocked(self):
        row=self.row(1,0);row['balance']=None
        with self.assertRaises(ValueError):self.run_analysis([row])
    def test_zero_balance_excel_numeric(self):
        mapping={'Date':'d','Description':'n','Debit':'dr','Credit':'cr','Balance':'b'}
        rows,errors=normalize([{'d':'01/04/2026','n':'repayment','dr':0,'cr':100000,'b':0}],mapping)
        self.assertEqual(errors,[]);self.assertEqual(rows[0]['balance'],0)
    def test_cr_dr_and_parse_errors(self):
        m={'Date':'d','Description':'n','Balance':'b'}
        rows,errors=normalize([{'d':'01/04/2026','n':'x','b':'100 CR'},{'d':'bad','n':'x','b':'2 DR'}],m,balance_mode='DR/CR suffix')
        self.assertEqual(rows[0]['balance'],-100);self.assertEqual(len(errors),1)
    def test_money_and_classification(self):
        self.assertEqual(money('1,00,000.50 DR'),D('100000.50'))
        self.assertEqual(classify('GST on interest'),'GST / tax')
        self.assertEqual(classify('penal interest'),'Penal interest')
        for value in ['NaN','Infinity','nonsense']:
            with self.assertRaises(ValueError):money(value)
    def test_invalid_dates_and_rate(self):
        with self.assertRaises(ValueError):self.run_analysis(end=date(2026,3,1))
        with self.assertRaises(ValueError):self.run_analysis(annual_rate=D(-1))
    def test_actual360(self):
        self.assertAlmostEqual(self.run_analysis(basis='Actual/360')['expected'],D(1000),places=18)

if __name__=='__main__':unittest.main()
