import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from .context_window import fit,retain
from .project_context import reference

class ContextTests(unittest.TestCase):
 def test_history_preserves_long_turns(self):
  h=[{'role':r,'content':'x'*7000} for _ in range(10) for r in ('user','assistant')]
  self.assertEqual(retain(h),h)
  self.assertLess(len(retain(h,15000)),len(h))
  self.assertEqual(retain(h,15000)[0]['role'],'user')
 def test_projects_skip_links_and_mark_binary(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'a.py').write_text('print(123)');(p/'.secret').write_text('secret');(p/'link').symlink_to(p/'a.py');(p/'binary.stl').write_bytes(b'\xff\x00')
   result=reference(p)
   self.assertIn('print(123)',result);self.assertNotIn('secret',result);self.assertNotIn('link',result);self.assertIn('не прочитано',result)
 def test_budget_removes_only_old_turns(self):
  messages=[{'role':'system','content':'rules'},{'role':'user','content':'old'},{'role':'assistant','content':'old answer'},{'role':'user','content':'new'},{'role':'assistant','content':'tool request','tool_calls':[]},{'role':'tool','content':'result','tool_call_id':'x'}]
  def response(req,**kwargs):
   data={'default_generation_settings':{'n_ctx':10000}} if req.full_url.endswith('/props') else {'tokens':[0]*(6000 if 'old answer' in req.data.decode() else 100)}
   import io
   return io.BytesIO(json.dumps(data).encode())
  with patch('urllib.request.urlopen',side_effect=response):fit('http://local',messages,[],1000,lambda *x:None)
  self.assertEqual([m['content'] for m in messages],['rules','new','tool request','result'])
if __name__=='__main__':unittest.main()
