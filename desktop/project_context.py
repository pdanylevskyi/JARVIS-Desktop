"""Read-only project reference; file content never supplies agent instructions."""
import os
from pathlib import Path
from .files import Files

def reference(root):
    root=Path(root)
    if not root.is_dir() or root.is_symlink():return 'Папку projects не знайдено.'
    files=Files([str(root)],owner=True)
    rows=[];remaining=180000;seen=0
    for folder,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in ('node_modules','__pycache__','venv') and not (Path(folder)/d).is_symlink())
        for name in sorted(names):
            path=Path(folder)/name
            if name.startswith('.') or path.is_symlink() or not path.is_file():continue
            seen+=1
            if seen>2000:return '\n'.join(rows)+'\n[Ліміт огляду: 2000 файлів.]'
            rows.append('Файл: '+str(path.relative_to(root)))
            if remaining<=0:rows.append('[Вміст не прочитано: ліміт огляду.]');continue
            try:
                result=files.call('read_document',{'root':0,'path':str(path.relative_to(root))})
                text=result['text'];rows.append(text[:remaining]);remaining-=len(text)
                if result.get('truncated') or remaining<0:rows.append('[Вміст скорочено; за потреби прочитай файл інструментом.]')
            except Exception:
                rows.append('[Вміст не прочитано: бінарний, завеликий або непідтримуваний файл.]')
    return '\n'.join(rows) or 'Папка projects порожня.'
