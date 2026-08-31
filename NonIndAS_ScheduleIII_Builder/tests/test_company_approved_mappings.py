import unittest
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_connection
from src.mapping_engine import execute_auto_mapping, update_single_mapping, get_mapping_register, bulk_map_tally_group
from src.import_engine import save_imported_ledgers

class TestCompanyApprovedMappings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    @classmethod
    def tearDownClass(cls):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE company_settings SET company_name = 'Apex Engineering India Private Limited';")
        conn.commit()
        conn.close()

    def setUp(self):

        conn = get_connection()
        cursor = conn.cursor()
        # Set active company to 'Test Corp Alpha'
        cursor.execute("UPDATE company_settings SET company_name = 'Test Corp Alpha';")
        cursor.execute("DELETE FROM company_approved_mappings WHERE company_name = 'Test Corp Alpha';")
        cursor.execute("DELETE FROM tally_import;")
        cursor.execute("DELETE FROM ledger_mappings;")
        conn.commit()
        conn.close()

    def test_approved_mapping_permanently_retained_on_reimport(self):
        # 1. Import TB with 3 ledgers
        ledgers = [
            {'ledger_name': 'Custom Project Advances', 'tally_group': 'Current Liabilities', 'closing_net': -50000.0},
            {'ledger_name': 'HDFC Bank OD', 'tally_group': 'Bank OD A/c', 'closing_net': -120000.0},
            {'ledger_name': 'Machinery Spare Parts', 'tally_group': 'Direct Expenses', 'closing_net': 35000.0},
        ]
        save_imported_ledgers(ledgers)
        
        # 2. Run auto-mapping (initial state)
        mapped, reviews = execute_auto_mapping()
        
        # 3. CA Reviews and approves 'Custom Project Advances' as OTHER_CURRENT_LIAB (Note 10)
        update_single_mapping(
            ledger_name='Custom Project Advances',
            schedule3_code='OTHER_CURRENT_LIAB',
            note_no='10',
            classification_override='Current',
            cash_flow_category='Operating',
            review_status='Approved',
            review_note='CA verified as advance against export orders',
            user_name='CA Lead Auditor'
        )

        # Verify it was saved to permanent company memory
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_approved_mappings WHERE company_name = 'Test Corp Alpha' AND ledger_name = 'Custom Project Advances';")
        frozen_row = cursor.fetchone()
        self.assertIsNotNone(frozen_row)
        self.assertEqual(frozen_row['schedule3_code'], 'OTHER_CURRENT_LIAB')
        self.assertEqual(frozen_row['review_status'], 'Approved')
        conn.close()

        # 4. Now simulate next year's TB import or re-importing TB
        # Notice that 'Custom Project Advances' appears again with different balance
        next_year_ledgers = [
            {'ledger_name': 'Custom Project Advances', 'tally_group': 'Current Liabilities', 'closing_net': -85000.0},
            {'ledger_name': 'Machinery Spare Parts', 'tally_group': 'Direct Expenses', 'closing_net': 42000.0},
        ]
        save_imported_ledgers(next_year_ledgers)
        
        # 5. Run auto-mapping on the new TB
        execute_auto_mapping()

        # 6. Verify that 'Custom Project Advances' was automatically populated with the frozen approved mapping
        mappings = {r['ledger_name']: r for r in get_mapping_register()}
        adv_mapping = mappings.get('Custom Project Advances')
        self.assertIsNotNone(adv_mapping)
        self.assertEqual(adv_mapping['schedule3_code'], 'OTHER_CURRENT_LIAB')
        self.assertEqual(adv_mapping['note_no'], '10')
        self.assertEqual(adv_mapping['review_status'], 'Approved')
        self.assertEqual(adv_mapping['is_company_frozen'], 1)
        self.assertIn('Permanently retained', adv_mapping['review_note'])

    def test_company_isolation(self):
        # Approve mapping under 'Test Corp Alpha'
        update_single_mapping('Custom Consultant Retainer', 'OTHER_EXPENSES', '29', 'N/A', 'Operating', 'Approved')

        # Switch company to 'Test Corp Beta'
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE company_settings SET company_name = 'Test Corp Beta';")
        conn.commit()
        conn.close()

        # Import same ledger under Beta
        save_imported_ledgers([{'ledger_name': 'Custom Consultant Retainer', 'tally_group': 'Current Liabilities', 'closing_net': -10000.0}])
        execute_auto_mapping()

        # Under Beta, company approved mappings should NOT have Alpha's memory if not approved yet
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM company_approved_mappings WHERE company_name = 'Test Corp Beta' AND ledger_name = 'Custom Consultant Retainer';")
        beta_frozen = cursor.fetchone()
        self.assertIsNone(beta_frozen)
        conn.close()


if __name__ == '__main__':
    unittest.main()
