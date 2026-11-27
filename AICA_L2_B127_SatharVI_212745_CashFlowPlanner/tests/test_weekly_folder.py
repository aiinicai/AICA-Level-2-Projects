import shutil
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from planner_workflow import prepare
from sources import InputError
from weekly_folder import weekly_files


class DateSelectionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.prev=self.root/"2026"/"10. Oct-26"/"30. 31-10-2026"
        self.week=self.root/"2026"/"11. Nov-26"/"31. 07-11-2026"
        self.prev.mkdir(parents=True)
        self.week.mkdir(parents=True)
        self.seed=self.prev/"CF-01-11-2026.xlsx"
        shutil.copy2(APP/"demo_week"/"Starting Model.xlsx",self.seed)
        for p in (APP/"demo_week").iterdir():
            if p.name!="Starting Model.xlsx":
                shutil.copy2(p,self.week/(p.stem+"-08-11-2026"+p.suffix))
        (self.week/"CF-08-11-2026.xlsx").write_bytes(b"must not be read")
        (self.week/"~$CF-01-11-2026.xlsx").touch()

    def test_previous_folder_across_month_boundary(self):
        files=weekly_files(self.week)
        self.assertEqual(files.baseline,self.seed)
        self.assertEqual(len(files.paths),8)
        self.assertEqual(files.original.name,"CF-08-11-2026.xlsx")

    def test_portable_folder_and_existing_output(self):
        local=self.week/self.seed.name
        shutil.copy2(self.seed,local)
        self.assertEqual(weekly_files(self.week).baseline,local)
        self.assertEqual(float(prepare(self.week).closing["2026-12 forecast"]),-7050.75)

    def test_ambiguous_then_explicit_selection(self):
        for name in ("CF-01-11-2026.xlsx","CF-02-11-2026.xlsx"):
            shutil.copy2(self.seed,self.week/name)
        with self.assertRaisesRegex(InputError,"Multiple prior"):
            weekly_files(self.week)
        self.assertEqual(weekly_files(self.week,self.seed).baseline,self.seed)

    def test_mixed_snapshots(self):
        (self.week/"LC-08-11-2026.xlsx").rename(self.week/"LC-09-11-2026.xlsx")
        with self.assertRaisesRegex(InputError,"different snapshot dates"):
            weekly_files(self.week)

    def test_same_week_rejected_as_explicit_baseline(self):
        with self.assertRaisesRegex(InputError,"prior dated"):
            weekly_files(self.week,self.week/"CF-08-11-2026.xlsx")
