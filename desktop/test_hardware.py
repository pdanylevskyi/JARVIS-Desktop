import unittest,math
from .hardware import recommend
class HardwareTests(unittest.TestCase):
 def test_public_default_and_bounds(self):
  plan=recommend({'ram_gib':32,'vram_gib':8})
  self.assertEqual(plan['default_context'],50000);self.assertTrue(plan['models'])
  self.assertEqual(plan['models'][0]['mode'],'GPU weights + RAM KV cache')
  for row in plan['models']:
   self.assertLessEqual(row['context'],50000);self.assertLessEqual(row['context'],row['estimated_max_context']);self.assertLessEqual(row['estimated_max_context'],row['max_context']);self.assertTrue(row['sha256'])
 def test_unified_not_double_counted(self):
  a=recommend({'ram_gib':16,'vram_gib':0,'unified':True})
  b=recommend({'ram_gib':16,'vram_gib':16,'unified':True})
  self.assertEqual(a,b)
 def test_low_memory_and_invalid_input(self):
  self.assertFalse(recommend({'ram_gib':4,'vram_gib':0})['models'])
  for n in (-1,float('nan'),float('inf'),4096):
   with self.assertRaises(ValueError):recommend({'ram_gib':16,'vram_gib':n})
 def test_available_memory_limits_context(self):
  full=recommend({'ram_gib':32,'vram_gib':8})['models']
  low=recommend({'ram_gib':32,'available_ram_gib':6,'vram_gib':8})['models']
  by={(r['name'],r['quant']):r for r in full}
  for r in low:self.assertLessEqual(r['estimated_max_context'],by[(r['name'],r['quant'])]['estimated_max_context'])
if __name__=='__main__':unittest.main()
