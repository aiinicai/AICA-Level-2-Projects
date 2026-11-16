"""Package only explicit project assets; exclude credentials, local databases and QA data."""
from pathlib import Path
import hashlib
import shutil
import zipfile

root=Path(__file__).resolve().parents[1]
out=root/'release'
out.mkdir(exist_ok=True)
source=out/'FinstockEventScope-Source.zip'
binary=out/'FinstockEventScope-Windows.zip'
files=['README.md','launch.py','pyproject.toml','requirements.txt','requirements-dev.txt','requirements-lock.txt','FinstockEventScope.spec','.gitignore','.env.example']
folders=['app','assets','docs','migrations','sample_data','scripts','tests']
shutil.copytree(root/'docs',root/'dist/FinstockEventScope/_internal/docs',dirs_exist_ok=True)
with zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name in files:
        archive.write(root/name,'FinstockEventScope/'+name)
    for folder in folders:
        for path in sorted((root/folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc','.db','.log'}:
                archive.write(path,'FinstockEventScope/'+path.relative_to(root).as_posix())
with zipfile.ZipFile(binary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in sorted((root/'dist'/'FinstockEventScope').rglob('*')):
        if path.is_file():
            archive.write(path,path.relative_to(root/'dist').as_posix())
    archive.write(root/'README.md','FinstockEventScope/README.md')
    for path in sorted((root/'docs').rglob('*')):
        if path.is_file():archive.write(path,'FinstockEventScope/docs/'+path.relative_to(root/'docs').as_posix())
lines=[]
for path in (source,binary):
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    lines.append(f'{digest}  {path.name}')
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
    print(f'{path.name}: {path.stat().st_size:,} bytes; archive integrity OK')
(out/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
