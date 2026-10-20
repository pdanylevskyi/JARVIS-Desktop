import os,json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
from desktop import model_settings as m,webapp
class ContextChanges(unittest.TestCase):
 @unittest.skipIf(os.name=="nt","Linux server operation")
 def test_smaller_context_never_restarts_or_reallocates(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);(base/'server-settings.json').write_text(json.dumps({'context':262144}))
   current={'context':262144,'allocated':262144,'minimum':16384,'maximum':262144}
   with patch.object(m,'info',return_value=current),patch.object(m.subprocess,'run') as restart:
    result=m.change(base,50000,lambda *a:None)
   restart.assert_not_called();self.assertEqual(result['context'],50000)
   data=json.loads((base/'server-settings.json').read_text());self.assertEqual(data['context'],262144);self.assertEqual(data['chat_context'],50000)
 @unittest.skipIf(os.name=="nt","Linux server operation")
 def test_failed_growth_restores_previous_configuration(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);before=json.dumps({'context':50000,'chat_context':32768});(base/'server-settings.json').write_text(before)
   current={'context':32768,'allocated':50176,'minimum':16384,'maximum':262144}
   import io
   with patch.object(m,'info',side_effect=[current,RuntimeError('load failed'),current]),patch.object(m.urllib.request,'urlopen',return_value=io.BytesIO(b'[]')),patch.object(m.subprocess,'run') as restart:
    with self.assertRaisesRegex(ValueError,'restored'):m.change(base,65536,lambda *a:None)
   self.assertEqual((base/'server-settings.json').read_text(),before);self.assertEqual(restart.call_count,2)
 def test_dictation_completes_while_chat_is_busy(self):
  finished=threading.Event()
  def remote(settings,payload,emit,cancel):
   self.assertEqual(payload['operation'],'transcribe');emit('transcript','dictated words');finished.set()
  with tempfile.TemporaryDirectory() as d,patch.object(webapp,'DATA',Path(d)),patch.object(webapp,'CONFIG',Path(d)/'settings.json'),patch.object(webapp.remote,'request',remote):
   b=webapp.Bridge();b._connected=True;b._busy=True;b._recording=MagicMock();b._pcm=[b'pcm']
   self.assertTrue(b.record_toggle());self.assertTrue(finished.wait(2))
   self.assertTrue(b._busy);self.assertTrue(any(e['type']=='transcript' for e in list(b._events.queue)))
if __name__=='__main__':unittest.main()
