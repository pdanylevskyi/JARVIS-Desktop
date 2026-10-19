"""Declarative 2D CAD: identical geometry in editable DXF and vector PDF.
No Python evaluation, SVG execution, external resources or filesystem access.
"""
import io
import math
from pathlib import Path

WIDTH, HEIGHT = 267, 155


def expand(elements):
    """Exact affine copies; cubic control points remain cubic, never sampled."""
    import copy
    result=[]
    for original in elements:
        count=original.get('copies',1)
        if type(count) is not int or not 1<=count<=50:raise ValueError('copies: 1–50, разом з оригіналом.')
        step=original.get('step',[0,0])
        if len(step)!=2 or not all(math.isfinite(float(v)) for v in step):raise ValueError('Некоректний step.')
        axis=original.get('mirror_x')
        if axis is not None:
            if not math.isfinite(float(axis)):raise ValueError('Некоректна вісь.')
            if original['type'] not in ('polyline','bezier','circle','arc'):
                raise ValueError('Дзеркалення лише геометрії; підписи й розміри додавай окремо.')
        for i in range(count):
            for mirror in ([False,True] if axis is not None else [False]):
                e=copy.deepcopy(original)
                for key in ('copies','step','mirror_x'):e.pop(key,None)
                def transform(p):
                    x,y=map(float,p)
                    return [(2*float(axis)-x if mirror else x)+i*float(step[0]),y+i*float(step[1])]
                for key in ('center','at','p1','p2'):
                    if key in e:e[key]=transform(e[key])
                if 'points' in e:e['points']=[transform(p) for p in e['points']]
                if mirror and e['type']=='arc':
                    e['start_angle'],e['end_angle']=(180-float(e['end_angle']))%360,(180-float(e['start_angle']))%360
                result.append(e)
                if len(result)>500:raise ValueError('Після копіювання понад 500 елементів.')
    return result


def build(title, elements, concept=True):
    import ezdxf
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from .files import font
    if not isinstance(elements,list) or not 1 <= len(elements) <= 500:
        raise ValueError('Потрібно 1–500 елементів.')
    elements=expand(elements)
    doc=ezdxf.new('R2010');doc.units=4
    doc.styles.new('JARVIS',dxfattribs={'font':str(Path(__file__).parent/'assets/NotoSans-Regular.ttf')})
    for name,color in [('outline',7),('detail',4),('axis',8),('dimension',3),('label',7)]:
        doc.layers.new(name,dxfattribs={'color':color})
    msp=doc.modelspace()
    out=io.BytesIO();c=canvas.Canvas(out,pagesize=(297*mm,210*mm))
    c.setTitle(title);c.setFont(font(),15);c.drawString(15*mm,193*mm,str(title)[:80])
    note='Концепт • Без масштабу • Не для виготовлення' if concept else 'Одиниці: мм • Масштаб 1:1 при друці 100% • Розміри потребують перевірки'
    c.setFont(font(),8);c.drawString(15*mm,12*mm,note)
    msp.add_text(note,dxfattribs={'height':2.5,'style':'JARVIS','layer':'label','insert':(0,-8)})
    c.translate(15*mm,27*mm);c.scale(mm,mm)
    def num(value):
        v=float(value)
        if not math.isfinite(v):raise ValueError('Некоректне число.')
        return v
    def point(value):
        if not isinstance(value,(list,tuple)) or len(value)!=2:raise ValueError('Точка: [x,y].')
        x,y=map(num,value)
        if not (0<=x<=WIDTH and 0<=y<=HEIGHT):raise ValueError('Геометрія поза полем 267×155 мм.')
        return x,y
    def line(a,b,attrs):
        msp.add_line(a,b,dxfattribs=attrs);c.line(*a,*b)
    for e in elements:
        kind=e['type'];layer=e.get('layer','outline')
        if layer not in doc.layers:raise ValueError('Невідомий шар.')
        attrs={'layer':layer}
        weight=num(e.get('line_width',0.3))
        if not 0.1<=weight<=1.5:raise ValueError('Товщина лінії: 0.1–1.5 мм.')
        attrs['lineweight']=round(weight*100);c.setLineWidth(weight)
        c.setStrokeColorRGB(*( (0.45,0.45,0.45) if layer=='axis' else (0.08,0.13,0.18)))
        c.setFillColorRGB(0.08,0.13,0.18);c.setDash([2,1] if layer=='axis' else [])
        if kind in ('polyline','bezier'):
            pts=[point(p) for p in e['points']]
            if not 2<=len(pts)<=300:raise ValueError('Потрібно 2–300 точок.')
            path=c.beginPath();path.moveTo(*pts[0])
            if kind=='bezier':
                if len(pts)!=4:raise ValueError('Кубічна крива: рівно 4 контрольні точки.')
                msp.add_open_spline(pts,degree=3,dxfattribs=attrs)
                path.curveTo(*pts[1],*pts[2],*pts[3])
            else:
                closed=bool(e.get('closed',False));msp.add_lwpolyline(pts,close=closed,dxfattribs=attrs)
                for p in pts[1:]:path.lineTo(*p)
                if closed:path.close()
            c.drawPath(path)
        elif kind in ('circle','arc'):
            center=point(e['center']);r=num(e['radius'])
            if r<=0:raise ValueError('Радіус має бути додатним.')
            point([center[0]-r,center[1]-r]);point([center[0]+r,center[1]+r])
            if kind=='circle':msp.add_circle(center,r,dxfattribs=attrs);c.circle(*center,r)
            else:
                start,end=num(e['start_angle']),num(e['end_angle']);sweep=(end-start)%360
                if sweep==0:raise ValueError('Для повного кола використай circle.')
                msp.add_arc(center,r,start,end,dxfattribs=attrs)
                c.arc(center[0]-r,center[1]-r,center[0]+r,center[1]+r,startAng=start,extent=sweep)
        elif kind=='text':
            at=point(e['at']);height=num(e.get('height',3));text=str(e['text'])
            if not 1<=height<=8 or len(text)>120:raise ValueError('Завеликий підпис.')
            from reportlab.pdfbase.pdfmetrics import stringWidth
            if at[0]+stringWidth(text,font(),height)>WIDTH or at[1]+height>HEIGHT:raise ValueError('Підпис виходить за поле.')
            msp.add_text(text,dxfattribs={**attrs,'height':height,'style':'JARVIS','insert':at})
            c.setFont(font(),height);c.drawString(*at,text)
        elif kind=='dimension':
            if concept:raise ValueError('Розміри доступні лише для concept=false і підтверджених користувачем даних.')
            a,b=point(e['p1']),point(e['p2']);offset=num(e.get('offset',7))
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<1 or not 3<=abs(offset)<=30:raise ValueError('Некоректна розмірна лінія.')
            nx,ny=-dy/length,dx/length
            aa=point([a[0]+nx*offset,a[1]+ny*offset]);bb=point([b[0]+nx*offset,b[1]+ny*offset])
            # Actual length is computed, never accepted as an invented label.
            dim=msp.add_aligned_dim(p1=a,p2=b,distance=offset,dxfattribs=attrs,
                override={'dimtxt':2.5,'dimasz':1.5,'dimtxsty':'JARVIS','dimdec':2});dim.render()
            c.line(*a,*aa);c.line(*b,*bb);c.line(*aa,*bb)
            for p,direction in ((aa,1),(bb,-1)):
                ux,uy=dx/length*direction,dy/length*direction
                c.line(*p,p[0]+ux*1.5+nx*.6,p[1]+uy*1.5+ny*.6)
                c.line(*p,p[0]+ux*1.5-nx*.6,p[1]+uy*1.5-ny*.6)
            c.saveState();c.translate((aa[0]+bb[0])/2,(aa[1]+bb[1])/2);c.rotate(math.degrees(math.atan2(dy,dx)))
            c.setFont(font(),2.5);c.drawCentredString(0,1.5,f'{length:.2f}'.rstrip('0').rstrip('.'));c.restoreState()
        else:raise ValueError('Невідомий CAD-елемент.')
    audit=doc.audit()
    if audit.has_errors:raise ValueError('CAD-перевірка виявила помилки.')
    c.showPage();c.save()
    dxf=io.StringIO();doc.write(dxf)
    return out.getvalue(),dxf.getvalue().encode('utf-8')

POINT={'type':'array','items':{'type':'number'},'minItems':2,'maxItems':2}
ELEMENT={'type':'object','properties':{
    'type':{'type':'string','enum':['polyline','bezier','circle','arc','text','dimension']},
    'layer':{'type':'string','enum':['outline','detail','axis','dimension','label']},
    'points':{'type':'array','items':POINT,'maxItems':300},'closed':{'type':'boolean'},
    **{k:POINT for k in ('center','at','p1','p2')},
    **{k:{'type':'number'} for k in ('radius','start_angle','end_angle','height','offset','line_width')},
    'mirror_x':{'type':'number'},'copies':{'type':'integer','minimum':1,'maximum':50},'step':POINT,
    'text':{'type':'string'}},'required':['type'],'additionalProperties':False}
DESCRIPTION='Створити 2D CAD-креслення: PDF та редагований DXF з однаковою геометрією. Координати [x,y] у мм на полі 267×155, знизу зліва. polyline: points,closed; bezier: 4 points; circle/arc: center,radius,start_angle,end_angle (градуси проти годинника); text: at,text,height; dimension: p1,p2,offset, лише concept=false, довжина обчислюється. concept=true: довільні пропорції без виробничих розмірів. Шари outline/detail/axis/dimension/label. path має закінчуватися .pdf, поруч створиться .dxf. Обидва імені мають бути новими.'

DESCRIPTION += ' Для симетричних polyline/bezier/circle/arc: mirror_x=X додає точну дзеркальну копію відносно вертикалі X. copies=N та step=[dx,dy] задають N копій разом з оригіналом; кожна наступна зміщена на step. Дзеркалення виконується перед зміщенням. Не дублюй точки вручну, не спрощуй криві; асиметрію малюй окремо. Загалом не більше 500 елементів після розгортання.'
