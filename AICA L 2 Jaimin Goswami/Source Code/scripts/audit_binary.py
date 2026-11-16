from pathlib import Path
import pefile
root=Path(__file__).resolve().parents[1]/'dist/FinstockEventScope/_internal'
lookup={p.name.lower():p for p in root.rglob('*.dll')}
cache={}
for file in [root/'PySide6/QtCore.pyd',root/'PySide6/Qt6Core.dll',root/'PySide6/pyside6.abi3.dll',root/'shiboken6/shiboken6.abi3.dll']:
    pe=pefile.PE(str(file))
    for imp in pe.DIRECTORY_ENTRY_IMPORT:
        name=imp.dll.decode().lower()
        target=lookup.get(name)
        if not target:continue
        if name not in cache:
            dependency=pefile.PE(str(target),max_symbol_exports=100000)
            cache[name]={x.name for x in dependency.DIRECTORY_ENTRY_EXPORT.symbols if x.name}
        missing=[x.name.decode() for x in imp.imports if x.name and x.name not in cache[name]]
        if missing:print(file.name,name,'MISSING:',missing)
