import hashlib,tempfile,unittest
from pathlib import Path
from desktop.files import Files
from desktop.local_browser import requested_url,open_requested
class OwnerTests(unittest.TestCase):
 def test_edit_backup_and_changed_file(self):
  with tempfile.TemporaryDirectory() as d:
   files=Files([d]);p=Path(d)/'file.txt';p.write_text('old')
   sha=hashlib.sha256(b'old').hexdigest()
   result=files.call('edit_text',{'path':'file.txt','text':'new','sha256':sha})
   self.assertEqual(p.read_text(),'new');self.assertEqual((Path(result['backup'])/'original').read_text(),'old')
   with self.assertRaises(ValueError):files.edit(0,'file.txt','stale',sha)
 def test_owner_and_web_boundaries(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d).resolve()/'.config';p.write_text('value')
   with self.assertRaises(ValueError):Files([d]).path(0,'.config')
   owner=Files([d,'/'],owner=True)
   self.assertEqual(owner.path(0,str(p)),p)
   self.assertEqual(owner.call('read_document',{'path':str(p)})['text'],'value')
   with self.assertRaises(ValueError):owner.path(0,'/proc/self/environ')
   with self.assertRaises(ValueError):Files([d]).path(0,'/etc/passwd')
 def test_browser_only_explicit_local_requests(self):
  self.assertIsNone(requested_url('Знайди в інтернеті таблицю Менделєєва'))
  url=requested_url('Відкрий на моєму компі Google і знайди там таблицю Менделєєва')
  self.assertTrue(url.startswith('https://www.google.com/search?q='))
  self.assertIn('google.com',open_requested('/google periodic table',lambda *a,**k:True))
  with self.assertRaises(ValueError):requested_url('/open file:///etc/passwd')
 def test_owner_read_requires_approval_and_write_reports_progress(self):
  import json,threading
  from unittest.mock import patch
  from desktop import agent
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'private.txt';p.write_text('private data')
   call={'role':'assistant','content':'','tool_calls':[{'id':'1','function':{'name':'read_document','arguments':json.dumps({'root':0,'path':'private.txt'})}}]}
   messages=[]
   def completion(url,history,*args):
    if len(history)==2:return call
    messages.extend(history);return {'role':'assistant','content':'Denied'}
   with patch.object(agent,'completion',completion):agent.run('',[d],[],'read',lambda *_:None,threading.Event(),{'owner_files':True,'approve':lambda _:False})
   tool=next(m for m in messages if m['role']=='tool')
   self.assertIn('не підтвердив',tool['content']);self.assertNotIn('private data',tool['content'])
if __name__=='__main__':unittest.main()
