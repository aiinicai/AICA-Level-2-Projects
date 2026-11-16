"""Preserve installed dependency metadata and available licence texts."""
from importlib.metadata import distributions
from pathlib import Path
import json
import shutil

root = Path(__file__).resolve().parents[1] / 'docs' / 'licenses'
root.mkdir(parents=True, exist_ok=True)
inventory = []
for dist in distributions():
    name = dist.metadata.get('Name', 'unknown')
    inventory.append({'name': name, 'version': dist.version,
                      'license': dist.metadata.get('License-Expression') or dist.metadata.get('License'),
                      'homepage': dist.metadata.get('Home-page')})
    for entry in dist.files or []:
        path = Path(str(entry))
        if not any(part.endswith(('.dist-info', '.egg-info')) for part in path.parts):
            continue
        if not any(token in path.name.lower() for token in ('license', 'licence', 'copying', 'notice')):
            continue
        source = Path(dist.locate_file(entry))
        if source.is_file():
            target = root / name / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
(root / 'inventory.json').write_text(json.dumps(sorted(inventory, key=lambda x:x['name'].lower()), indent=2), encoding='utf-8')
print(f'Preserved dependency inventory for {len(inventory)} distributions')
