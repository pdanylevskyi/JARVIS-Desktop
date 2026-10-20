"""Apply logical context immediately; reload only when allocation must grow."""
import json,os,time,subprocess,urllib.request
from pathlib import Path
BASE=Path(__file__).resolve().parent.parent

def configured(base=BASE):
    try:return json.loads((Path(base)/'server-settings.json').read_text()).get('chat_context')
    except (OSError,ValueError):return None

def info(base=BASE):
    with urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5) as r:
        if json.load(r).get('status')!='ok':raise ValueError('Model is still loading.')
    with urllib.request.urlopen('http://127.0.0.1:8080/v1/models',timeout=5) as r:meta=json.load(r)['data'][0]['meta']
    allocated=meta['n_ctx'];limit=configured(base)
    effective=min(allocated,limit) if type(limit) is int and limit>=16384 else allocated
    return {'context':effective,'allocated':allocated,'minimum':16384,'maximum':min(meta.get('n_ctx_train',allocated),262144),'model':meta}

def change(base,value,emit):
    import fcntl
    if type(value) is not int:raise ValueError('Context must be an integer.')
    base=Path(base);lockpath=base/'.run/context.lock';lockpath.parent.mkdir(exist_ok=True)
    with lockpath.open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('A context change is already running.')
        current=info(base)
        if not current['minimum']<=value<=current['maximum']:raise ValueError(f"Context range: {current['minimum']}–{current['maximum']} tokens.")
        if value==current['context']:return current
        path=base/'server-settings.json';before=path.read_bytes();settings=json.loads(before);settings['chat_context']=value
        def save(raw):
            temp=path.with_suffix('.context.tmp');temp.write_bytes(raw);os.replace(temp,path)
        if value<=current['allocated']:
            save((json.dumps(settings,indent=2)+'\n').encode())
            emit('status','Context applied without reloading weights. It affects the next request.')
            return dict(current,context=value)
        with urllib.request.urlopen('http://127.0.0.1:8080/slots',timeout=5) as r:slots=json.load(r)
        if any(s.get('is_processing') for s in slots):raise ValueError('Finish or stop the current generation first.')
        settings['context']=value
        def restart():subprocess.run(['systemctl','--user','restart','--no-block','jarvis'],check=True,timeout=15)
        def ready():
            until=time.monotonic()+180
            while time.monotonic()<until:
                try:
                    result=info(base)
                    if result['allocated']>=value:return result
                except (OSError,ValueError,KeyError):pass
                emit('status','Model loading; dictation remains available…');time.sleep(2)
            raise RuntimeError('Model did not become ready within 180 seconds.')
        emit('status','Increasing model allocation; loading weights…')
        save((json.dumps(settings,indent=2)+'\n').encode())
        try:restart();return ready()
        except Exception as exc:
            save(before);restart();value=current['allocated']
            try:ready()
            except Exception as rollback:raise RuntimeError('Model reload and recovery failed. Check the model service log.') from rollback
            raise ValueError('Context change failed; the previous configuration was restored.') from exc
