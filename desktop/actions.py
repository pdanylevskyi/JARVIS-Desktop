"""Undo only our newly created, unchanged files; never execute model shell commands."""
import hashlib,json,uuid
from pathlib import Path
from .files import Files

STATE=Path(__file__).resolve().parent.parent/'.run/desktop/actions'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def remember(paths):
 STATE.mkdir(parents=True,exist_ok=True)
 record=[{'path':str(Path(p).resolve()),'hash':digest(Path(p))} for p in paths]
 import time
 (STATE/(str(time.time_ns())+'.json')).write_text(json.dumps(record))

def undo(roots,approve):
 STATE.mkdir(parents=True,exist_ok=True)
 records=sorted(STATE.glob('*.json'))
 if not records:return 'Немає створених файлів для скасування.'
 record=records[-1];items=json.loads(record.read_text());files=Files(roots)
 def validate():
  paths=[]
  for item in items:
   p=Path(item['path'])
   for i,root in enumerate(files.roots):
    if p.is_relative_to(root):p=files.path(i,str(p.relative_to(root)),write=True);break
   else:raise ValueError('Файл більше не в дозволених папках.')
   if not p.is_file() or digest(p)!=item['hash']:raise ValueError('Файл змінено або прибрано; автоматичний відкат заборонено.')
   paths.append(p)
  return paths
 paths=validate()
 if not approve('Скасувати створення та перенести в резерв: '+', '.join(map(str,paths))+'?'):return 'Скасування відхилено.'
 paths=validate();backup=STATE/('undo-'+uuid.uuid4().hex);backup.mkdir()
 moved=[]
 try:
  for i,p in enumerate(paths):
   dest=backup/(str(i)+'-'+p.name);p.rename(dest);moved.append((p,dest))
 except BaseException:
  for p,dest in reversed(moved):dest.rename(p)
  raise
 record.rename(backup/'record.json')
 return 'Створення скасовано. Файли можна відновити з '+str(backup)
