import unittest,json
from unittest.mock import patch
from xml.etree import ElementTree as ET
from desktop.dashboard import export_drawing,validate_drawing,weather,news
from desktop.mac_navigation import safe_target
class DashboardTests(unittest.TestCase):
 def setUp(self):self.d={'shapes':[{'kind':'line','points':[[0,0],[40,40]],'color':'#147099'},{'kind':'text','points':[[20,20]],'text':'Опір <1>','color':'#147099'}]}
 def test_svg_escaped_and_physical_units(self):
  root=ET.fromstring(export_drawing(self.d,'svg'));self.assertEqual(root.attrib['width'],'297mm');self.assertEqual(root[-1].text,'Опір <1>')
 def test_dxf_mm_and_inverted_y(self):
  dxf=export_drawing(self.d,'dxf').decode();self.assertIn('$INSUNITS\n70\n4',dxf);self.assertIn('11\n10.0\n21\n200.0',dxf)
 def test_pdf_and_project_roundtrip(self):
  self.assertTrue(export_drawing(self.d,'pdf').startswith(b'%PDF'))
  self.assertEqual(validate_drawing(json.loads(export_drawing(self.d,'json')))[1]['text'],'Опір <1>')
 def test_rejects_bad_coordinates_and_color(self):
  for field,value in [('points',[[float('nan'),1],[2,3]]),('color','url(https://evil)')]:
   self.d['shapes'][0][field]=value
   with self.assertRaises(ValueError):validate_drawing(self.d)
 def test_weather_city_resolved_and_not_found(self):
  with patch('desktop.dashboard.fetch',side_effect=[b'{"results":[{"name":"Kyiv","latitude":50.45,"longitude":30.52}]}',b'{"current":{}}']) as f:
   self.assertIn('Kyiv',weather('Kyiv')['place']);self.assertIn('latitude=50.45',f.call_args.args[0])
  with patch('desktop.dashboard.fetch',return_value=b'{}'):
   with self.assertRaises(ValueError):weather('missing')
 def test_news_strips_markup_restricts_source(self):
  rss=b'<rss><channel><item><title>A</title><description>&lt;b&gt;B&lt;/b&gt;</description><link>https://www.bbc.com/ukrainian/a</link></item><item><link>https://evil.example/</link></item></channel></rss>'
  with patch('desktop.dashboard.fetch',return_value=rss):
   items=news();self.assertEqual(len(items),1);self.assertEqual(items[0]['summary'],'B')
 def test_navigation_policy_never_trusts_buttons_or_web_elements(self):
  self.assertTrue(safe_target('AXTextField',['AXWindow','AXApplication']))
  self.assertTrue(safe_target('AXRadioButton',['AXTabGroup','AXApplication']))
  for role,parents in [('AXButton',['AXWindow']),('AXTextField',['AXWebArea','AXApplication']),('AXRadioButton',['AXWindow']),('AXTextField',[])]:self.assertFalse(safe_target(role,parents))
if __name__=='__main__':unittest.main()
