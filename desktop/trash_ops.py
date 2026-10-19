"""Recoverable file deletion, with a fresh identity check after confirmation."""
import json,os,stat,uuid
from pathlib import Path

def snapshot(path):
    p=Path(path).expanduser()
    if not p.is_absolute():raise ValueError('Потрібен повний шлях до файлу.')
    if p.is_symlink():raise ValueError('Символічні посилання не видаляються цим інструментом.')
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode):raise ValueError('Оберіть один звичайний файл, не папку.')
    return {'path':str(p.resolve()),'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime':s.st_mtime_ns,'ctime':s.st_ctime_ns}

def check(path,expected):
    if not isinstance(expected,dict) or snapshot(path)!=expected:raise ValueError('Файл змінився після підтвердження. Потрібне нове підтвердження.')

def trash_file(path,expected):
    p=Path(path);check(p,expected)
    # Same-filesystem rename: no permanent unlink, cross-volume copy or overwrite.
    trash=p.parent/'.jarvis-trash'
    if trash.is_symlink():raise ValueError('Кошик не може бути символічним посиланням.')
    trash.mkdir(mode=0o700,exist_ok=True)
    slot=trash/uuid.uuid4().hex;slot.mkdir(mode=0o700)
    destination=slot/'file'
    metadata=slot/'restore.json'
    metadata.write_text(json.dumps({'original':str(p),'file':p.name},ensure_ascii=False));metadata.chmod(0o600)
    check(p,expected)
    p.rename(destination)
    return {'trashed':str(p),'trash':str(destination),'restore_info':str(metadata),'message':'Файл у кошику JARVIS; його можна повернути за початковим шляхом.'}

def trash_mac(path,expected):
    check(path,expected)
    from Foundation import NSFileManager,NSURL
    ok,url,error=NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(NSURL.fileURLWithPath_(str(path)),None,None)
    if not ok:raise ValueError(str(error.localizedDescription()) if error else 'Не вдалося перенести файл у кошик.')
    return {'trashed':str(path),'trash':str(url.path()) if url else 'Кошик macOS'}
