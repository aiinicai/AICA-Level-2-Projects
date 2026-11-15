"""Build source-only release from an explicit allowlist; never bundle uploads/private data."""
from pathlib import Path
import hashlib,zipfile,json
ROOT=Path(__file__).resolve().parents[1]
FILES=[]
for pattern in ('*.py','*.pyw','*.bat','*.vbs','requirements*.txt','README.md'):
    FILES.extend(ROOT.glob(pattern))
FILES.extend((ROOT/'tests').glob('test_*.py'))
FILES.extend((ROOT/'tools').glob('*.py'))
for name in ('SOURCE_PARITY_2.1.0.md','FORMULA_REVIEW.md','QA_RESULTS.md','GUI_ACCEPTANCE_2.1.1.md','DESKTOP_SMOKE_TEST.md','input_sha256.json','reference_structure_2.1.0.json','test_results.xml'):
    FILES.append(ROOT/'docs'/name)
for p in (ROOT/'examples').iterdir():
    if '2.1.2' in p.name or p.name in ('SYNTHETIC_valuation_first.txt','SYNTHETIC_valuation_second_ambiguous.txt','SYNTHETIC_ITR_2025_26.txt','SYNTHETIC_computation_2025_26.txt','SYNTHETIC_noisy_passport.txt','SAMPLE_signature.jpg','SAMPLE_signature.png','SAMPLE_whole_page_letterpad.png'):
        FILES.append(p)
FILES=sorted(set(FILES),key=lambda p:p.relative_to(ROOT).as_posix())
manifest=ROOT/'MANIFEST.sha256'
manifest.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in FILES),encoding='utf-8')
archive=ROOT/'Net_Asset_Report_2.1.2_source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in FILES+[manifest]:z.write(p,p.relative_to(ROOT).as_posix())
print(json.dumps(dict(path=str(archive),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(FILES)+1),indent=2))
