"""Fetch the pinned runtime, verify it, and run --version (no model weights)."""
import os,subprocess,sys,tempfile,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop.local_runtime import runtime,download,extract
r=runtime()
with tempfile.TemporaryDirectory() as d:
 p=Path(d);archive=p/r['url'].rsplit('/',1)[1]
 download(r['url'],archive,r['bytes'],r['sha256'],lambda *a:None,threading.Event());extract(archive,p/'bin')
 exe=next((p/'bin').rglob('llama-server.exe' if os.name=='nt' else 'llama-server'))
 env=os.environ.copy()
 if sys.platform.startswith('linux'):env['LD_LIBRARY_PATH']=':'.join({str(f.parent) for f in (p/'bin').rglob('*.so*')})
 subprocess.run([str(exe),'--version'],env=env,check=True,timeout=30)
 print('Verified runtime starts on this platform.')
