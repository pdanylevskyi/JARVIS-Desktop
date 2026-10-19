"""Explicit owner-only context changes, with health verification and rollback."""
import json,os,time,subprocess,urllib.request
from pathlib import Path

def info():
    with urllib.request.urlopen('http://127.0.0.1:8080/v1/models',timeout=5) as r:meta=json.load(r)['data'][0]['meta']
    return {'context':meta['n_ctx'],'minimum':16384,'maximum':min(meta.get('n_ctx_train',meta['n_ctx']),262144),'model':meta}

def change(base,value,emit):
    import fcntl
    if type(value) is not int:raise ValueError('Context must be an integer.')
    base=Path(base);lockpath=base/'.run/context.lock';lockpath.parent.mkdir(exist_ok=True)
    with lockpath.open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('A context change is already running.')
        current=info()
        if not current['minimum']<=value<=current['maximum']:raise ValueError(f"Context range: {current['minimum']}–{current['maximum']} tokens.")
        with urllib.request.urlopen('http://127.0.0.1:8080/slots',timeout=5) as r:slots=json.load(r)
        if any(s.get('is_processing') for s in slots):raise ValueError('Finish or stop the current generation first.')
        path=base/'server-settings.json';before=path.read_bytes();settings=json.loads(before);settings['context']=value
        def save(raw):
            temp=path.with_suffix('.context.tmp');temp.write_bytes(raw);os.replace(temp,path)
        def restart():subprocess.run(['systemctl','--user','restart','jarvis'],check=True,timeout=15)
        def ready():
            until=time.monotonic()+75
            while time.monotonic()<until:
                try:return info()
                except (OSError,ValueError,KeyError):time.sleep(1)
            raise RuntimeError('Model did not become ready within 75 seconds.')
        emit('status','Restarting the model with the new context…')
        save((json.dumps(settings,indent=2)+'\n').encode())
        try:
            restart();result=ready()
            if result['context']<value:raise RuntimeError('The server did not apply the requested context.')
            return result
        except Exception:
            save(before);restart();ready()
            raise ValueError('Context change failed; the previous configuration was restored.')
