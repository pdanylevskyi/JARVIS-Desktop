'use strict';
(()=>{
 const canvas=document.getElementById('reactor');
 const gl=canvas.getContext('webgl',{alpha:false,antialias:false,powerPreference:'low-power'});
 let target=0,morph=0,level=0,impulse=0,recording=false,active=false;
 window.reactor={state(s){recording=s==='recording';active=s==='generating'||s==='speaking';target=active?1:0;},audio(v){level=Math.min(1,Math.max(0,v));},pulse(){impulse=Math.min(1,impulse+.22);}};
 if(!gl){document.getElementById('core-detail').textContent='WebGL недоступний';window.reactorReady=false;return;}
 const vs=`attribute vec3 sphere;attribute vec2 ring;attribute float seed;uniform float time,morph,level,pulse,recording,aspect,dpr;varying float glow;
 void main(){float a=seed*6.283185;float wave=sin(a*7.+time*4.)*.055+cos(a*13.-time*3.)*.025;
 vec3 r=vec3(ring*(1.+recording*level*(.34+wave*4.)+sin(time*1.5+a)*.008),recording*level*sin(a*5.+time*3.)*.18);
 vec3 s=sphere;float y=time*.24;float x=.3+sin(time*.16)*.16;
 s.xz=mat2(cos(y),-sin(y),sin(y),cos(y))*s.xz;s.yz=mat2(cos(x),-sin(x),sin(x),cos(x))*s.yz;
 vec3 p=mix(r,s,morph);p*=1.+pulse*.045;float depth=2.8/(2.8-p.z*.65);vec2 pos=p.xy*depth*.64;pos.x/=aspect;pos.y+=.13;
 gl_Position=vec4(pos,0.,1.);gl_PointSize=dpr*(1.15+seed*1.1+morph*(p.z+1.)*.65+pulse*.5);
 glow=(.35+.65*(p.z+1.)*.5)*(.6+.4*sin(time*1.7+seed*87.));}`;
 const fs=`precision mediump float;varying float glow;void main(){float r=length(gl_PointCoord-.5)*2.;float a=exp(-r*r*3.6)*(1.-smoothstep(.65,1.,r));vec3 col=mix(vec3(.015,.17,.72),vec3(.1,.86,1.),glow);gl_FragColor=vec4(col,a*(.45+glow*.55));}`;
 function shader(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
 const program=gl.createProgram();gl.attachShader(program,shader(gl.VERTEX_SHADER,vs));gl.attachShader(program,shader(gl.FRAGMENT_SHADER,fs));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);
 const N=5200,data=new Float32Array(N*6),golden=Math.PI*(3-Math.sqrt(5));
 for(let i=0;i<N;i++){const h=1-2*(i+.5)/N,rad=Math.sqrt(1-h*h),angle=i*golden,a=i/N*Math.PI*2,band=.88+.12*Math.sin(i*79.31)**2;data.set([rad*Math.cos(angle),h,rad*Math.sin(angle),Math.cos(a)*band,Math.sin(a)*band,i/N],i*6);}
 const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
 for(const [name,size,offset] of [['sphere',3,0],['ring',2,3],['seed',1,5]]){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,24,offset*4);}
 const u={};for(const name of ['time','morph','level','pulse','recording','aspect','dpr'])u[name]=gl.getUniformLocation(program,name);
 gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.clearColor(0,0,0,1);
 let last=0;const reduced=matchMedia('(prefers-reduced-motion: reduce)');
 function frame(now){requestAnimationFrame(frame);if(document.hidden||now-last<30)return;const dt=Math.min(.1,(now-last)/1000);last=now;
 const dpr=Math.min(devicePixelRatio||1,2),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
 morph+=(target-morph)*(1-Math.exp(-dt*3.2));impulse*=Math.exp(-dt*4.5);gl.clear(gl.COLOR_BUFFER_BIT);
 const values={time:reduced.matches?0:now*.001,morph:reduced.matches?target:morph,level,pulse:reduced.matches?0:impulse,recording:recording?1:0,aspect:w/Math.max(1,h),dpr};
 for(const key in values)gl.uniform1f(u[key],values[key]);gl.drawArrays(gl.POINTS,0,N);}
 requestAnimationFrame(frame);window.reactorReady=true;
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();window.reactorReady=false;document.getElementById('core-detail').textContent='Графічний контекст втрачено — перевідкрийте вікно';});
})();
