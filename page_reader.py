"""Bounded public HTTP(S) reader; no scripts, cookies or local-network access."""
import http.client
import ipaddress
import re
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden=0; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript','svg','nav','footer','header'):
            self.hidden += 1
        if not self.hidden and tag in ('p','div','br','li','h1','h2','h3'):
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript','svg','nav','footer','header'):
            self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def target(url):
    u=urlsplit(url)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:
        raise ValueError('Потрібне публічне HTTP(S) посилання.')
    port=u.port or (443 if u.scheme=='https' else 80)
    if port not in (80,443): raise ValueError('Непідтримуваний порт.')
    addresses=socket.getaddrinfo(u.hostname,port,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Локальні та службові адреси недоступні.')
    return u,port,addresses[0][4][0]

def read_page(url):
    for _ in range(4):
        u,port,ip=target(url)
        conn=http.client.HTTPConnection(u.hostname,port,timeout=10)
        sock=socket.create_connection((ip,port),timeout=10)
        try:
            if u.scheme=='https':
                sock=ssl.create_default_context().wrap_socket(sock,server_hostname=u.hostname)
            conn.sock=sock
            conn.request('GET',(u.path or '/')+('?' + u.query if u.query else ''),headers={'User-Agent':'JarvisReader/1.0','Accept':'text/html,text/plain','Accept-Encoding':'identity'})
            response=conn.getresponse()
            if response.status in (301,302,303,307,308):
                url=urljoin(url,response.getheader('Location','')); continue
            if response.status!=200: raise ValueError(f'HTTP {response.status}')
            mime=response.getheader('Content-Type','').lower()
            if not any(x in mime for x in ('text/html','text/plain','application/xhtml')):
                raise ValueError('Підтримуються HTML та звичайний текст; PDF поки ні.')
            data=response.read(1_000_001)
            if len(data)>1_000_000: raise ValueError('Сторінка завелика.')
            charset=re.search(r'charset=([\w-]+)',mime)
            raw=data.decode(charset.group(1) if charset else 'utf-8',errors='replace')
            if 'html' in mime:
                parser=TextParser();parser.feed(raw);raw=' '.join(parser.parts)
            text=re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', raw)
            text=re.sub(r'\s+',' ',text).strip()
            if not text: raise ValueError('Немає доступного тексту.')
            return {'url':url,'text':text[:160000],'truncated':len(text)>160000}
        finally:
            conn.close();sock.close()
    raise ValueError('Забагато перенаправлень.')

def token_clip(text, budget):
    """Count with the running model, never a characters-per-token guess."""
    import json
    import urllib.request
    def api(path, body):
        req=urllib.request.Request('http://127.0.0.1:8080/'+path,
            json.dumps(body).encode(), {'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:
            return json.load(response)
    tokens=api('tokenize',{'content':text,'add_special':False})['tokens']
    if len(tokens)<=budget:return text,False
    return api('detokenize',{'tokens':tokens[:budget]})['content'],True


def enrich(rows):
    from concurrent.futures import ThreadPoolExecutor
    def enrich_one(row):
        try:
            page=read_page(row['url'])
            row.update(page_text=page['text'], page_url=page['url'], truncated=page['truncated'])
        except Exception as exc:
            row['read_error']=str(exc)[:160]
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(enrich_one, rows[:3]))
    readable=[row for row in rows[:3] if 'page_text' in row]
    quota=20000//max(1,len(readable))
    for row in readable:
        try:
            row['page_text'],clipped=token_clip(row['page_text'],quota)
        except Exception:
            # UTF-8 byte limit is conservative for this byte-level tokenizer.
            raw=row['page_text'].encode('utf-8')
            row['page_text']=raw[:quota].decode('utf-8',errors='ignore')
            clipped=len(raw)>quota
            row['budget_note']='Токенізатор недоступний: використано менший байтовий ліміт.'
        row['truncated']=row.get('truncated',False) or clipped
    return rows

def links(text):
    return [url.rstrip('.,;!?)]}»') for url in re.findall(r'https?://[^\s<>]+',text)[:3]]
