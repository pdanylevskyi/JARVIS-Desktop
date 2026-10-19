"""Explicit user uploads to Ubuntu; files are data and never auto-executed."""
import base64,json,uuid,zipfile
from pathlib import Path
MAX_BYTES=10*1024*1024

def receive(items,root):
    if not isinstance(items,list) or not 1<=len(items)<=8:raise ValueError('Оберіть 1–8 файлів.')
    decoded=[];total=0
    for item in items:
        name=item.get('name');encoded=item.get('data')
        if not isinstance(name,str) or not name or len(name)>200 or name in ('.','..') or '/' in name or '\\' in name or any(ord(c)<32 for c in name):raise ValueError('Некоректне ім’я вкладення.')
        if not isinstance(encoded,str) or len(encoded)>14_000_000:raise ValueError('Вкладення завелике.')
        raw=base64.b64decode(encoded,validate=True);total+=len(raw)
        if total>MAX_BYTES:raise ValueError('Разом вкладення мають бути до 10 МБ.')
        decoded.append((name,raw))
    root=Path(root)
    if root.is_symlink():raise ValueError('Папка вкладень не може бути посиланням.')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    session=root/uuid.uuid4().hex;session.mkdir(mode=0o700)
    result=[];images=[];budget=48000
    from .files import Files
    files=Files([str(session)],owner=True);files.read_limit=MAX_BYTES
    for name,raw in decoded:
        folder=session/uuid.uuid4().hex;folder.mkdir(mode=0o700);path=folder/name
        with path.open('xb') as out:out.write(raw)
        path.chmod(0o600);item={'name':name,'path':str(path),'bytes':len(raw)}
        if path.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):
            if len(images)<4:
                try:
                    from .vision import image_url
                    images.append(image_url({'data':base64.b64encode(raw).decode()}));item['note']='Зображення передано зоровій моделі.'
                except Exception as e:item['note']='Збережено, але зображення не прочитано: '+str(e)
            else:item['note']='Збережено. За запит зоровій моделі передаються перші 4 зображення.'
        elif path.suffix.lower()=='.zip':
            try:
                with zipfile.ZipFile(path) as archive:item['text']=json.dumps([{'name':i.filename,'bytes':i.file_size} for i in archive.infolist()[:200]],ensure_ascii=False)
                item['note']='Лише список ZIP, без розпакування чи запуску.'
            except Exception as e:item['note']='Не вдалося прочитати ZIP: '+str(e)
        else:
            try:
                if path.suffix.lower() in ('.docx','.xlsx','.pptx'):
                    with zipfile.ZipFile(path) as z:
                        if len(z.infolist())>5000 or sum(i.file_size for i in z.infolist())>64*1024*1024:raise ValueError('Документ завеликий після розпакування.')
                parsed=files.call('read_document',{'path':str(path.relative_to(session))})
                if '\x00' in parsed['text']:raise ValueError('Бінарний формат; текст не витягнуто.')
                item.update(parsed)
            except Exception as e:item['note']='Файл збережено; автоматичне читання недоступне: '+str(e)
        if 'text' in item:
            text=item['text'];item['text']=text[:budget];item['truncated']=item.get('truncated',False) or len(text)>budget;budget=max(0,budget-len(item['text']))
        result.append(item)
    return result,images
