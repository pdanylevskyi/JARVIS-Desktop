"""Bound transport history and fit actual model tokens, preserving the active tool turn."""
import json
import urllib.request

def retain(history, limit=2_000_000):
    result=[]; used=0
    for item in reversed(history):
        size=len(json.dumps(item,ensure_ascii=False).encode())
        if used+size>limit:break
        result.append(item);used+=size
    result.reverse()
    while result and result[0].get('role')!='user':result.pop(0)
    return result

def fit(url,messages,tools,reserve,emit):
    def request(path,data=None):
        req=urllib.request.Request(url.rstrip('/')+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    capacity=request('/props')['default_generation_settings']['n_ctx']
    # Serialize conservatively with schemas and extra allowance for chat-template markers.
    def count():
        sanitized=[];images=0
        for m in messages:
            m=dict(m)
            if isinstance(m.get('content'),list):
                images+=sum(x.get('type')=='image_url' for x in m['content'])
                m['content']=[x for x in m['content'] if x.get('type')!='image_url']
            sanitized.append(m)
        text=json.dumps({'messages':sanitized,'tools':tools},ensure_ascii=False)
        return len(request('/tokenize',{'content':text,'add_special':True})['tokens'])+images*2048+4096+len(messages)*16
    removed=False
    while count()+reserve>capacity:
        users=[i for i,m in enumerate(messages) if m['role']=='user']
        if len(users)<2:raise ValueError('Поточний запит і файли перевищують контекст. Зменште вкладення або почніть новий чат.')
        del messages[1:users[1]];removed=True
    if removed:emit('warning','Контекст заповнений: найстаріші репліки пропущено; поточний запит збережено.')
