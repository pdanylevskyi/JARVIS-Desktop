import base64,hashlib,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from desktop.files import Files
from desktop.transfers import download,emit_file

class PythonFilesTests(unittest.TestCase):
 def test_python_is_saved_without_execution(self):
  with tempfile.TemporaryDirectory() as folder:
   f=Files([folder]);p=Path(folder)/'script.py'
   f.call('write_text',{'root':0,'path':'script.py','text':'raise RuntimeError("do not run")'})
   self.assertTrue(p.exists())
   with self.assertRaises(FileExistsError):f.save(0,'script.py',b'other')
 def test_download_roundtrip_and_collision(self):
  with tempfile.TemporaryDirectory() as source,tempfile.TemporaryDirectory() as dest:
   path=Path(source).resolve()/'part.stl';path.write_bytes(b'cad\x00\x01')
   def request(settings,payload,emit,cancel):emit_file(payload['path'],[source],emit)
   with patch('desktop.remote.request',request):
    first=download({},str(path),threading.Event(),dest)
    second=download({},str(path),threading.Event(),dest)
   self.assertNotEqual(first,second);self.assertEqual(Path(second).read_bytes(),path.read_bytes())
 def test_saved_event_downloads_on_client(self):
  from desktop import webapp
  import time
  def request(settings,payload,emit,cancel):
   emit('saved','/server/part.stl');emit('done','')
  with tempfile.TemporaryDirectory() as folder,patch.object(webapp,'DATA',Path(folder)),patch.object(webapp,'CONFIG',Path(folder)/'settings'),patch('desktop.remote.request',request),patch('desktop.transfers.download',return_value='/Downloads/part.stl') as transfer:
   bridge=webapp.Bridge();bridge._connected=True
   bridge.send('Створи STL','normal',False,False,True)
   until=time.monotonic()+2
   while bridge._busy and time.monotonic()<until:time.sleep(.01)
   transfer.assert_called_once()
   self.assertIn({'type':'downloaded','value':'/Downloads/part.stl'},list(bridge._events.queue))
 def test_reject_path_escape(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):emit_file('/etc/passwd',[folder],lambda *a:None)
 def test_corrupt_download_not_published(self):
  def request(settings,payload,emit,cancel):
   emit('file_begin',{'name':'part.stl','size':1});emit('file_chunk','YQ==');emit('file_end',{'size':1,'sha256':'wrong'})
  with tempfile.TemporaryDirectory() as folder,patch('desktop.remote.request',request):
   with self.assertRaises(ValueError):download({},'x',threading.Event(),folder)
   self.assertEqual(list(Path(folder).iterdir()),[])
if __name__=='__main__':unittest.main()
