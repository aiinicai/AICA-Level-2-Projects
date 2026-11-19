"""Exercise the EXE without showing an interactive window or enabling feeds."""
from pathlib import Path
import json
import subprocess
import uuid

root=Path(__file__).resolve().parents[1]
exe=root/'dist/FinstockEventScope/FinstockEventScope.exe'
results=[]
for flag,name in [('--smoke-test','backend'),('--ui-smoke-test','ui')]:
    folder=root/'qa-data'/f'packaged-{name}-{uuid.uuid4().hex[:8]}'
    run=subprocess.run([str(exe),flag,'--data-dir',str(folder)],timeout=60)
    report=folder/('smoke-report.json' if name=='backend' else 'ui-smoke-report.json')
    outcome={'check':name,'exit_code':run.returncode,'report':json.loads(report.read_text()) if report.exists() else None}
    results.append(outcome)
    print(json.dumps(outcome))
    if run.returncode or not report.exists():
        log=folder/'eventscope.log'
        if log.exists():print(log.read_text(encoding='utf-8'))
(root/'docs/packaged-test-report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
raise SystemExit(0 if all(item['exit_code']==0 and item['report'] for item in results) else 1)
