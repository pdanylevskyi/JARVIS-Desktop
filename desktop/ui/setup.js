'use strict';
(()=>{
 const button=document.getElementById('model-setup');
 async function open(){
  const box=document.createElement('div'),note=document.createElement('p');
  note.textContent='Enter the specs of the computer that will run the model. This release is an SSH client; scanning this computer does not install an AI server. Public default: 50,000 context tokens.';
  const ram=document.createElement('input'),vram=document.createElement('input'),unified=document.createElement('input');
  for(const i of [ram,vram]){i.type='number';i.min=0;i.max=2048;i.step=.5;}
  let detected=null;
  const profile=()=>({ram_gib:Number(ram.value),vram_gib:Number(vram.value),unified:unified.checked,...(detected&&Number(ram.value)===detected.ram_gib?{available_ram_gib:detected.available_ram_gib}:{})});
  ram.value=16;vram.value=8;unified.type='checkbox';
  const scan=document.createElement('button');scan.type='button';scan.textContent='Scan this computer';
  const results=document.createElement('div'),recommend=document.createElement('button');recommend.type='button';recommend.textContent='Recommend models';
  box.append(note,inputLabel('RAM (GiB)',ram),inputLabel('VRAM (GiB)',vram),inputLabel('Unified memory (Apple Silicon)',unified),scan,recommend,results);
  scan.onclick=async()=>{const p=await invoke('scan_hardware');if(!p)return;detected=p;ram.value=p.ram_gib;vram.value=p.vram_gib;unified.checked=p.unified;note.textContent=p.os+' · '+p.note;};
  recommend.onclick=async()=>{
   const plan=await invoke('recommend_models',profile());if(!plan)return;
   results.replaceChildren();const warning=document.createElement('p');warning.textContent=plan.warning;results.append(warning);
   if(!plan.models.length){results.append(document.createTextNode('No supported model fits these estimates. Check the memory values.'));return;}
   for(const [i,m] of plan.models.entries()){
    const card=document.createElement('p'),link=document.createElement('button');link.type='button';link.textContent=(i===0?'Recommended · ':'')+m.name+' · '+m.quant;
    link.onclick=()=>invoke('open_model_source',m.repository,m.filename);
    const context=document.createElement('input');context.type='number';context.min=16384;context.max=m.estimated_max_context;context.value=m.context;
    const save=document.createElement('button');save.type='button';save.textContent='Save plan';save.onclick=async()=>{const n=Number(context.value);if(!Number.isInteger(n)||n<16384||n>m.estimated_max_context)return error('Invalid context size');if(await invoke('save_model_plan',m.repository,m.filename,n,profile())){document.getElementById('modal').close();connect();}};
    card.append(link,document.createElement('br'),document.createTextNode(m.weights_gib+' GiB weights · '+m.mode+' · estimated maximum '+m.estimated_max_context+' tokens'),context,save);results.append(card);
   }
  };
  dialog('MODEL SETUP',box,()=>document.getElementById('modal').close(),'Close');
 }
 button.onclick=open;window.jarvisSetup=open;
})();
