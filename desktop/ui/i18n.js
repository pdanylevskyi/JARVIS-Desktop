"use strict";
(()=>{
 let language=localStorage.getItem('language')||'en',dictionary={},reverse={};
 const originals=new WeakMap();let observer;
 function translate(value){const key=reverse[value]||value;return language==='uk'?(dictionary[key]||value):key;}
 function eligible(node){const e=node.nodeType===3?node.parentElement:node;return e&&!e.closest('script,style,textarea,#language option,#chat .body,#chat .note,#news-article');}
 function render(){
  observer?.disconnect();document.documentElement.lang=language;
  const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT,{acceptNode(n){if(!eligible(n))return NodeFilter.FILTER_REJECT;return n.nodeType===3?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_SKIP;}});
  while(walk.nextNode()){
   const n=walk.currentNode;if(!eligible(n))continue;
   const previous=originals.get(n),current=n.nodeValue;
   const original=previous&&previous.rendered===current?previous.original:current;
   const core=original.trim(),rendered=original.replace(core,translate(core));
   if(current!==rendered)n.nodeValue=rendered;
   originals.set(n,{original,rendered});
  }
  for(const n of document.querySelectorAll('[placeholder],[aria-label],[title]')){
   if(!eligible(n))continue;
   for(const a of ['placeholder','aria-label','title'])if(n.hasAttribute(a))n.setAttribute(a,translate(n.getAttribute(a)));
  }
  observer?.observe(document.body,{subtree:true,childList:true,characterData:true});
 }
 window.jarvisI18n={get language(){return language;},set(value){language=value==='en'?'en':'uk';localStorage.setItem('language',language);render();},t:translate};
 dictionary=window.jarvisLocales.uk;reverse=Object.fromEntries(Object.entries(dictionary).map(([en,uk])=>[uk,en]));reverse['Підключення']='Connect';
 observer=new MutationObserver(records=>{if(records.some(r=>eligible(r.target)))render();});render();
 const select=document.getElementById('language');select.value=language;select.onchange=()=>window.jarvisI18n.set(select.value);
})();
