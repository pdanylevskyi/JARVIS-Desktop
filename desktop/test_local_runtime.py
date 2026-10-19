import hashlib,io,tempfile,threading,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from . import local_runtime as rt
class Response(io.BytesIO):
 status=200
 headers={}
class RuntimeTests(unittest.TestCase):
 def test_verified_download_and_cache(self):
  data=b'verified GGUF fixture';digest=hashlib.sha256(data).hexdigest()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf'
   with patch('urllib.request.urlopen',return_value=Response(data)) as request:
    rt.download('https://example.com/model',p,len(data),digest,lambda *a:None,threading.Event())
    rt.download('https://example.com/model',p,len(data),digest,lambda *a:None,threading.Event())
    self.assertEqual(request.call_count,1);self.assertEqual(p.read_bytes(),data)
 def test_completed_partial_is_verified_without_network(self):
  data=b'completed';digest=hashlib.sha256(data).hexdigest()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf';p.with_suffix('.gguf.part').write_bytes(data)
   with patch('urllib.request.urlopen') as request:
    rt.download('https://example.com',p,len(data),digest,lambda *a:None,threading.Event())
    request.assert_not_called();self.assertEqual(p.read_bytes(),data)
 def test_bad_checksum_never_installed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'model.gguf'
   with patch('urllib.request.urlopen',return_value=Response(b'bad')):
    with self.assertRaises(ValueError):rt.download('https://example.com',p,3,'0'*64,lambda *a:None,threading.Event())
   self.assertFalse(p.exists())
 def test_archive_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   archive=Path(d)/'runtime.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','bad')
   with self.assertRaises(ValueError):rt.extract(archive,Path(d)/'target')
   self.assertFalse((Path(d)/'escape').exists())
 def test_stop_terminates_only_owned_process(self):
  from unittest.mock import MagicMock
  process=MagicMock();process.poll.return_value=None
  with patch.object(rt,'_PROCESS',process):rt.stop()
  process.terminate.assert_called_once();process.wait.assert_called_once()
if __name__=='__main__':unittest.main()
