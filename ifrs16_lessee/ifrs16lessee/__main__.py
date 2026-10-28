"""python -m ifrs16lessee            -> start the desktop app
python -m ifrs16lessee --sample-report out.xlsx [--company "Name"]   -> build the sample lease and export the Excel workbook (no UI needed)
python -m ifrs16lessee --version"""
import sys


def cli(argv):
    if '--version' in argv:
        from . import __version__
        print(__version__); return 0
    if '--sample-report' in argv:
        from .reports import export_workbook
        from .sample import load_sample
        from .store import Store
        out = argv[argv.index('--sample-report') + 1]
        company = argv[argv.index('--company') + 1] if '--company' in argv else 'Sample Company'
        s = Store()
        ref = load_sample(s)
        export_workbook(s, [ref], out, company)
        print('Wrote', out)
        return 0
    try:
        from .ui.app import main
    except ImportError as e:
        print('The desktop UI needs PySide6 (pip install -r requirements.txt).\n', e)
        return 2
    return main()


if __name__ == '__main__':
    sys.exit(cli(sys.argv[1:]))
