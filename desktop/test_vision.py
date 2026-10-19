import base64
import io
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image
from .vision import image_url
from . import agent

class VisionTests(unittest.TestCase):
 def test_image_normalization(self):
  raw=io.BytesIO();Image.new('RGBA',(2400,1200),(255,0,0,128)).save(raw,'PNG')
  url=image_url({'data':base64.b64encode(raw.getvalue()).decode()})
  pic=Image.open(io.BytesIO(base64.b64decode(url.split(',',1)[1])))
  self.assertEqual(pic.size,(1600,800));self.assertEqual(pic.format,'JPEG')
 def test_invalid_input(self):
  for data in ('!invalid',base64.b64encode(b'<svg/>').decode()):
   with self.assertRaises(Exception):image_url({'data':data})
 def test_model_receives_image(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(agent,'completion',return_value={'role':'assistant','content':'Червоне коло'}) as call:
   agent.run('unused',[folder],[],'Що це?',lambda *a:None,threading.Event(),{'image_url':'data:image/jpeg;base64,dGVzdA=='})
   content=call.call_args.args[1][1]['content']
   self.assertEqual(content[0]['text'],'Що це?')
   self.assertEqual(content[1]['type'],'image_url')
if __name__=='__main__':unittest.main()
