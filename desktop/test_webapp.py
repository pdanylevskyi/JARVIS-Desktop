import tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from desktop import webapp
from desktop.tts import speech_text

class WebClientTests(unittest.TestCase):
 def test_legacy_voice_request_is_text_only(self):
  calls=[]
  def request(settings,payload,emit,cancel):
   calls.append(payload)
   if payload['operation']=='chat':
    emit('text','English');emit('translation_begin','');emit('text','Українська відповідь.')
    emit('history',[{'role':'assistant','content':'Українська відповідь.'}])
   else:emit('audio','sample')
   emit('done','')
  with tempfile.TemporaryDirectory() as directory,patch.object(webapp,'DATA',Path(directory)),patch.object(webapp,'CONFIG',Path(directory)/'settings.json'),patch.object(webapp.remote,'request',request):
   b=webapp.Bridge();b._connected=True
   self.assertTrue(b.send('Тест','long',True,True,False))
   deadline=time.monotonic()+2
   while b._busy and time.monotonic()<deadline:time.sleep(.01)
   self.assertFalse(b._busy)
   self.assertEqual(calls[0]['prompt'],'/long Тест')
   self.assertTrue(calls[0]['search_enabled'])
   self.assertEqual(len(calls),1)
   events=list(b._events.queue)
   self.assertIn({'type':'answer_reset','value':''},events)
   self.assertTrue(next(e['value'] for e in events if e['type']=='user')['show_text'])
   self.assertFalse(next(e['value'] for e in events if e['type']=='user')['voice'])
 def test_speech_omits_code_and_markup(self):
  text=speech_text('## Привіт\n**Сер**, [джерело](https://example.com).\n```python\nprint(1)\n```')
  self.assertIn('Блок коду.',text);self.assertNotIn('print',text);self.assertNotIn('https',text)
if __name__=='__main__':unittest.main()
