"""Local Mac action loop. Model proposals are data; effects require approval."""
import json,time

MUTATING={'trash_file','click','double_click','type','key','drag','open_url'}
KINDS=MUTATING|{'scroll','open_app','wait','done'}
KEYS={'enter','tab','esc','space','backspace','delete','up','down','left','right','home','end','pageup','pagedown','command','ctrl','alt','shift'}|set('abcdefghijklmnopqrstuvwxyz0123456789')

def validate(action):
 if not isinstance(action,dict) or action.get('kind') not in KINDS:raise ValueError('Модель запропонувала невідомий інструмент.')
 if not isinstance(action.get('reason'),str) or len(action['reason'])>1000:raise ValueError('Потрібен короткий опис дії.')
 kind=action['kind']
 for name in ('x','y','to_x','to_y'):
  if name in action and (type(action[name]) not in (int,float) or not 0<=action[name]<=1):raise ValueError('Координати мають бути від 0 до 1.')
 if kind in ('click','double_click','drag') and not all(k in action for k in ('x','y')):raise ValueError('Немає координат.')
 if kind=='drag' and not all(k in action for k in ('to_x','to_y')):raise ValueError('Немає кінцевих координат.')
 if kind=='type' and (not isinstance(action.get('text'),str) or len(action['text'])>4000):raise ValueError('Текст завеликий.')
 if kind=='key' and (not isinstance(action.get('keys'),list) or not 1<=len(action['keys'])<=4 or any(k not in KEYS for k in action['keys'])):raise ValueError('Непідтримувана клавіша.')
 if kind=='scroll' and (type(action.get('amount')) is not int or not -10<=action['amount']<=10):raise ValueError('Некоректна прокрутка.')
 if kind=='open_app':
  import re
  if not isinstance(action.get('app'),str) or not re.fullmatch(r'[\w .-]{1,80}',action['app']):raise ValueError('Некоректна назва програми.')
 if kind=='trash_file':
  from pathlib import Path
  if not isinstance(action.get('path'),str) or not Path(action['path']).is_absolute() or len(action['path'])>4096:raise ValueError('Потрібен точний абсолютний шлях до файлу.')
 if kind=='open_url':
  from urllib.parse import urlsplit
  u=urlsplit(action.get('url',''))
  if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:raise ValueError('Дозволені тільки HTTP(S) адреси.')
 return action

def approved_navigation(action,prompt):
 # Only a Google search made from words in the user's own request can skip a dialog.
 if action['kind']!='open_url':return False
 import re
 from urllib.parse import urlsplit,parse_qs
 url=urlsplit(action['url']);params=parse_qs(url.query)
 if url.scheme!='https' or url.netloc not in ('google.com','www.google.com') or url.path!='/search' or set(params)!={'q'} or len(params['q'])!=1:return False
 if not re.search(r'знай|шук|пошук|search|google|гугл',prompt,re.I):return False
 words=re.findall(r'\w+',prompt.casefold());query=re.findall(r'\w+',params['q'][0].casefold())
 return bool(query) and all(any(word==source or (len(word)>=4 and len(source)>=4 and word[:4]==source[:4]) for source in words) for word in query)

def needs_approval(action,prompt,observation=None):
 if action['kind'] not in MUTATING:return False
 if approved_navigation(action,prompt):return False
 # Only fixed focus/navigation shortcuts; never trust model-labelled risk.
 if action['kind']=='key':
  if action['keys']==['command','tab']:return False
  if (observation or {}).get('app')=='Google Chrome' and action['keys'] in [['command','l'],['command','f']]:return False
 return True

def describe(action):
 detail={k:v for k,v in action.items() if k!='reason' and not k.startswith('_')}
 return action['reason']+'\n'+json.dumps(detail,ensure_ascii=False)+'\nДозволити лише цю дію?'

def run(prompt,backend,planner,approve,emit,cancelled,clock=time.monotonic):
 deadline=clock()+900;history=[];backend.cancelled=cancelled;refreshes=0
 while clock()<deadline:
  if cancelled.is_set():raise RuntimeError('Зупинено.')
  observation=backend.observe()
  emit('progress','Оглядаю екран Mac: '+observation.get('app',''))
  action=validate(planner(prompt,observation,history[-12:]))
  if cancelled.is_set() or clock()>=deadline:raise RuntimeError('Зупинено або минуло 15 хвилин.')
  if action['kind']=='done':emit('text',action['reason']);return
  if action['kind']=='trash_file':backend.prepare_trash(action)
  native_navigation=action['kind']=='click' and hasattr(backend,'navigation_target') and backend.navigation_target(action,observation) is True
  if needs_approval(action,prompt,observation) and not native_navigation:
   if not approve('Програма: '+observation.get('app','')+'\n'+describe(action)):
    emit('text','Дію відхилено. Зупинив завдання, сер.');return
   if cancelled.is_set():raise RuntimeError('Зупинено.')
   if action['kind'] not in ('open_url','trash_file'):
    backend.restore(observation)
    if not backend.unchanged(observation):
     refreshes+=1
     if refreshes>=3:
      emit('text','Екран продовжує змінюватися. Дочекайтеся завершення завантаження сторінки й повторіть запит.');return
     emit('progress','Сторінка оновилася. Оглядаю її повторно та уточнюю наступну дію…')
     history.append({'action':action,'result':'НЕ виконано: екран змінився. Сплануй нову дію за свіжим зображенням.'})
     continue
  if clock()>=deadline:raise RuntimeError('Минуло 15 хвилин.')
  if native_navigation and backend.navigation_target(action,observation) is not True:
   history.append({'action':action,'result':'НЕ виконано: елемент навігації змінився.'});continue
  emit('progress','Виконую: '+action['reason'])
  outcome=backend.execute(action);refreshes=0
  if isinstance(outcome,dict) and outcome.get('trash'):emit('progress','Файл перенесено у кошик: '+outcome['trash'])
  history.append({'action':{k:v for k,v in action.items() if not k.startswith('_')},'result':outcome if isinstance(outcome,dict) else 'Виконано; результат буде перевірений наступним оглядом.'})
  emit('progress','Дію виконано. Перевіряю результат…')
  if cancelled.wait(.6):raise RuntimeError('Зупинено.')
 raise RuntimeError('Минуло 15 хвилин. Завдання зупинено.')
