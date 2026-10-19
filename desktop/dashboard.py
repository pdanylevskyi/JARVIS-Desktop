"""Read-only dashboard data and explicit user-initiated drawing export."""
import json,math,re,html,time,threading
from urllib.request import Request,urlopen
from urllib.parse import urlencode,urlsplit
from xml.etree import ElementTree

def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'JARVIS/1.0'}),timeout=8) as r:
        raw=r.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Відповідь сервера завелика.')
    return raw

def _weather(city='',latitude=None,longitude=None):
    label='Ваше розташування'
    if city.strip():
        data=json.loads(fetch('https://geocoding-api.open-meteo.com/v1/search?'+urlencode({'name':city[:100],'count':1,'language':'uk','format':'json'})))
        places=data.get('results') or []
        if not places:raise ValueError('Місто не знайдено. Спробуйте іншу назву.')
        p=places[0];latitude,longitude=p['latitude'],p['longitude'];label=p['name']+', '+p.get('country','')
    latitude=float(latitude);longitude=float(longitude)
    if not(-90<=latitude<=90 and -180<=longitude<=180):raise ValueError('Некоректні координати.')
    query={'latitude':latitude,'longitude':longitude,'current':'temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','forecast_days':3,'timezone':'auto'}
    data=json.loads(fetch('https://api.open-meteo.com/v1/forecast?'+urlencode(query)))
    return {'place':label,'data':data,'source':'https://open-meteo.com/'}

_WEATHER_CACHE={}
_WEATHER_LOCK=threading.Lock()
def weather(city='',latitude=None,longitude=None):
    city=str(city or '').strip()
    if not city and (latitude is None or longitude is None):
        raise ValueError('Введіть місто або дозвольте визначення розташування.')
    key=(city.casefold(),latitude,longitude)
    with _WEATHER_LOCK:cached=_WEATHER_CACHE.get(key)
    now=time.monotonic()
    if cached and now-cached[0]<600:return dict(cached[1],cached=True)
    failure=None
    for attempt in range(2):
        try:
            result=_weather(city,latitude,longitude)
            if not isinstance(result['data'].get('current'),dict):raise ValueError('Некоректна відповідь погодного API.')
            with _WEATHER_LOCK:
                if len(_WEATHER_CACHE)>=32:_WEATHER_CACHE.pop(next(iter(_WEATHER_CACHE)))
                _WEATHER_CACHE[key]=(now,result)
            return result
        except (OSError,TimeoutError) as exc:failure=exc
    if cached and now-cached[0]<3600:
        return dict(cached[1],cached=True,stale=True,warning='API тимчасово недоступне. Показано останній прогноз, перевірте час оновлення.')
    raise ValueError('Погодний сервіс не відповідає. Спробуйте ще раз трохи пізніше.') from failure

def news():
    root=ElementTree.fromstring(fetch('https://feeds.bbci.co.uk/ukrainian/rss.xml'))
    items=[]
    for item in root.findall('./channel/item')[:12]:
        clean=lambda name:html.unescape(re.sub('<[^>]+>','',item.findtext(name,'')).strip())
        link=clean('link');host=urlsplit(link).hostname or ''
        if urlsplit(link).scheme!='https' or not (host.endswith('.bbc.com') or host.endswith('.bbc.co.uk')):continue
        items.append({'title':clean('title'),'summary':clean('description'),'date':clean('pubDate'),'url':link})
    if not items:raise ValueError('Джерело новин тимчасово недоступне.')
    return items

def validate_drawing(data):
    if not isinstance(data,dict) or not isinstance(data.get('shapes'),list) or len(data['shapes'])>5000:raise ValueError('Некоректне креслення.')
    shapes=[]
    for shape in data['shapes']:
        if shape.get('kind') not in ('line','rect','circle','path','text'):raise ValueError('Невідомий елемент.')
        points=shape.get('points',[])
        if not 1<=len(points)<=10000:raise ValueError('Некоректні точки.')
        for point in points:
            if len(point)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=2000 for x in point):raise ValueError('Некоректна координата.')
        if shape['kind'] in ('line','rect','circle') and len(points)!=2:raise ValueError('Потрібні дві точки.')
        color=shape.get('color','#00aaff')
        if not re.fullmatch('#[0-9a-fA-F]{6}',color):raise ValueError('Некоректний колір.')
        shapes.append({'kind':shape['kind'],'points':points,'color':color,'text':str(shape.get('text',''))[:200]})
    return shapes

def export_drawing(data,fmt):
    from xml.sax.saxutils import escape
    shapes=validate_drawing(data)
    if fmt=='json':return json.dumps({'version':1,'shapes':shapes},ensure_ascii=False,indent=2).encode()
    def geometry(s):
        p=s['points'];a=p[0];b=p[-1];return a,b,abs(b[0]-a[0]),abs(b[1]-a[1])
    if fmt=='svg':
        parts=['<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 1188 840">']
        for s in shapes:
            a,b,w,h=geometry(s);style=f'fill="none" stroke="{s["color"]}" stroke-width="2"'
            if s['kind']=='text':parts.append(f'<text x="{a[0]}" y="{a[1]}" font-size="14" fill="{s["color"]}">{escape(s["text"])}</text>')
            elif s['kind']=='rect':parts.append(f'<rect x="{min(a[0],b[0])}" y="{min(a[1],b[1])}" width="{w}" height="{h}" {style}/>')
            elif s['kind']=='circle':parts.append(f'<circle cx="{a[0]}" cy="{a[1]}" r="{math.dist(a,b)}" {style}/>')
            else:parts.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in s['points'])+f'" {style}/>')
        return ('\n'.join(parts)+'</svg>').encode()
    if fmt=='dxf':
        # ASCII DXF, millimetres; screen +Y maps to CAD -Y. $INSUNITS = 4 (mm).
        out=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
        def line(a,b):out.extend(['0','LINE','8','0','10',str(a[0]/4),'20',str((840-a[1])/4),'11',str(b[0]/4),'21',str((840-b[1])/4)])
        for s in shapes:
            a,b,w,h=geometry(s)
            if s['kind']=='circle':out.extend(['0','CIRCLE','8','0','10',str(a[0]/4),'20',str((840-a[1])/4),'40',str(math.dist(a,b)/4)])
            elif s['kind']=='text':out.extend(['0','TEXT','8','0','10',str(a[0]/4),'20',str((840-a[1])/4),'40','3.5','1',s['text'].replace('\n',' ').replace('\r',' ')])
            else:
                p=s['points'] if s['kind']!='rect' else [a,[b[0],a[1]],b,[a[0],b[1]],a]
                for a,b in zip(p,p[1:]):line(a,b)
        return ('\n'.join(out+['0','ENDSEC','0','EOF'])+'\n').encode('utf-8')
    if fmt=='pdf':
        import io
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from pathlib import Path
        font=Path(__file__).parent/'assets/DejaVuSans.ttf'
        if 'JarvisSans' not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont('JarvisSans',str(font)))
        stream=io.BytesIO();c=canvas.Canvas(stream,pagesize=(841.89,595.28));scale=841.89/1188
        c.setTitle('JARVIS — drawing');c.setFont('JarvisSans',14*scale)
        for s in shapes:
            a,b,w,h=geometry(s);x,y=a[0]*scale,(840-a[1])*scale
            c.setStrokeColor(HexColor(s['color']));c.setFillColor(HexColor(s['color']));c.setLineWidth(.7)
            if s['kind']=='text':c.drawString(x,y,s['text'])
            elif s['kind']=='circle':c.circle(x,y,math.dist(a,b)*scale)
            elif s['kind']=='rect':c.rect(min(a[0],b[0])*scale,(840-max(a[1],b[1]))*scale,w*scale,h*scale)
            else:
                for a,b in zip(s['points'],s['points'][1:]):c.line(a[0]*scale,(840-a[1])*scale,b[0]*scale,(840-b[1])*scale)
        c.showPage();c.save();return stream.getvalue()
    raise ValueError('Невідомий формат.')
