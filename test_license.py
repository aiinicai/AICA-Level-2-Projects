import tempfile,json,time,unittest
from pathlib import Path
from unittest.mock import patch
from licensing import License,TRIAL_END

class LicenseTests(unittest.TestCase):
    def test_activation_and_expiry(self):
        keys=[line for line in Path('OWNER_ACTIVATION_KEYS.txt').read_text().splitlines() if '.' in line and len(line)>100]
        self.assertEqual(len(keys),12)
        with tempfile.TemporaryDirectory() as temp:
            with patch('licensing.time.time',return_value=TRIAL_END-100):
                lic=License(temp); self.assertEqual(lic.remaining(),100)
                for index,key in enumerate(keys):
                    lic.activate(key); self.assertEqual(round(lic.remaining()),[300,86400,2592000][index//4])
                    with self.assertRaises(ValueError): lic.activate(key)
                with self.assertRaises(ValueError): lic.activate(keys[0][:-4]+'abcd')
            with patch('licensing.time.time',return_value=TRIAL_END+2592000): self.assertEqual(lic.remaining(),0)
            with patch('licensing.time.time',return_value=TRIAL_END-1000):
                lic.checkpoint(); self.assertEqual(lic.remaining(),0)

if __name__=='__main__': unittest.main(verbosity=2)
