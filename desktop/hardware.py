"""Local-only hardware probing and conservative, explicitly estimated model plans."""
import json,math,platform,subprocess
from pathlib import Path
GIB=1024**3
DEFAULT_CONTEXT=50000

def scan():
    import psutil
    memory=psutil.virtual_memory();gpus=[]
    try:
        text=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.free','--format=csv,noheader,nounits'],text=True,timeout=5,stderr=subprocess.DEVNULL)
        for line in text.splitlines():
            name,total,free=line.rsplit(',',2)
            gpus.append({'name':name.strip(),'vram_gib':round(float(total)/1024,2),'free_gib':round(float(free)/1024,2)})
    except (OSError,ValueError,subprocess.SubprocessError):pass
    if not gpus and platform.system()=='Linux':
        for p in Path('/sys/class/drm').glob('card[0-9]*/device/mem_info_vram_total'):
            try:gpus.append({'name':p.parent.parent.name,'vram_gib':round(int(p.read_text())/GIB,2)})
            except (OSError,ValueError):pass
    unified=platform.system()=='Darwin' and platform.machine()=='arm64'
    return {'os':platform.system(),'ram_gib':round(memory.total/GIB,2),'available_ram_gib':round(memory.available/GIB,2),'gpus':gpus,'unified':unified,'vram_gib':max((g['vram_gib'] for g in gpus),default=0),'note':'Apple Silicon uses shared RAM, not separate VRAM.' if unified else ('GPU not detected: enter VRAM manually.' if not gpus else 'GPU memory is not added across cards.')}

def recommend(profile):
    ram=float(profile.get('ram_gib',0));vram=float(profile.get('vram_gib',0));unified=profile.get('unified') is True
    if not all(math.isfinite(v) and 0<=v<=2048 for v in (ram,vram)) or ram<4:raise ValueError('Enter valid RAM and VRAM sizes in GiB (RAM at least 4).')
    available=float(profile.get('available_ram_gib',ram))
    if not math.isfinite(available) or available<0:raise ValueError('Invalid available RAM.')
    available=min(available,ram)
    # Preserve OS space and graph/scratch buffers. Estimates are not a load guarantee.
    host_budget=max(0,min(ram*.75,available-2))*GIB
    gpu_budget=max(0,vram*.85-1)*GIB
    models=json.loads(Path(__file__).with_name('model_catalog.json').read_text())['models']
    rows=[]
    for model in models:
        weight=model['bytes'];scratch=max(GIB,weight*.15)
        if unified:
            mode='unified';budget=host_budget-weight-scratch
        elif vram and weight+scratch<gpu_budget:
            mode='GPU weights + RAM KV cache';budget=host_budget-scratch
        else:
            mode='CPU / partial GPU offload';budget=host_budget-weight-scratch
        maximum=min(model['max_context'],262144,max(0,int(budget/model['kv_bytes_per_token_f16'])))
        maximum=maximum//1024*1024
        if maximum<16384:continue
        row=dict(model,mode=mode,estimated_max_context=maximum,context=min(DEFAULT_CONTEXT,maximum),weights_gib=round(weight/GIB,2),estimated=True)
        row['url']='https://huggingface.co/'+model['repository']+'/blob/'+model['revision']+'/'+model['filename']
        rows.append(row)
    # Prefer a practical GPU-resident model before a much slower CPU-heavy model.
    rows.sort(key=lambda r:(r['mode']!='CPU / partial GPU offload',r['context']==DEFAULT_CONTEXT,r['parameters_b'],{'Q4_K_M':0,'Q5_K_M':1,'Q6_K':2,'Q8_0':3}[r['quant']]),reverse=True)
    return {'default_context':DEFAULT_CONTEXT,'models':rows,'warning':'Estimates include F16 KV cache and memory reserves. Vision, other apps and runtime versions can change the result. Actual loading must be tested. Uncensored is a publisher label, not a guarantee of quality or correctness.'}
