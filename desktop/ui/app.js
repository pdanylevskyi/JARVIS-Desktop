let transcribing=false;
'use strict';
const $=id=>document.getElementById(id),reactor=window.reactor;
let localTextOnly=false;
let mode='normal',busy=false,recording=false,connected=false,current=null,pending='',showText=true,roots=[],memoryBefore='',settings={},generating=false;
let audioContext=null,audioSources=[],audioEnd=0,audioEpoch=0,audioChain=Promise.resolve(),speaking=false;
let autoSend=false,confirmation=null;
function actionNote(text){const p=document.createElement('p');p.className='note';p.textContent=text;$('chat').append(p);status(text);}
const status=t=>{$('status').textContent=t;};
const error=e=>{status(String(e.message||e));const p=document.createElement('p');p.className='note error';p.textContent=String(e.message||e);$('chat').append(p);};
async function invoke(name,...args){if(!window.pywebview){error('Інтерфейс ще запускається.');return null;}try{return await window.pywebview.api[name](...args);}catch(e){error(e);return null;}}
function state(){const s=recording?'recording':speaking?'speaking':busy||generating||pending?'generating':'idle';reactor.state(s);$('core-state').textContent={recording:'СЛУХАЮ ВАС',speaking:'ГОЛОС ДЖАРВІСА',generating:'ФОРМУЮ ВІДПОВІДЬ',idle:'СИСТЕМИ ГОТОВІ'}[s];}
function message(label,cls=''){const card=document.createElement('article');card.className='message '+cls;const tag=document.createElement('div');tag.className='message-label';tag.textContent=label;const body=document.createElement('div');body.className='body';card.append(tag,body);$('chat').append(card);return body;}
function ensureAnswer(){if(!current){current=message('J.A.R.V.I.S.');if(!showText){current.classList.add('voice-only');current.textContent='Голосова відповідь · текст приховано';}}return current;}
function scroll(follow){if(follow)$('chat').scrollTop=$('chat').scrollHeight;}
function tick(){const follow=$('chat').scrollHeight-$('chat').scrollTop-$('chat').clientHeight<100;
 if(pending){const n=matchMedia('(prefers-reduced-motion: reduce)').matches?pending.length:Math.min(16,Math.max(2,Math.ceil(pending.length/20)));const part=pending.slice(0,n);pending=pending.slice(n);ensureAnswer();if(showText)current.append(document.createTextNode(part));reactor.pulse();scroll(follow);state();}
 if(speaking&&audioContext&&audioContext.currentTime>=audioEnd){speaking=false;state();}requestAnimationFrame(tick);}
requestAnimationFrame(tick);
function stopAudio(){audioEpoch++;for(const s of audioSources){try{s.stop();}catch(_){}}audioSources=[];audioEnd=0;speaking=false;state();}
function dialog(title,content,save,label='Зберегти'){$('modal-title').textContent=title;$('modal-content').replaceChildren(content);$('modal-save').textContent=label;$('modal-save').onclick=save;$('modal').showModal();}
function inputLabel(text,input){const div=document.createElement('div'),label=document.createElement('label');label.textContent=text;div.append(label,input);return div;}
function connect(){const div=document.createElement('div'),host=document.createElement('input'),key=document.createElement('input'),row=document.createElement('div'),choose=document.createElement('button');host.value=settings.host||'';key.value=settings.key||'';choose.type='button';choose.textContent='Обрати ключ';row.className='key-row';row.append(key,choose);choose.onclick=async()=>{const p=await invoke('choose_key');if(p)key.value=p;};div.append(inputLabel('SSH користувач@сервер',host),inputLabel('Ключ на цьому комп’ютері',row));dialog('ПІДКЛЮЧЕННЯ / UBUNTU',div,async()=>{settings={host:host.value.trim(),key:key.value.trim()};if(await invoke('configure',settings.host,settings.key))$('modal').close();},'Підключитися');}
$('connect').onclick=connect;
$('folders').onclick=()=>{if(!connected)return connect();const box=document.createElement('textarea');box.value=roots.join('\n');dialog('ДОЗВОЛЕНІ ПАПКИ UBUNTU / ПО ОДНІЙ НА РЯДОК',box,async()=>{if(await invoke('set_roots',box.value))$('modal').close();});};
$('memory').onclick=()=>{if(!connected)return connect();invoke('send','/memory edit','normal',false,false,true);};
$('new').onclick=()=>{stopAudio();invoke('clear');};
$('attach').onclick=()=>invoke('attach_image');$('remove-image').onclick=()=>invoke('remove_image');
$('stop').onclick=()=>{stopAudio();invoke('stop');};
const undoButton=document.createElement('button');undoButton.textContent='СКАСУВАТИ ДІЮ ↶';undoButton.onclick=()=>{if(!busy&&!recording)invoke('send','/undo','normal',false,false,true);};$('stop').before(undoButton);
$('modal').addEventListener('close',()=>{if(confirmation){invoke('confirm_action',confirmation,false);confirmation=null;}});
async function copyText(text){try{await navigator.clipboard.writeText(text);}catch(_){const t=document.createElement('textarea');t.value=text;document.body.append(t);t.select();document.execCommand('copy');t.remove();}status('Скопійовано');}
const copyMenu=document.createElement('div');copyMenu.className='copy-menu';copyMenu.hidden=true;document.body.append(copyMenu);
function hideCopyMenu(){copyMenu.hidden=true;}
$('chat').addEventListener('contextmenu',e=>{e.preventDefault();const selected=window.getSelection().toString(),answer=e.target.closest('.message')?.querySelector('.body')?.textContent||'';copyMenu.replaceChildren();for(const [label,text] of [['Копіювати весь діалог',$('chat').innerText],['Копіювати виділене / відповідь',selected||answer]]){const button=document.createElement('button');button.textContent=label;button.disabled=!text;button.onclick=()=>{hideCopyMenu();copyText(text).catch(error);};copyMenu.append(button);}copyMenu.hidden=false;copyMenu.style.left=Math.max(0,Math.min(e.clientX,innerWidth-copyMenu.offsetWidth))+'px';copyMenu.style.top=Math.max(0,Math.min(e.clientY,innerHeight-copyMenu.offsetHeight))+'px';});
document.addEventListener('pointerdown',e=>{if(!copyMenu.contains(e.target))hideCopyMenu();});document.addEventListener('keydown',e=>{if(e.key==='Escape')hideCopyMenu();});$('chat').addEventListener('scroll',hideCopyMenu);window.addEventListener('resize',hideCopyMenu);
for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>{mode=b.dataset.mode;for(const x of document.querySelectorAll('[data-mode]')){x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',String(x===b));}};
async function send(){if(busy||recording)return;if(!connected)return connect();generating=true;state();const ok=await invoke('send',$('prompt').value,mode,$('search').checked,false,true,$('mac-agent').checked);if(ok){$('prompt').value='';document.querySelector('[data-mode="normal"]').click();}else{generating=false;state();}}
$('send').onclick=send;$('prompt').onkeydown=e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();send();}};
$('mic-button').onclick=()=>{if(!connected)return connect();stopAudio();invoke('record_toggle');};
window.jarvisEvents=events=>{for(const {type,value} of events){switch(type){
 case 'user':$('token-speed').textContent='— tok/s';stopAudio();document.querySelector('.welcome')?.remove();message('ВИ','user').textContent=value.text;current=null;pending='';showText=value.show_text;generating=false;$('chat').scrollTop=$('chat').scrollHeight;break;
 case 'text':if(value){pending+=value;generating=true;state();}break;
 case 'answer_reset':pending='';if(current&&showText)current.textContent='';break;
 case 'generation_done':generating=false;state();break;
 case 'busy':busy=value;undoButton.disabled=busy;$('send').disabled=busy;$('attach').disabled=busy;$('new').disabled=busy;$('mic-button').disabled=transcribing||localTextOnly;if(!busy){generating=false;status('Готово');if(autoSend){autoSend=false;send();}}state();break;
 case 'context_settings':contextDialog(value);break;
 case 'context_changed':status('Context: '+value.context+' tokens');break;
 case 'capabilities':localTextOnly=value.local_text;for(const id of ['mic-button','mac-agent','memory','folders'])$(id).disabled=localTextOnly;if(localTextOnly){$('mac-agent').checked=false;}break;
 case 'metrics':$('token-speed').textContent=value.tokens_per_second+' tok/s';break;
 case 'phase':$('core-detail').textContent=value;status(value);break;
 case 'status':status(value);$('core-detail').textContent=value;break;
 case 'progress':actionNote(value);break;
 case 'action':actionNote('Наступна дія: '+value);break;
 case 'action_result':actionNote(value);break;
 case 'confirm':{confirmation=value.id;const p=document.createElement('p');p.textContent=value.description;dialog('ПІДТВЕРДЖЕННЯ ДІЇ',p,()=>{const id=confirmation;confirmation=null;invoke('confirm_action',id,true);$('modal').close();},'Підтвердити');break;}
 case 'confirm_closed':if(confirmation){confirmation=null;$('modal').close();}break;
 case 'connected':connected=value;$('connection-dot').textContent=value?'●':'○';$('core-detail').textContent=value?'Ubuntu підключено':'Немає з’єднання';break;
 case 'roots':roots=value;break;
 case 'transcript':$('prompt').value+=($('prompt').value.trim()?'\n':'')+value;$('prompt').focus();break;
 case 'transcribing':transcribing=value;$('mic-button').disabled=value||localTextOnly;break;
 case 'recording':recording=value;$('mic-button').classList.toggle('recording',value);$('mic-button').setAttribute('aria-label',value?'Завершити запис':'Почати запис');$('send').disabled=value||busy;if(!value){reactor.audio(0);$('mic-time').textContent='AUDIO · STANDBY';}state();break;
 case 'level':reactor.audio(value.level);$('mic-time').textContent='ЗАПИС · '+value.seconds.toFixed(1)+' / 60 c';break;
 case 'attachment':$('attachment').hidden=!value;$('attachment').querySelector('span').textContent=value?'Прикріплено: '+value:'';break;
 case 'clear':$('chat').replaceChildren();current=null;pending='';generating=false;$('attachment').hidden=true;state();break;
 case 'memory_edit':{memoryBefore=value;const box=document.createElement('textarea');box.value=value;dialog('ПАМ’ЯТЬ МАЙСТЕРНІ / UBUNTU',box,async()=>{if(await invoke('save_memory',memoryBefore,box.value))$('modal').close();});break;}
 case 'downloaded':{const p=document.createElement('p');p.className='note';p.textContent='Завантажено на цей комп’ютер: '+value;$('chat').append(p);status('Файл у Downloads');break;}
 case 'saved':{const p=document.createElement('p');p.className='note';p.textContent='Файл на Ubuntu: '+value;$('chat').append(p);break;}
 case 'audio':break;
 case 'stop_audio':stopAudio();break;
 case 'error':case 'warning':error(value);break;
 }};};
window.addEventListener('pywebviewready',async()=>{const boot=await invoke('bootstrap');if(boot){settings=boot.settings;roots=boot.roots;if(boot.local_mode)invoke('use_local');else if(boot.needs_setup)setTimeout(()=>window.jarvisSetup?.(),100);}status('Системи готові · підключіть Ubuntu');});

$('tools-catalog').onclick=async()=>{const tools=await invoke('tool_catalog');if(!tools)return;const list=document.createElement('div');for(const t of tools){const p=document.createElement('p');p.className='note';p.textContent=t.name+' — '+t.description;list.append(p);}dialog('ІНСТРУМЕНТИ JARVIS · '+tools.length,list,()=> $('modal').close(),'Закрити');};

$('context-settings').onclick=()=>invoke('context_settings');
function contextDialog(value){
 const minimum=Number(value.minimum),maximum=Number(value.maximum),active=Number(value.context);
 if(!Number.isInteger(minimum)||!Number.isInteger(maximum)||minimum<1||maximum<minimum||!Number.isInteger(active))return error('Invalid context range');
 const box=document.createElement('div'),slider=document.createElement('input'),input=document.createElement('input'),note=document.createElement('p'),current=document.createElement('p'),limits=document.createElement('p');
 box.className='context-controls';slider.id='context-slider';slider.type='range';input.id='context-number';input.type='number';
 for(const control of [slider,input]){control.min=minimum;control.max=maximum;control.step=1;control.value=Math.max(minimum,Math.min(maximum,active));}
 slider.setAttribute('aria-label','Context tokens');input.setAttribute('aria-label','Exact context tokens');
 current.textContent=(document.documentElement.lang==='uk'?'Зараз застосовано: ':'Currently applied: ')+active.toLocaleString()+' tokens';
 limits.textContent=minimum.toLocaleString()+' — '+maximum.toLocaleString();
 note.className='note';note.textContent='Context applies immediately within allocated memory. Increasing allocation reloads the model; dictation stays available. Lowering the limit does not free allocated RAM.';
 slider.oninput=()=>{input.value=slider.value;input.setCustomValidity('');};
 input.oninput=()=>{input.setCustomValidity('');if(input.value!==''&&input.checkValidity())slider.value=input.value;};
 box.append(current,slider,limits,inputLabel('Exact context tokens',input),note);
 dialog('MODEL CONTEXT',box,async()=>{
  const n=Number(input.value);
  if(input.value===''||!Number.isInteger(n)||n<minimum||n>maximum){input.setCustomValidity('Enter a whole number within the displayed range.');input.reportValidity();return;}
  if(busy)return error('Finish or stop the current task first.');
  if(n===active){$('modal').close();return;}
  const accepted=await invoke('set_context',n);
  if(accepted)$('modal').close();
 },'Apply');
}
