import base64,json,tempfile,unittest,zipfile,io
from pathlib import Path
from unittest.mock import patch
from desktop.attachments import receive
from desktop.files import Files,TOOLS
from desktop.commands import prepare
class Tests(unittest.TestCase):
 def attachment(self,name,data):return {'name':name,'data':base64.b64encode(data).decode()}
 def test_uploads_text_and_binary_without_execution(self):
  with tempfile.TemporaryDirectory() as d:
   rows,images=receive([self.attachment('hello.txt','Привіт'.encode()),self.attachment('unknown.bin',b'\x00\xff'),self.attachment('empty.txt',b'')],Path(d)/'uploads')
   self.assertEqual(rows[0]['text'],'Привіт');self.assertNotIn('text',rows[1]);self.assertTrue(Path(rows[1]['path']).is_file());self.assertFalse(images)
 def test_invalid_names_and_sizes_rejected_before_write(self):
  with tempfile.TemporaryDirectory() as d:
   for name in ('../x','a/b','a\\b'):
    with self.assertRaises(ValueError):receive([self.attachment(name,b'x')],Path(d)/'uploads')
   self.assertFalse((Path(d)/'uploads').exists())
 def test_duplicate_names_separated(self):
  with tempfile.TemporaryDirectory() as d:
   rows,_=receive([self.attachment('a.txt',b'one'),self.attachment('a.txt',b'two')],Path(d)/'uploads')
   self.assertNotEqual(rows[0]['path'],rows[1]['path'])
 def test_tools_do_not_overwrite_and_cannot_escape(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'a.txt').write_text('Hello\nneedle');f=Files([d]);f.call('copy_file',{'path':'a.txt','destination':'b.txt'})
   with self.assertRaises(FileExistsError):f.call('copy_file',{'path':'a.txt','destination':'b.txt'})
   self.assertEqual((p/'b.txt').read_text(),'Hello\nneedle')
   f.call('move_file',{'path':'b.txt','destination':'c.txt'});self.assertFalse((p/'b.txt').exists());self.assertTrue((p/'c.txt').exists())
   self.assertEqual(f.call('search_text',{'path':'a.txt','query':'needle'})['matches'][0]['line'],2)
   with self.assertRaises(ValueError):f.call('copy_file',{'path':'a.txt','destination':'../outside.txt'})
   f.call('make_directory',{'path':'folder'});self.assertTrue((p/'folder').is_dir())
 def test_memory_in_regular_chat_without_overriding_request(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'config').mkdir();(p/'config/workshop-memory.txt').write_text('Резистор 1 кОм')
   with patch('web_search.search_query',return_value=None),patch('page_reader.links',return_value=[]):
    prompt,options=prepare('Напиши код',p,[d],lambda *_:None,False)
   self.assertEqual(prompt,'Напиши код');self.assertIn('Резистор 1 кОм',options['context']);self.assertIn('НЕ історія',options['context'])
 @unittest.skipUnless(__import__("sys").platform=="darwin","Native Mac client test")
 def test_native_picker_accepts_multiple_formats_and_send_payload(self):
  from desktop import webapp
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as d,patch.object(webapp,'DATA',Path(d)),patch.object(webapp,'CONFIG',Path(d)/'settings.json'):
   p=Path(d)/'note.txt';p.write_text('text');q=Path(d)/'model.stl';q.write_bytes(b'fake test data')
   b=webapp.Bridge();b._window=Mock();b._window.create_file_dialog.return_value=[str(p),str(q)]
   b.attach_image();self.assertEqual(len(b._attachments),2);b._connected=True;b._launch=Mock(return_value=True)
   self.assertTrue(b.send('Read','normal',False,False,True));payload=b._launch.call_args.args[0]
   self.assertEqual([a['name'] for a in payload['attachments']],['note.txt','model.stl']);self.assertNotIn('image',payload)
if __name__=='__main__':unittest.main()
