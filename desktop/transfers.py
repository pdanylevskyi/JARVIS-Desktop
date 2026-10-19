"""Bounded SSH file transfer; downloaded files are never executed locally."""
import base64,hashlib,os,re,tempfile
from pathlib import Path
LIMIT=64*1024*1024

def emit_file(path,roots,emit):
 from .files import Files
 files=Files(roots);p=Path(path)
 for i,root in enumerate(files.roots):
  if p.is_relative_to(root):p=files.path(i,str(p.relative_to(root)));break
 else:raise ValueError('Файл поза дозволеними папками.')
 if not p.is_file() or p.stat().st_size>LIMIT:raise ValueError('Потрібен файл до 64 МБ.')
 with p.open('rb') as stream:
  size=os.fstat(stream.fileno()).st_size
  emit('file_begin',{'name':p.name,'size':size})
  digest=hashlib.sha256();count=0
  while block:=stream.read(65536):
   count+=len(block)
   if count>LIMIT:raise ValueError('Файл перевищує 64 МБ.')
   digest.update(block);emit('file_chunk',base64.b64encode(block).decode())
  emit('file_end',{'size':count,'sha256':digest.hexdigest()})

def download(settings,path,cancelled,destination=None):
 from .remote import request
 folder=Path(destination) if destination else Path.home()/'Downloads'
 folder.mkdir(parents=True,exist_ok=True)
 header=None;finished=False;count=0;digest=hashlib.sha256()
 fd,temp=tempfile.mkstemp(prefix='.jarvis-',suffix='.part',dir=folder)
 try:
  with os.fdopen(fd,'wb') as out:
   def receive(kind,value):
    nonlocal header,finished,count
    if kind=='error':raise RuntimeError(value)
    if kind=='file_begin':
     if header is not None or not isinstance(value['size'],int) or not 0<=value['size']<=LIMIT:raise ValueError('Некоректний розмір.')
     name=value['name']
     if not isinstance(name,str) or not name or name.startswith('.') or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise ValueError('Некоректна назва.')
     header=value
    elif kind=='file_chunk':
     if header is None or finished:raise ValueError('Некоректний порядок даних.')
     block=base64.b64decode(value,validate=True);count+=len(block)
     if count>header['size'] or count>LIMIT:raise ValueError('Завеликий файл.')
     digest.update(block);out.write(block)
    elif kind=='file_end':
     if header is None or count!=header['size'] or count!=value['size'] or digest.hexdigest()!=value['sha256']:raise ValueError('Контрольна сума не збігається.')
     finished=True
   request(settings,{'operation':'download_file','path':path},receive,cancelled)
   if not finished or (cancelled is not None and cancelled.is_set()):raise RuntimeError('Завантаження не завершене.')
  stem=Path(header['name']).stem;suffix=Path(header['name']).suffix
  for n in range(10000):
   target=folder/(header['name'] if n==0 else f'{stem} ({n}){suffix}')
   try:os.link(temp,target);break
   except FileExistsError:continue
  else:raise RuntimeError('Не вдалося обрати вільну назву.')
  return str(target)
 finally:Path(temp).unlink(missing_ok=True)
