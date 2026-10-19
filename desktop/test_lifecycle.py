import io,threading,unittest,time
from unittest.mock import patch
from .lifecycle import InputSession
from . import dashboard
class LifecycleTests(unittest.TestCase):
 def test_eof_cancels(self):
  cancel=threading.Event();ended=threading.Event();InputSession(io.BytesIO(b''),cancel,ended.set)
  self.assertTrue(ended.wait(1));self.assertTrue(cancel.is_set())
 def test_approval_does_not_compete_with_eof_reader(self):
  import os
  r,w=os.pipe();stream=os.fdopen(r,'rb');writer=os.fdopen(w,'wb');cancel=threading.Event();ended=threading.Event()
  try:
   session=InputSession(stream,cancel,ended.set);writer.write(b'{"approved":true}\n');writer.flush()
   self.assertTrue(session.approved(1));writer.close();self.assertTrue(ended.wait(1))
  finally:stream.close()
 def test_weather_stale_is_explicit(self):
  dashboard._WEATHER_CACHE.clear();dashboard._WEATHER_CACHE[('test',None,None)]=(time.monotonic()-700,{'data':{'current':{}},'place':'test'})
  with patch('desktop.dashboard._weather',side_effect=TimeoutError):
   result=dashboard.weather('test');self.assertTrue(result['stale']);self.assertIn('warning',result)
 def test_weather_empty_input(self):
  with self.assertRaises(ValueError):dashboard.weather('')
if __name__=='__main__':unittest.main()
