import io
import tempfile
import unittest
from pathlib import Path
import ezdxf
from pypdf import PdfReader
from .cad import build
from .files import Files
from .commands import prepare

ELEMENTS=[
 {'type':'polyline','points':[[25,25],[85,25],[85,65],[25,65]],'closed':True},
 {'type':'bezier','points':[[110,25],[105,90],[165,100],[175,25]]},
 {'type':'arc','center':[55,45],'radius':10,'start_angle':0,'end_angle':180},
 {'type':'circle','center':[35,35],'radius':3},
 {'type':'text','at':[25,100],'text':'Перевірка кривих і розмірів','height':4},
 {'type':'dimension','p1':[25,25],'p2':[85,25],'offset':-10,'layer':'dimension'},
]

class CADTests(unittest.TestCase):
 def test_curve_dimension_and_unicode_roundtrip(self):
  pdf,dxf=build('Тест CAD',ELEMENTS,False)
  doc=ezdxf.read(io.StringIO(dxf.decode()))
  self.assertFalse(doc.audit().has_errors)
  self.assertEqual(len(doc.modelspace().query('SPLINE')),1)
  self.assertEqual(len(doc.modelspace().query('DIMENSION')),1)
  spline=list(doc.modelspace().query('SPLINE'))[0]
  self.assertEqual(len(spline.control_points),4)
  text=PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
  self.assertIn('Перевірка кривих',text)
  self.assertIn('60',text)
 def test_concept_does_not_claim_scale(self):
  pdf,_=build('Concept',ELEMENTS[:2],True)
  text=PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
  self.assertIn('Без масштабу',text)
  self.assertNotIn('1:1',text)
  with self.assertRaises(ValueError):build('Bad',ELEMENTS,True)
 def test_invalid_geometry_and_protected_files(self):
  for points in ([[0,0],[999,5]],[[0,0],[float('nan'),5]]):
   with self.assertRaises(ValueError):build('Bad',[{'type':'polyline','points':points}])
  with tempfile.TemporaryDirectory() as folder:
   files=Files([folder]);args={'root':0,'path':'part.pdf','title':'Part','elements':ELEMENTS[:2],'concept':True}
   result=files.call('create_cad_drawing',args)
   self.assertTrue(Path(result['dxf']).exists())
   with self.assertRaises(FileExistsError):files.call('create_cad_drawing',args)
   with self.assertRaises(ValueError):files.call('create_cad_drawing',dict(args,path='../escape.pdf'))
   with self.assertRaises(ValueError):files.call('write_text',{'path':'raw.dxf','text':'bad'})

if __name__=='__main__':unittest.main()

class TransformTests(unittest.TestCase):
 def test_mirror_preserves_bezier_control_points(self):
  from .cad import expand
  e={'type':'bezier','points':[[10.125,20],[11.25,40],[30.5,50],[40,20]],'mirror_x':50}
  a,b=expand([e])
  self.assertEqual(a['points'],e['points'])
  self.assertEqual(b['points'],[[89.875,20],[88.75,40],[69.5,50],[60,20]])
  pdf,dxf=build('Mirror',[e]);doc=ezdxf.read(io.StringIO(dxf.decode()))
  self.assertEqual(len(doc.modelspace().query('SPLINE')),2)
 def test_arc_orientation_and_copy(self):
  from .cad import expand
  rows=expand([{'type':'arc','center':[30,30],'radius':5,'start_angle':20,'end_angle':100,'mirror_x':50,'copies':2,'step':[0,40]}])
  self.assertEqual(len(rows),4)
  self.assertEqual((rows[1]['start_angle'],rows[1]['end_angle']),(80,160))
  self.assertEqual(rows[3]['center'],[70,70])
  with self.assertRaises(ValueError):expand([{'type':'circle','center':[5,5],'radius':1,'copies':51}])
