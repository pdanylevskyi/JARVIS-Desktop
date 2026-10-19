import tempfile,unittest,json,threading
from pathlib import Path
from unittest.mock import Mock
from desktop.trash_ops import snapshot,trash_file
from desktop.mac_agent import run,validate,needs_approval
from desktop.files import Files
class TrashTests(unittest.TestCase):
 def test_recoverable_and_metadata_name_collision(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'restore.json';p.write_bytes(b'original');result=trash_file(p,snapshot(p))
   self.assertFalse(p.exists());self.assertEqual(Path(result['trash']).read_bytes(),b'original');self.assertEqual(json.loads(Path(result['restore_info']).read_text())['original'],str(p))
 def test_changed_file_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';p.write_text('before');s=snapshot(p);p.write_text('after')
   with self.assertRaises(ValueError):trash_file(p,s)
   self.assertEqual(p.read_text(),'after')
 def test_directories_and_symlinks_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';p.write_text('a');link=Path(d)/'link';link.symlink_to(p)
   for item in (Path(d),link):
    with self.assertRaises(ValueError):snapshot(item)
 def test_root_escape_and_missing_confirmation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.txt';p.write_text('a');f=Files([d])
   with self.assertRaises(ValueError):f.call('delete_file',{'path':'../a.txt'})
   with self.assertRaises(ValueError):f.call('delete_file',{'path':'a.txt'})
   self.assertTrue(p.exists())
 def test_mac_deletion_always_requires_approval(self):
  action=validate({'kind':'trash_file','path':'/tmp/example.txt','reason':'Кошик'})
  self.assertTrue(needs_approval(action,'Видали'))
  backend=Mock();backend.observe.return_value={'app':'Finder'}
  run('Видали',backend,lambda *_:action,lambda _:False,Mock(),threading.Event())
  backend.prepare_trash.assert_called_once();backend.execute.assert_not_called()
if __name__=='__main__':unittest.main()
