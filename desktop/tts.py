"""Local Ukrainian TTS on Ubuntu; bounded subprocess, no external API."""
import json,os,re,signal,subprocess,tempfile,threading,time
from pathlib import Path
from terminal_format import TerminalFormatter
BASE=Path(__file__).resolve().parent.parent

def speech_text(text):
 if not isinstance(text,str) or len(text)>40000:raise ValueError('Відповідь завелика для озвучки.')
 text=re.sub(r'```[\s\S]*?```',' Блок коду. ',text)
 text=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',text)
 fmt=TerminalFormatter();text=fmt.feed(text)+fmt.finish()
 text=re.sub(r'(?m)^\s*#{1,6}\s*','',text)
 text=text.replace('**','').replace('`','')
 if len(text)>20000:raise ValueError('Озвучка підтримує до 20 000 символів. Текст відповіді доступний у чаті.')
 return text.strip()

def synthesize(text,emit,cancelled):
 text=speech_text(text)
 if not text:return
 python=BASE/'.tts-venv/bin/python'
 if not python.exists():raise RuntimeError('Український Piper ще не встановлено: python3 install-tts.py')
 env=os.environ.copy();env.update(OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
 with tempfile.TemporaryFile() as errors:
  process=subprocess.Popen([str(python),str(BASE/'desktop/tts_engine.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,env=env,start_new_session=True)
  ended=threading.Event()
  def watch():
   deadline=time.monotonic()+900
   while not ended.wait(.1):
    if cancelled.is_set() or time.monotonic()>deadline:
     try:os.killpg(process.pid,signal.SIGKILL)
     except ProcessLookupError:pass
     return
  threading.Thread(target=watch,daemon=True).start()
  try:
   process.stdin.write(text.encode());process.stdin.close()
   for line in process.stdout:
    if len(line)>12*1024**2:raise RuntimeError('Завеликий фрагмент озвучки.')
    event=json.loads(line)
    if event.get('type')!='audio':raise RuntimeError('Некоректна відповідь Piper.')
    emit('audio',event['value'])
   if process.wait()!=0:
    errors.seek(0);detail=errors.read()[-1200:].decode(errors='replace')
    raise RuntimeError('Озвучку зупинено.' if cancelled.is_set() else 'Помилка Piper: '+detail)
  finally:
   ended.set()
   if process.poll() is None:
    os.killpg(process.pid,signal.SIGKILL);process.wait()
