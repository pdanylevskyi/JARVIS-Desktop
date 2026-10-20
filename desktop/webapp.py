"""Local WebGL client. Models, documents and speech synthesis stay on Ubuntu."""
import array,base64,json,queue,threading,time
from pathlib import Path
from . import remote
from .app import pcm_level,DATA,CONFIG
from terminal_format import TerminalFormatter

class Bridge:
 def __init__(self):
  DATA.mkdir(exist_ok=True)
  self._settings={'host':'','key':str(Path.home()/'.ssh/id_ed25519')}
  if CONFIG.exists():
   old=json.loads(CONFIG.read_text());self._settings.update({k:old[k] for k in ('host','key','mode') if k in old})
  self._window=None;self._events=queue.Queue();self._cancel=threading.Event();self._closed=threading.Event()
  self._busy=False;self._connected=False;self._history=[];self._image=None;self._attachments=[];self._roots=[]
  self._recording=None;self._pcm=[];self._level=0.;self._started=0.;self._lock=threading.Lock()
  self._approval=threading.Event();self._approved=False;self._approval_id=None
  self._last_voice=0.;self._heard_voice=False;self._transcribing=False;self._voice_cancel=threading.Event()
 def confirm_action(self,request_id,approved):
  if request_id!=self._approval_id:return False
  self._approved=approved is True;self._approval.set();return True
 def _emit(self,kind,value=''):self._events.put({'type':kind,'value':value})
 def dashboard_weather(self,city='',latitude=None,longitude=None):
  from .dashboard import weather
  return weather(city,latitude,longitude)
 def dashboard_geolocation(self):
  import sys
  if sys.platform!='darwin':return None
  from .location import locate
  return locate()
 def dashboard_article(self,url):
  from .news_reader import article
  return article(url)
 def dashboard_news(self):
  from .dashboard import news
  return news()
 def dashboard_export(self,drawing,fmt):
  from .dashboard import export_drawing
  import webview
  if fmt not in ('svg','dxf','pdf','json'):raise ValueError('Невідомий формат.')
  raw=export_drawing(drawing,fmt)
  path=self._window.create_file_dialog(webview.FileDialog.SAVE,save_filename='jarvis-drawing.'+fmt,file_types=(fmt.upper()+' (*.'+fmt+')',))
  if not path:return None
  path=Path(path[0] if isinstance(path,(list,tuple)) else path)
  path.write_bytes(raw)
  return str(path)
 def dashboard_import(self):
  from .dashboard import validate_drawing
  import webview
  result=self._window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=False,file_types=('JARVIS drawing (*.json)',))
  if not result:return None
  p=Path(result[0])
  if p.stat().st_size>5_000_000:raise ValueError('Файл завеликий.')
  return {'shapes':validate_drawing(json.loads(p.read_text()))}
 def dashboard_open_cad(self,name):
  import subprocess,sys,shutil
  if name not in ('FreeCAD','KiCad','PCB Editor','Schematic Editor'):raise ValueError('Невідома програма.')
  if sys.platform=='darwin':
   paths={'FreeCAD':'/Applications/FreeCAD.app','KiCad':'/Applications/KiCad/KiCad.app','PCB Editor':'/Applications/KiCad/PCB Editor.app','Schematic Editor':'/Applications/KiCad/Schematic Editor.app'}
   path=Path(paths[name])
   if not path.exists():raise ValueError(name+' не встановлено.')
   subprocess.run(['/usr/bin/open',str(path)],check=True,timeout=10)
  else:
   path=shutil.which({'PCB Editor':'pcbnew','Schematic Editor':'eeschema'}.get(name,name.lower())) or shutil.which(name)
   if not path:raise ValueError(name+' не встановлено.')
   subprocess.Popen([path])
  return name+' відкрито'
 def dashboard_open_source(self,url):
  from urllib.parse import urlsplit
  import webbrowser
  u=urlsplit(url);host=u.hostname or ''
  if u.scheme!='https' or not (host.endswith('.bbc.com') or host.endswith('.bbc.co.uk') or host=='open-meteo.com'):raise ValueError('Непідтримуване джерело.')
  webbrowser.open(url);return True
 def bootstrap(self):return {'settings':self._settings,'roots':self._roots,'needs_setup':not (DATA/'model-plan.json').exists(),'local_mode':self._settings.get('mode')=='local'}
 def configure(self,host,key):
  if self._busy:raise ValueError('Дочекайтеся відповіді.')
  if not isinstance(host,str) or host.startswith('-') or '@' not in host or any(c.isspace() for c in host):raise ValueError('Некоректна SSH-адреса.')
  if not isinstance(key,str) or not Path(key).expanduser().is_file():raise ValueError('Файл SSH-ключа не знайдено.')
  self._emit('capabilities',{'local_text':False})
  self._settings={'host':host,'key':key};CONFIG.write_text(json.dumps(self._settings,ensure_ascii=False,indent=2))
  self._connected=False;return self._launch({'operation':'status'})
 def use_local(self):
  self._settings['mode']='local';CONFIG.write_text(json.dumps(self._settings))
  return self._launch({'operation':'status'})
 def install_local(self):
  with self._lock:
   if self._busy:return False
   self._busy=True
  self._cancel.clear();self._emit('busy',True)
  def work():
   try:
    from .local_runtime import install,stop
    install(self._emit,self._cancel)
    from .local_runtime import ROOT
    self._roots=[str(ROOT)];self._emit('roots',self._roots)
    self._settings['mode']='local';CONFIG.write_text(json.dumps(self._settings))
    self._connected=True;self._emit('capabilities',{'local_text':True});self._emit('connected',True);self._emit('status','Local model ready')
   except Exception as exc:
    from .local_runtime import stop
    stop();self._emit('error',str(exc))
   finally:self._busy=False;self._emit('busy',False)
  threading.Thread(target=work,daemon=True).start();return True
 def scan_hardware(self):
  from .hardware import scan
  return scan()
 def recommend_models(self,profile):
  from .hardware import recommend
  return recommend(profile)
 def open_model_source(self,repository,filename):
  import webbrowser
  from urllib.parse import quote
  catalog=json.loads(Path(__file__).with_name('model_catalog.json').read_text())['models']
  model=next((m for m in catalog if m['repository']==repository and m['filename']==filename),None)
  if not model:raise ValueError('Unknown catalog model.')
  webbrowser.open('https://huggingface.co/'+repository+'/blob/'+model['revision']+'/'+quote(filename));return True
 def save_model_plan(self,repository,filename,context,profile):
  from .hardware import recommend
  models=recommend(profile)['models'];model=next((m for m in models if m['repository']==repository and m['filename']==filename),None)
  if not model or type(context) is not int or not 16384<=context<=model['estimated_max_context']:raise ValueError('Invalid model plan.')
  (DATA/'model-plan.json').write_text(json.dumps({'model':model,'context':context,'profile':profile},indent=2));return True
 def context_settings(self):
  if not self._connected:raise ValueError('Connect to Ubuntu first.')
  return self._launch({'operation':'context_info'})
 def set_context(self,value):
  if not self._connected:raise ValueError('Connect to Ubuntu first.')
  if type(value) is not int:raise ValueError('Context must be a whole number.')
  return self._launch({'operation':'set_context','context':value})
 def choose_key(self):
  import webview
  result=self._window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=False)
  return result[0] if result else None
 def attach_image(self):
  if self._busy:return None
  import webview
  result=self._window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=True)
  if not result:return None
  if len(result)>8:raise ValueError('Максимум 8 файлів за раз.')
  attachments=[];total=0
  for value in result:
   path=Path(value)
   if not path.is_file():raise ValueError('Оберіть файли, не папки.')
   if path.stat().st_size>10*1024*1024:raise ValueError('Вкладення разом мають бути до 10 МБ.')
   with path.open('rb') as stream:raw=stream.read(10*1024*1024+1)
   total+=len(raw)
   if total>10*1024*1024:raise ValueError('Вкладення разом мають бути до 10 МБ.')
   attachments.append({'name':path.name,'data':base64.b64encode(raw).decode()})
  self._image=None;self._attachments=attachments
  label=', '.join(a['name'] for a in attachments)
  self._emit('attachment',label);return label
 def tool_catalog(self):
  from .files import TOOLS
  return [{'name':t['function']['name'],'description':t['function']['description']} for t in TOOLS]
 def remove_image(self):
  if not self._busy:self._image=None;self._attachments=[];self._emit('attachment','')
 def clear(self):
  if self._busy or self._recording:return False
  self._history=[];self._image=None;self._attachments=[];self._emit('clear');return True
 def set_roots(self,text):
  return self._launch({'operation':'set_roots','roots':[s.strip() for s in text.splitlines() if s.strip()]})
 def save_memory(self,before,after):return self._launch({'operation':'memory_save','before':before,'after':after})
 def send(self,prompt,mode,search,voice,text,mac_agent=False):
  if self._busy or self._recording:return False
  voice=False;text=True  # Speech output is disabled; retain legacy call compatibility.
  if not isinstance(prompt,str) or len(prompt)>12000:raise ValueError('Максимум 12 000 символів.')
  prompt=prompt.strip() or ('Прочитай прикріплені файли та поясни їхній зміст українською.' if self._attachments else 'Опиши це зображення українською.' if self._image else '')
  if not prompt:return False
  if (mac_agent or prompt.startswith('/mac ')) and self._attachments:raise ValueError('Вкладення надсилаються в чат Ubuntu. Вимкніть «Агент Mac», щоб прочитати файли.')
  if mac_agent or prompt.startswith('/mac '):
   if not self._connected:raise ValueError('Спочатку підключіть Ubuntu.')
   return self._run_mac(prompt[5:].strip() if prompt.startswith('/mac ') else prompt)
  from .local_browser import open_requested
  local_result=None if self._attachments else open_requested(prompt)
  if local_result:
   self._emit('user',{'text':prompt,'show_text':True,'voice':False});self._emit('text',local_result);self._emit('generation_done');return True
  if not self._connected:raise ValueError('Спочатку підключіть Ubuntu.')
  if prompt=='/clear':return self.clear()
  if prompt=='/exit':self._window.destroy();return True
  if mode not in ('normal','flash','long'):raise ValueError('Невідомий режим.')
  if not prompt.startswith('/') and mode!='normal':prompt='/'+mode+' '+prompt
  payload={'operation':'chat','prompt':prompt,'history':self._history,'search_enabled':bool(search)}
  if self._image:payload['image']=dict(self._image)
  if self._attachments:payload['attachments']=list(self._attachments)
  self._emit('user',{'text':prompt,'show_text':bool(text),'voice':bool(voice)})
  return self._launch(payload,speak=bool(voice))
 def _run_mac(self,prompt):
  if not prompt:raise ValueError('Додайте завдання для Mac.')
  with self._lock:
   if self._busy:return False
   self._busy=True
  self._cancel.clear();self._emit('user',{'text':prompt,'show_text':True,'voice':False});self._emit('busy',True)
  def work():
   try:
    from .mac_control import MacControl
    from .mac_agent import run
    backend=MacControl()
    def approve(description):
     import uuid
     self._approved=False;self._approval.clear();self._approval_id=uuid.uuid4().hex
     self._emit('confirm',{'id':self._approval_id,'description':description})
     deadline=time.monotonic()+110
     while not self._approval.wait(.1):
      if self._cancel.is_set() or time.monotonic()>deadline:break
     self._approval_id=None;self._emit('confirm_closed')
     return self._approved and not self._cancel.is_set()
    def planner(prompt,observation,history):
     result=[]
     def receive(kind,value):
      if kind=='mac_action':result.append(value)
      elif kind=='error':raise RuntimeError(value)
     remote.request(dict(self._settings),{'operation':'mac_plan','prompt':prompt,'observation':observation,'history':history},receive,self._cancel)
     if len(result)!=1:raise RuntimeError('Сервер не повернув коректну дію.')
     return result[0]
    self._emit('progress','Режим Mac: екран передається лише на ваш Ubuntu. Стоп — кнопкою або курсором у верхній лівий кут.')
    run(prompt,backend,planner,approve,self._emit,self._cancel)
   except Exception as exc:self._emit('error',str(exc))
   finally:self._busy=False;self._emit('generation_done');self._emit('busy',False)
  threading.Thread(target=work,daemon=True).start();return True
 def _launch(self,payload,speak=False):
  with self._lock:
   if self._busy:return False
   self._busy=True
  self._cancel.clear();self._emit('busy',True)
  def work():
   formatter=TerminalFormatter(live=True);answer='';final_answer=None;failed=False;downloads=[]

   speech=None  # Never synthesize output, including calls from older clients.
   def receive(kind,value):
    nonlocal formatter,answer,final_answer,failed
    if kind=='attachments_received':
     self._attachments=[];self._emit('attachment','');return
    if kind=='text':
     clean=formatter.feed(value);answer+=clean;self._emit('text',clean)
     if speech:speech.feed(clean)
     return
    if kind=='confirm':
     import uuid
     self._approved=False;self._approval.clear();self._approval_id=uuid.uuid4().hex
     self._emit('confirm',{'id':self._approval_id,'description':value})
     deadline=time.monotonic()+110
     while not self._approval.wait(.1):
      if self._cancel.is_set() or time.monotonic()>deadline:break
     self._approval_id=None;self._emit('confirm_closed')
     return self._approved and not self._cancel.is_set()
    if kind in ('action','action_result') and speech:
     labels={'list_files':'Переглядаю папку.','read_document':'Читаю документ.','write_text':'Готую запис файлу.','create_document':'Готую документ.','create_drawing':'Готую креслення.','create_cad_drawing':'Готую креслення.'}
     speech.enqueue(labels.get(value,value) if kind=='action' else ('Дію не виконано.' if 'помилка' in value else 'Дію виконано.'))
    if kind in ('translation_begin','replace_answer'):
     formatter=TerminalFormatter(live=True);answer='';self._emit('answer_reset')
     if speech:speech.reset()
     if kind=='replace_answer':receive('text',value)
     return
    if kind=='history':
     from .context_window import retain
     self._history=retain(self._history+value)
     final_answer=next((m['content'] for m in reversed(value) if m['role']=='assistant'),None)
     return
    if kind=='saved' and value not in downloads:downloads.append(value)
    if kind=='roots':self._roots=value
    if kind=='connected':self._connected=value
    if kind=='status' and value.startswith('Ubuntu підключено'):self._connected=True;self._emit('connected',True)
    if kind=='error':failed=True
    if kind!='done':self._emit(kind,value)
   try:
    remote.request(dict(self._settings),payload,receive,self._cancel)
    tail=formatter.finish();answer+=tail
    if tail:self._emit('text',tail)
    if speech:speech.feed(tail)
    self._emit('generation_done')
    from .transfers import download
    for path in downloads:
     if self._cancel.is_set():break
     self._emit('status','Завантажую файл у Downloads…')
     try:self._emit('downloaded',download(dict(self._settings),path,self._cancel))
     except Exception as exc:self._emit('warning','Файл залишився на Ubuntu; завантаження не вдалося: '+str(exc))
   except Exception as exc:failed=True;self._emit('error',str(exc))
   finally:
    if speech:
     if failed or self._cancel.is_set():speech.reset()
     speech.finish()
    self._busy=False;self._emit('busy',False)
  threading.Thread(target=work,daemon=True).start();return True
 def stop(self):
  self._cancel.set();self._emit('stop_audio')
 def _transcribe_audio(self,pcm):
  self._transcribing=True;self._voice_cancel.clear();self._emit('transcribing',True)
  def work():
   try:
    def receive(kind,value):
     if kind in ('transcript','error','warning'):self._emit(kind,value)
    remote.request(dict(self._settings),{'operation':'transcribe','audio':base64.b64encode(pcm).decode()},receive,self._voice_cancel)
   except Exception as exc:self._emit('error',str(exc))
   finally:self._transcribing=False;self._emit('transcribing',False)
  threading.Thread(target=work,daemon=True).start();return True
 def record_toggle(self):
  if self._transcribing:return False
  if not self._connected:raise ValueError('Спочатку підключіть Ubuntu.')
  if self._recording:
   stream=self._recording;self._recording=None;stream.stop();stream.close()
   self._level=0.;self._emit('recording',False)
   pcm=b''.join(self._pcm);self._pcm=[]
   return self._transcribe_audio(pcm)
  import sounddevice as sd
  self._emit('stop_audio');self._pcm=[]
  self._heard_voice=False;self._last_voice=time.monotonic()
  def capture(data,frames,timing,status):
   chunk=bytes(data)
   if len(self._pcm)<1200:self._pcm.append(chunk)
   self._level=pcm_level(chunk)
   if self._level>.035:self._heard_voice=True;self._last_voice=time.monotonic()
  stream=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',blocksize=800,callback=capture)
  try:stream.start()
  except Exception:stream.close();raise
  self._recording=stream;self._started=time.monotonic();self._emit('recording',True)
  return True
 def _pump(self):
  while not self._closed.wait(.04):
   events=[]
   try:
    while len(events)<150:events.append(self._events.get_nowait())
   except queue.Empty:pass
   if self._recording:
    events.append({'type':'level','value':{'level':self._level,'seconds':round(time.monotonic()-self._started,1)}})
    if time.monotonic()-self._started>=60:
     try:self.record_toggle()
     except Exception as exc:self._emit('error',str(exc))
   if events:
    try:self._window.evaluate_js('window.jarvisEvents('+json.dumps(events,ensure_ascii=True)+')')
    except Exception:
     if self._closed.is_set():break
 def _close(self):
  self._closed.set();self._cancel.set();self._voice_cancel.set();self._approval.set()
  from .local_runtime import stop
  stop()
  if self._recording:self._recording.stop();self._recording.close();self._recording=None

def main(self_test=False):
 import webview
 result={'ok':False}
 api=Bridge();ui=Path(__file__).parent/'ui/index.html'
 window=webview.create_window('J.A.R.V.I.S.',str(ui),js_api=api,width=1120,height=940,min_size=(820,700),background_color='#000000',text_select=True)
 api._window=window;window.events.closed+=api._close
 def loaded():
  threading.Thread(target=api._pump,daemon=True).start()
  if self_test:
   def check():
    time.sleep(1)
    try:
     if sys.platform=='darwin':
      from . import location  # Import only; never request location in self-test.
     assert window.evaluate_js('window.reactorReady === true')
     assert window.evaluate_js('document.querySelectorAll("[data-mode]").length')==3
     assert window.evaluate_js('document.querySelectorAll(".module-card").length')==6
     assert window.evaluate_js('''(()=>{window.jarvisDashboard.open('electronics');document.getElementById('calculate').click();return document.getElementById('calc-result').textContent.includes('0,12')})()''')
     assert window.evaluate_js('''(()=>{window.jarvisDashboard.open('draft');return document.getElementById('drawing').width===1188})()''')
     window.evaluate_js("window.jarvisDashboard.open('home')")
     result['ok']=True
     print('JARVIS WebGL UI ready; no model inference',flush=True)
    finally:window.destroy()
   threading.Thread(target=check,daemon=True).start()
 window.events.loaded+=loaded
 import sys
 webview.start(debug=False,private_mode=True,gui='qt' if sys.platform.startswith('linux') else None)
 if self_test and not result['ok']:raise RuntimeError('WebGL self-test failed')

if __name__=='__main__':main()
