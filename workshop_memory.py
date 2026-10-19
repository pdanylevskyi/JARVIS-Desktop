"""Explicit local memory commands; no model call."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

HELP = '/memory — показати пам’ять; /memory add текст — додати; /memory edit — редагувати (nano: Ctrl+O, Enter — зберегти; Ctrl+X — вийти).'

def save(path, before, after):
    if not after.strip():
        raise ValueError('Порожню пам’ять не збережено.')
    if len(after.encode()) > 100_000:
        raise ValueError('Пам’ять завелика: максимум 100 КБ.')
    import fcntl
    backup_dir=path.parent.parent/'.run'/'memory-backups'
    backup_dir.mkdir(parents=True,exist_ok=True)
    with (backup_dir/'lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if path.read_text()!=before:
            raise ValueError('Пам’ять змінилася в іншому чаті. Відкрийте її повторно.')
        (backup_dir/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.txt')).write_text(before)
        fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.memory-')
        try:
            with os.fdopen(fd,'w') as out:out.write(after.rstrip()+'\n')
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

def handle(text, base):
    if text!='/memory' and not text.startswith('/memory '):return False
    path=Path(base)/'config'/'workshop-memory.txt'
    arg=text[len('/memory'):].strip()
    if arg in ('','show'):
        print(path.read_text());print(HELP);return True
    if arg.startswith('add '):
        note=arg[4:].strip()
        if not note:raise ValueError('Напишіть відомості після /memory add.')
        before=path.read_text()
        save(path,before,before.rstrip()+'\n\nУточнення користувача ('+datetime.now().isoformat(timespec='seconds')+'):\n'+note+'\n')
    elif arg=='edit':
        editor=shutil.which('nano')
        if not editor:raise ValueError('Редактор nano не встановлено. Використайте /memory add текст.')
        before=path.read_text()
        with tempfile.TemporaryDirectory(prefix='jarvis-memory-') as temp:
            draft=Path(temp)/'workshop.txt';draft.write_text(before)
            result=subprocess.run([editor,str(draft)],check=False)
            if result.returncode:raise ValueError('Редагування скасовано.')
            after=draft.read_text()
        if after==before:
            print('Змін немає.');return True
        save(path,before,after)
    else:
        print(HELP);return True
    print('Пам’ять збережено. Резервна копія — .run/memory-backups. Для використання: /workshop ваше запитання.')
    return True
