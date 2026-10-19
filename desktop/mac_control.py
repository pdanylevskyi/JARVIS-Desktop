"""macOS desktop adapter. No shell execution or arbitrary Python from models."""
import base64,io,subprocess,time,sys

class MacControl:
 def __init__(self):
  if sys.platform!='darwin':raise RuntimeError('Цей режим призначений для macOS.')
  import Quartz,ApplicationServices,pyautogui
  self.q=Quartz;self.ax=ApplicationServices;self.mouse=pyautogui
  self.mouse.FAILSAFE=True;self.mouse.PAUSE=.15
  if not self.ax.AXIsProcessTrusted():
   self.ax.AXIsProcessTrustedWithOptions({self.ax.kAXTrustedCheckOptionPrompt:True})
   raise RuntimeError('Дозвольте JARVIS: Налаштування macOS → Конфіденційність і безпека → Універсальний доступ. Потім перезапустіть JARVIS.')
  if not self.q.CGPreflightScreenCaptureAccess():
   self.q.CGRequestScreenCaptureAccess()
   raise RuntimeError('Дозвольте JARVIS запис екрана в налаштуваннях macOS і перезапустіть застосунок.')
 def observe(self):
  from AppKit import NSWorkspace
  app=NSWorkspace.sharedWorkspace().frontmostApplication()
  screenshot=self.mouse.screenshot();screenshot.thumbnail((1440,1000));out=io.BytesIO();screenshot.convert('RGB').save(out,format='JPEG',quality=75)
  windows=self.q.CGWindowListCopyWindowInfo(self.q.kCGWindowListOptionOnScreenOnly,self.q.kCGNullWindowID) or []
  front=next((w.get('kCGWindowNumber') for w in windows if w.get('kCGWindowOwnerPID')==int(app.processIdentifier()) and w.get('kCGWindowLayer')==0),None)
  return {'window':front,'app':str(app.localizedName()),'pid':int(app.processIdentifier()),'image':base64.b64encode(out.getvalue()).decode(),'size':screenshot.size}
 def restore(self,observation):
  from AppKit import NSRunningApplication,NSApplicationActivateIgnoringOtherApps
  app=NSRunningApplication.runningApplicationWithProcessIdentifier_(observation['pid'])
  if not app:raise RuntimeError('Цільову програму закрито.')
  app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps);time.sleep(.4)
 def unchanged(self,observation):
  from PIL import Image,ImageChops,ImageStat
  latest=self.observe()
  if latest['pid']!=observation['pid'] or latest.get('window')!=observation.get('window'):return False
  before=Image.open(io.BytesIO(base64.b64decode(observation['image']))).convert('RGB').resize((160,100))
  after=Image.open(io.BytesIO(base64.b64decode(latest['image']))).convert('RGB').resize((160,100))
  return sum(ImageStat.Stat(ImageChops.difference(before,after)).mean)/3<2
 def navigation_target(self,action,observation):
  if action['kind']!='click':return False
  from AppKit import NSWorkspace
  from .mac_navigation import safe_target
  if int(NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier())!=observation.get('pid'):return False
  try:
   width,height=self.mouse.size()
   system=self.ax.AXUIElementCreateSystemWide()
   err,element=self.ax.AXUIElementCopyElementAtPosition(system,action['x']*width,action['y']*height,None)
   if err or element is None:return False
   def attr(e,key):
    err,value=self.ax.AXUIElementCopyAttributeValue(e,key,None)
    return None if err else value
   role=attr(element,'AXRole');ancestors=[];parent=element
   for _ in range(40):
    parent=attr(parent,'AXParent')
    if parent is None:break
    value=attr(parent,'AXRole')
    if not value:return False
    ancestors.append(value)
    if value=='AXApplication':break
   if not ancestors or ancestors[-1]!='AXApplication':return False
   return safe_target(role,ancestors)
  except Exception:return False
 def prepare_trash(self,a):
  from .trash_ops import snapshot
  a['_confirmed_snapshot']=snapshot(a['path']);a['path']=a['_confirmed_snapshot']['path']
 def execute(self,a):
  from .mac_agent import validate
  validate(a);self.mouse.failSafeCheck();kind=a['kind'];width,height=self.mouse.size()
  if getattr(self,'cancelled',None) is not None and self.cancelled.is_set():raise RuntimeError('Зупинено.')
  point=lambda x,y:(min(width-1,int(x*width)),min(height-1,int(y*height)))
  if kind=='trash_file':
   from .trash_ops import trash_mac
   return trash_mac(a['path'],a.get('_confirmed_snapshot'))
  if kind=='click':self.mouse.click(*point(a['x'],a['y']))
  elif kind=='double_click':self.mouse.doubleClick(*point(a['x'],a['y']),interval=.12)
  elif kind=='drag':self.mouse.moveTo(*point(a['x'],a['y']));self.mouse.dragTo(*point(a['to_x'],a['to_y']),duration=.6)
  elif kind=='scroll':self.mouse.scroll(a['amount'])
  elif kind=='key':self.mouse.hotkey(*a['keys'])
  elif kind=='type':
   # Unicode keyboard events, no clipboard replacement or shell interpreter.
   for offset in range(0,len(a['text']),32):
    self.mouse.failSafeCheck()
    if getattr(self,'cancelled',None) is not None and self.cancelled.is_set():raise RuntimeError('Зупинено.')
    text=a['text'][offset:offset+32]
    for down in (True,False):
     event=self.q.CGEventCreateKeyboardEvent(None,0,down)
     self.q.CGEventKeyboardSetUnicodeString(event,len(text.encode('utf-16-le'))//2,text)
     self.q.CGEventPost(self.q.kCGHIDEventTap,event)
  elif kind=='open_app':subprocess.run(['/usr/bin/open','-a','Google Chrome' if a['app'].casefold() in ('safari','google','chrome','google chrome') else a['app']],check=True,timeout=10)
  elif kind=='open_url':
   subprocess.run(['/usr/bin/open','-a','Google Chrome',a['url']],check=True,timeout=10)
  elif kind=='wait':time.sleep(1)
