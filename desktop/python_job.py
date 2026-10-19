"""Run generated Python in an offline, disposable Linux filesystem."""
import os,shutil,signal,subprocess,tempfile,time,uuid
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent
LIMIT=64*1024*1024
EXTENSIONS={'.stl','.step','.stp','.obj','.ply','.glb','.gltf','.3mf','.dxf','.pdf','.svg','.png','.json','.txt','.csv','.bin','.mtl','.docx','.xlsx','.pptx','.jpg','.jpeg','.webp','.zip','.html','.xml','.yaml','.yml','.toml'}

def run(files,root,path,cancelled=None):
 source=files.path(root,path)
 if not (source.name.endswith('.py') or source.name.endswith('.py.txt')):raise ValueError('Потрібен Python-файл .py або .py.txt.')
 code=source.read_bytes()
 if len(code)>2_000_000:raise ValueError('Скрипт перевищує 2 МБ.')
 python=BASE/'.cad-venv/bin/python'
 if not python.exists() or not shutil.which('bwrap'):raise RuntimeError('Спочатку встановіть desktop/install-cad.sh на Ubuntu.')
 prefix=subprocess.check_output([str(python),'-c','import sys;print(sys.base_prefix)'],text=True).strip()
 with tempfile.TemporaryDirectory(prefix='jarvis-python-') as directory:
  work=Path(directory);(work/'source.py').write_bytes(code)
  args=['bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv']
  for p in ['/usr','/lib','/lib64',prefix,str(python.parent.parent)]:
   if Path(p).exists():args+=['--ro-bind',p,p]
  args+=['--proc','/proc','--dev','/dev','--dir','/tmp','--bind',str(work),'/work','--chdir','/work']
  for k,v in {'HOME':'/tmp','TMPDIR':'/work','PATH':str(python.parent)+':/usr/bin','LANG':'C.UTF-8','OPENBLAS_NUM_THREADS':'2','OMP_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'}.items():args+=['--setenv',k,v]
  args+=['--',str(python),'-I','/work/source.py']
  args=['prlimit','--as=8589934592','--cpu=120','--fsize='+str(LIMIT),'--nofile=128','--nproc=256','--']+args
  with tempfile.TemporaryFile() as log:
   process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
   started=time.monotonic();reason=None
   try:
    while process.poll() is None:
     entries=list(work.rglob('*'))
     if cancelled is not None and cancelled.is_set():reason='Зупинено.'
     elif time.monotonic()-started>180:reason='Python перевищив 180 секунд.'
     elif len(entries)>200 or sum(p.lstat().st_size for p in entries)>128*1024*1024:reason='Забагато вихідних файлів.'
     if reason:break
     time.sleep(.1)
   finally:
    if process.poll() is None:
     os.killpg(process.pid,signal.SIGKILL);process.wait()
   log.seek(0);output=log.read(12000).decode(errors='replace')
   if reason:raise RuntimeError(reason+'\n'+output)
   if process.returncode:raise RuntimeError('Python завершився з помилкою:\n'+output)
  outputs=[]
  for p in sorted(work.rglob('*')):
   if p==work/'source.py' or p.is_symlink() or not p.is_file() or p.suffix.lower() not in EXTENSIONS:continue
   if p.stat().st_size>LIMIT:raise ValueError('Результат перевищує 64 МБ.')
   outputs.append(p)
  if not outputs:return {'stdout':output,'files':[],'note':'Скрипт виконався, але не створив файлів. Експортуйте результат у поточну папку.'}
  folder=str(Path(path).parent/(source.stem+'-result-'+uuid.uuid4().hex[:8]))
  saved=[]
  for p in outputs:
   relative=str(Path(folder)/p.relative_to(work))
   saved.append(files.save(root,relative,p.read_bytes(),max_bytes=LIMIT)['saved'])
  return {'saved':saved[0],'files':saved,'stdout':output,'note':'Файли створені. Геометрія та придатність для виготовлення потребують перевірки.'}
