"""Select the appropriate workbook workflow for a weekly folder."""
from pathlib import Path
from openpyxl import load_workbook

from engine import prepare as demo_prepare
from excel_report import save as demo_save
from weekly_folder import weekly_files
from weekly_model import prepare_week, WeeklyModel


def prepare(folder, baseline=None):
    folder=Path(folder)
    if not baseline and any(p.is_file() and p.name.casefold()=="starting model.xlsx" for p in folder.iterdir()):
        return demo_prepare(folder)
    files=weekly_files(folder,baseline)
    book=load_workbook(files.baseline,read_only=True,keep_links=False)
    try:
        demo={"Settings","History","Projects","Plan"}<=set(book.sheetnames)
    finally:
        book.close()
    if demo:
        return demo_prepare(folder,dict(files.paths,Model=files.baseline))
    return prepare_week(files)


def save(model,path):
    return model.save(path) if isinstance(model,WeeklyModel) else demo_save(model,path)
