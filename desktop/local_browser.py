"""Explicit local browser requests only; never invoked by model/tool output."""
import re
from urllib.parse import quote,urlsplit

def requested_url(prompt):
 text=prompt.strip()
 if text.startswith('/google '):
  query=text.partition(' ')[2].strip()
  return 'https://www.google.com/search?q='+quote(query) if query else None
 if text.startswith('/open '):
  url=text.partition(' ')[2].strip();parts=urlsplit(url)
  if parts.scheme not in ('https','http') or not parts.hostname or parts.username or parts.password:
   raise ValueError('Для /open потрібне звичайне HTTP(S) посилання без пароля.')
  return url
 # Only a direct request to open Google on this computer; no general document instructions.
 if not re.search(r'\b(?:відкрий|відкрити|open)\b',text,re.I):return None
 if not re.search(r'\b(?:google|гугл\w*)\b',text,re.I):return None
 if not re.search(r'(?:на\s+(?:моєму|цьому)\s+(?:комп\w*|мак\w*)|\bmac\b|\bлокально\b)',text,re.I):return None
 match=re.search(r'(?:знайди|пошукай|шукай|search\s+for)\s+(?:там\s+)?(.+)',text,re.I)
 if match:
  query=match.group(1).strip().rstrip('.!?')
  return 'https://www.google.com/search?q='+quote(query)
 return 'https://www.google.com/'

def open_requested(prompt,opener=None):
 url=requested_url(prompt)
 if url is None:return None
 if opener is None:
  import webbrowser,sys,subprocess
  def opener(url,new=2):
   if sys.platform=='darwin':
    subprocess.run(['/usr/bin/open','-a','Google Chrome',url],check=True,timeout=10);return True
   return webbrowser.open(url,new=new)
 if not opener(url,new=2):raise RuntimeError('Не вдалося відкрити браузер на цьому комп’ютері.')
 return 'Відкрив у браузері на цьому комп’ютері: '+url
