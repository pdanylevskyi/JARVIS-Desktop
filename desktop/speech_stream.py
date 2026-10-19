"""Ordered sentence audio, synthesized concurrently with incoming model text."""
import queue,re,threading
from . import remote

class SpeechStream:
 def __init__(self,settings,emit,cancel):
  self.settings=dict(settings);self.emit=emit;self.cancel=cancel
  self.queue=queue.Queue();self.buffer='';self.total=0;self.epoch=0;self.code=False
  self.thread=threading.Thread(target=self.work,daemon=True);self.thread.start()
 def feed(self,text):
  self.buffer+=text
  while True:
   match=re.search(r'[.!?…](?:\s|$)|\n',self.buffer)
   if not match and len(self.buffer)<280:break
   cut=match.end() if match else self.buffer.rfind(' ',0,280)
   if cut<=0:cut=280
   part=self.buffer[:cut];self.buffer=self.buffer[cut:]
   self.enqueue(part)
 def enqueue(self,text):
  # Never read fenced code aloud, including across streamed chunks.
  parts=text.split('```');spoken=[]
  for i,part in enumerate(parts):
   if i:self.code=not self.code
   if not self.code:spoken.append(part)
  text=' '.join(spoken).strip()
  if text and self.total+len(text)<=20000:
   self.total+=len(text);self.queue.put((self.epoch,text))
 def reset(self):
  self.epoch+=1;self.buffer='';self.code=False;self.emit('stop_audio','')
 def finish(self):
  self.enqueue(self.buffer);self.buffer='';self.queue.put(None);self.thread.join()
 def work(self):
  while True:
   item=self.queue.get()
   if item is None:return
   epoch,text=item
   if self.cancel.is_set() or epoch!=self.epoch:continue
   try:
    def receive(kind,value):
     if kind!='done' and epoch==self.epoch and not self.cancel.is_set():self.emit(kind,value)
    remote.request(self.settings,{'operation':'synthesize','text':text},receive,self.cancel)
   except Exception as exc:
    if not self.cancel.is_set():self.emit('warning','Озвучка: '+str(exc))
