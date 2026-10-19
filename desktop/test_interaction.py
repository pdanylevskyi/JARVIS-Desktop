import tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from desktop import actions,webapp,agent
from desktop.speech_stream import SpeechStream

class InteractionTests(unittest.TestCase):
 def test_agent_denied_write_never_executes(self):
  import json
  reply={'role':'assistant','content':'','tool_calls':[{'id':'1','function':{'name':'write_text','arguments':json.dumps({'root':0,'path':'test.txt','text':'test'})}}]}
  with tempfile.TemporaryDirectory() as d,patch.object(agent,'completion',side_effect=[reply,{'role':'assistant','content':'Відхилено.'}]):
   agent.run('',[d],[],'test',lambda *_:None,threading.Event(),{'approve':lambda _:False})
   self.assertFalse((Path(d)/'test.txt').exists())
 def test_undo_preserves_changed_file_and_requires_approval(self):
  with tempfile.TemporaryDirectory() as d,patch.object(actions,'STATE',Path(d)/'state'):
   root=Path(d)/'files';root.mkdir();p=root/'note.txt';p.write_text('original')
   actions.remember([p])
   actions.undo([root],lambda _:False);self.assertTrue(p.exists())
   p.write_text('changed')
   with self.assertRaises(ValueError):actions.undo([root],lambda _:True)
   p.write_text('original');actions.undo([root],lambda _:True)
   self.assertFalse(p.exists());self.assertEqual(next(actions.STATE.glob('undo-*/*note.txt')).read_text(),'original')
 def test_audio_starts_before_finish_and_preserves_order(self):
  calls=[];started=threading.Event()
  def request(settings,payload,emit,cancel):calls.append(payload['text']);started.set()
  with patch('desktop.speech_stream.remote.request',request):
   speech=SpeechStream({},lambda *_:None,threading.Event())
   speech.feed('Перша фраза. ');self.assertTrue(started.wait(1))
   speech.feed('Друга фраза');speech.finish()
  self.assertEqual(calls,['Перша фраза.','Друга фраза'])
 def test_cancelled_audio_not_requested(self):
  cancel=threading.Event();cancel.set()
  with patch('desktop.speech_stream.remote.request') as request:
   speech=SpeechStream({},lambda *_:None,cancel);speech.feed('Привіт.');speech.finish();request.assert_not_called()
 def test_confirmation_only_accepts_matching_request(self):
  with tempfile.TemporaryDirectory() as d,patch.object(webapp,'DATA',Path(d)),patch.object(webapp,'CONFIG',Path(d)/'settings.json'):
   b=webapp.Bridge();b._approval_id='current'
   self.assertFalse(b.confirm_action('old',True));self.assertFalse(b._approval.is_set())
   self.assertTrue(b.confirm_action('current',True));self.assertTrue(b._approved)

if __name__=='__main__':unittest.main()
