"""Additional bounded tools; mutations are confirmed by the agent dispatcher."""
import os,hashlib,zipfile,shutil
from pathlib import Path
from .trash_ops import snapshot,check
READ_ONLY={'file_info','find_files','search_text','list_archive'}
NAMES=READ_ONLY|{'copy_file','move_file','make_directory'}

def call(files,name,args):
    root=args.get('root',0);p=files.path(root,args.get('path',''))
    if name=='file_info':
        s=p.stat();return {'path':str(p),'directory':p.is_dir(),'bytes':s.st_size,'modified_unix':s.st_mtime,'extension':p.suffix}
    if name=='find_files':
        query=args.get('query','').casefold()
        if not query or len(query)>200:raise ValueError('Потрібна частина назви до 200 символів.')
        result=[];scanned=0
        for directory,dirs,names in os.walk(p,followlinks=False):
            dirs[:]=[d for d in dirs if not d.startswith('.') and not (Path(directory)/d).is_symlink()]
            for name_ in dirs+names:
                scanned+=1
                if scanned>10000 or len(result)>=200:return {'matches':result,'truncated':True}
                candidate=Path(directory)/name_
                if not name_.startswith('.') and not candidate.is_symlink() and query in name_.casefold():result.append(str(candidate))
        return {'matches':result,'truncated':False}
    if name=='search_text':
        query=args.get('query','')
        if not query or len(query)>500:raise ValueError('Потрібен текст пошуку до 500 символів.')
        if p.stat().st_size>2_000_000:raise ValueError('Пошук у текстових файлах до 2 МБ.')
        text=p.read_text('utf-8')
        if '\x00' in text:raise ValueError('Це бінарний файл.')
        matches=[{'line':i,'text':line[:1000]} for i,line in enumerate(text.splitlines(),1) if query.casefold() in line.casefold()]
        return {'matches':matches[:100],'truncated':len(matches)>100}
    if name=='list_archive':
        if p.stat().st_size>50_000_000:raise ValueError('Архів має бути до 50 МБ.')
        with zipfile.ZipFile(p) as archive:
            items=archive.infolist()
            return {'files':[{'name':i.filename,'bytes':i.file_size} for i in items[:200]],'truncated':len(items)>200,'note':'ZIP не розпаковано.'}
    if name=='make_directory':
        p=files.path(root,args.get('path',''));p.mkdir(parents=False,exist_ok=False)
        return {'directory':str(p)}
    if name in ('copy_file','move_file'):
        before=snapshot(p)
        target=files.path(root,args['destination'],write=True)
        if target==p:raise ValueError('Вкажіть інший шлях призначення.')
        if name=='copy_file':
            if p.stat().st_size>64*1024*1024:raise ValueError('Копіювання обмежене 64 МБ.')
            created=False
            try:
                with target.open('xb') as out:
                    created=True
                    with p.open('rb') as src:shutil.copyfileobj(src,out,1024*1024)
                check(p,before)
            except BaseException:
                if created:target.unlink(missing_ok=True)
                raise
            return {'copied':str(target),'source':str(p)}
        # Hard link + unlink refuses existing targets and cross-volume moves.
        os.link(p,target,follow_symlinks=False)
        try:
            # link changes ctime, so compare all other identity fields.
            now=snapshot(p)
            if any(now[k]!=before[k] for k in before if k!='ctime'):raise ValueError('Файл змінився.')
            p.unlink()
        except BaseException:
            target.unlink();raise
        return {'moved':str(target),'source':str(p)}
    raise ValueError('Невідомий інструмент.')
