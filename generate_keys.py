"""Owner-only utility. Regenerating invalidates previously issued keys; do not distribute."""
import base64,json,secrets
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
root=Path(__file__).parent
if (root/'license_public.py').exists(): raise SystemExit('Keys already generated. Refusing to replace public key.')
private=Ed25519PrivateKey.generate()
(root/'license_public.py').write_text('PUBLIC_KEY = '+repr(private.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw).hex())+'\n')
def encode(b): return base64.urlsafe_b64encode(b).decode().rstrip('=')
rows=['SMART BILLING MANAGER - OWNER ACTIVATION KEYS','Keep this file private. Do not distribute with the EXE.','Each key starts its validity at activation, replacing the current expiry.','Each key can be used once per installation; offline keys are not globally single-use.','']
for seconds,label in [(300,'5 MINUTES'),(86400,'1 DAY'),(2592000,'30 DAYS')]:
    for i in range(1,5):
        raw=json.dumps({'id':secrets.token_hex(8),'seconds':seconds},separators=(',',':')).encode()
        rows.extend([f'{label} - KEY {i}',encode(raw)+'.'+encode(private.sign(raw)),''])
(root/'OWNER_ACTIVATION_KEYS.txt').write_text('\n'.join(rows))
