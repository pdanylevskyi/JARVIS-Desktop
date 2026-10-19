"""Reproducible geometric reactor icon; no downloaded or AI assets."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import math
base=Path(__file__).parent
im=Image.new('RGBA',(1024,1024),(0,0,0,0));d=ImageDraw.Draw(im)
d.rounded_rectangle((20,20,1004,1004),radius=218,fill='#000000',outline='#124b70',width=5)
for y in range(70,960,12):d.line((80,y,944,y),fill='#020c19',width=2)
glow=Image.new('RGBA',im.size);g=ImageDraw.Draw(glow)
g.ellipse((240,240,784,784),outline='#00aeff',width=32)
im=Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(40)));d=ImageDraw.Draw(im)
for r,w,c in [(407,4,'#103857'),(382,12,'#087dff'),(348,3,'#123a60'),(294,5,'#36dcff'),(268,16,'#0969c7'),(232,3,'#a8edff')]:
 d.ellipse((512-r,512-r,512+r,512+r),outline=c,width=w)
for i in range(72):
 a=math.radians(i*5);r=365 if i%6 else 352
 d.line((512+r*math.cos(a),512+r*math.sin(a),512+375*math.cos(a),512+375*math.sin(a)),fill='#37bfff',width=5 if i%6==0 else 2)
for i in range(6):
 a=i*60
 d.arc((190,190,834,834),a+5,a+40,fill='#69e5ff',width=13)
 angle=math.radians(a+30)
 x,y=512+415*math.cos(angle),512+415*math.sin(angle)
 d.ellipse((x-9,y-9,x+9,y+9),fill='#21bbff')
points=[(512+202*math.cos(math.radians(a)),512+202*math.sin(math.radians(a))) for a in range(30,390,60)]
d.polygon(points,fill='#031629',outline='#27baff',width=9)
# Angular J monogram with inset highlights.
d.line([(422,405),(610,405),(610,566),(559,622),(476,622),(423,568)],fill='#24bfff',width=45,joint='curve')
d.line([(427,390),(625,390),(625,563)],fill='#b8efff',width=5)
for x in (174,810):
 for y in (175,815):d.rounded_rectangle((x-22,y-5,x+22,y+5),radius=4,fill='#138dff')
im.save(base/'jarvis.png')
im.save(base/'jarvis.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
im.save(base/'jarvis.icns')
