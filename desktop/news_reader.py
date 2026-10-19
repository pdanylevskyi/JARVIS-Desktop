"""Text-only BBC article reader. Remote HTML never enters the desktop WebView."""
import re,time
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler

def validate_url(url):
    if not isinstance(url,str) or len(url)>2000:raise ValueError('Некоректне посилання.')
    u=urlsplit(url);host=u.hostname or ''
    if u.scheme!='https' or u.username or u.password or u.port not in (None,443) or host not in ('www.bbc.com','www.bbc.co.uk','bbc.com','bbc.co.uk'):
        raise ValueError('Читач підтримує лише статті BBC.')
    return url

class BBCRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.stack=[];self.blocks=[];self.title='';self.capture=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('br',):
            if self.capture:self.capture[1].append('\n')
            return
        if tag in ('img','input','meta','link','hr','source','area','wbr','embed','param','track','col','base'):return
        self.stack.append(tag)
        blocked=any(t in self.stack for t in ('script','style','nav','aside','footer','figure','button'))
        if ('main' in self.stack or 'article' in self.stack) and not blocked and tag in ('h1','h2','h3','p','li') and self.capture is None:
            self.capture=[tag,[],len(self.stack)]
    def handle_data(self,text):
        if self.capture and not any(t in self.stack for t in ('script','style','button')):self.capture[1].append(text)
    def handle_endtag(self,tag):
        if self.capture and tag==self.capture[0] and len(self.stack)==self.capture[2]:
            kind,parts,_=self.capture;self.capture=None;text=re.sub(r'\s+',' ',''.join(parts)).strip()
            if text and text not in ('Facebook','Telegram','Viber') and not text.startswith('End of '):
                if kind=='h1' and not self.title:self.title=text
                elif kind!='h1':self.blocks.append({'kind':'heading' if kind.startswith('h') else 'paragraph','text':text})
        if tag in self.stack:
            index=len(self.stack)-1-self.stack[::-1].index(tag);del self.stack[index:]

@lru_cache(maxsize=24)
def _article(url,bucket):
    with build_opener(BBCRedirect()).open(Request(url,headers={'User-Agent':'JARVIS/1.0'}),timeout=20) as response:
        validate_url(response.url)
        if 'html' not in response.headers.get('Content-Type',''):raise ValueError('Джерело не повернуло статтю.')
        raw=response.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('Стаття завелика для читача.')
    parser=ArticleParser();parser.feed(raw.decode('utf-8',errors='replace'))
    if not parser.title or sum(len(b['text']) for b in parser.blocks)<200:
        raise ValueError('Повний текст недоступний. Опис зі стрічки залишився нижче; спробуйте пізніше.')
    return {'title':parser.title,'blocks':parser.blocks,'url':url,'source':'BBC News Україна'}

def article(url):
    return _article(validate_url(url),int(time.time()//600))
