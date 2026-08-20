import unittest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.app import app

class TestNotesAPI(unittest.TestCase):
    def test_notes_generation(self):
        with app.test_client() as client:
            r = client.get('/api/notes')
            self.assertEqual(r.status_code, 200)
            data = r.get_json()
            notes = data['notes']
            self.assertEqual(len(notes), 29)

if __name__ == '__main__':
    unittest.main()

