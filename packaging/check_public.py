"""Fail closed on personal runtime data in the tracked public source."""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
errors=[]
authors=subprocess.check_output(['git','log','HEAD','--format=%ae%n%ce'],cwd=root).decode().splitlines()
if any(re.search(r'@[^@\s]+\.local$',address,re.I) for address in authors):
 errors.append('Git history contains a machine-local email address')
for name in filter(None,paths):
 p=root/name
 if name.startswith(('config/','.run/','models/','.ssh/')) or p.name in ('settings.json','identity.json','workshop-memory.txt','id_rsa','id_ed25519','id_ecdsa','.env'):
  errors.append(name+': private runtime data')
 try:text=p.read_text()
 except UnicodeError:continue
 if re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|192\.168\.\d+\.\d+|/Users/[A-Za-z0-9._-]+/',text):
  errors.append(name+': potential personal data or credential')
if errors:raise SystemExit('\n'.join(errors))
print('Public source check passed')
