// node _kit/palette-check.js style.css
// Measures the colour tokens in style.css §2: WCAG contrast floors (AA text, 3:1 controls and stripes) in both themes,
// and the eight people under protanopia, deuteranopia and tritanopia (Machado 2009, full severity), as CIEDE2000 distances.
// colour helpers: WCAG contrast, CVD simulation (Machado 2009, severity 1), CIEDE2000
const hex = h => { h = h.replace('#',''); if (h.length===3) h=[...h].map(c=>c+c).join(''); return [0,2,4].map(i=>parseInt(h.slice(i,i+2),16)/255); };
const lin = c => c<=0.04045 ? c/12.92 : ((c+0.055)/1.055)**2.4;
const unlin = c => { c=Math.min(1,Math.max(0,c)); return c<=0.0031308 ? 12.92*c : 1.055*c**(1/2.4)-0.055; };
const L = h => { const [r,g,b]=hex(h).map(lin); return 0.2126*r+0.7152*g+0.0722*b; };
const cr = (a,b) => { const x=L(a), y=L(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
const M = {
  protan:[[0.152286,1.052583,-0.204868],[0.114503,0.786281,0.099216],[-0.003882,-0.048116,1.051998]],
  deutan:[[0.367322,0.860646,-0.227968],[0.280085,0.672501,0.047413],[-0.011820,0.042940,0.968881]],
  tritan:[[1.255528,-0.076749,-0.178779],[-0.078411,0.930809,0.147602],[0.004733,0.691367,0.303900]],
};
const sim = (h,t) => { if(t==='normal') return hex(h); const c=hex(h).map(lin); return M[t].map(r=>unlin(r[0]*c[0]+r[1]*c[1]+r[2]*c[2])); };
const lab = rgb => { const [r,g,b]=rgb.map(lin); let X=(0.4124*r+0.3576*g+0.1805*b)/0.95047, Y=0.2126*r+0.7152*g+0.0722*b, Z=(0.0193*r+0.1192*g+0.9505*b)/1.08883;
  const f=t=>t>0.008856?Math.cbrt(t):7.787*t+16/116; [X,Y,Z]=[X,Y,Z].map(f); return [116*Y-16,500*(X-Y),200*(Y-Z)]; };
function de2000([L1,a1,b1],[L2,a2,b2]){const d=Math.PI/180,C1=Math.hypot(a1,b1),C2=Math.hypot(a2,b2),Cb=(C1+C2)/2,G=0.5*(1-Math.sqrt(Cb**7/(Cb**7+25**7)));
 const a1p=(1+G)*a1,a2p=(1+G)*a2,C1p=Math.hypot(a1p,b1),C2p=Math.hypot(a2p,b2);let h1=Math.atan2(b1,a1p)/d;if(h1<0)h1+=360;let h2=Math.atan2(b2,a2p)/d;if(h2<0)h2+=360;
 const dL=L2-L1,dC=C2p-C1p;let dh=h2-h1;if(C1p*C2p===0)dh=0;else if(dh>180)dh-=360;else if(dh<-180)dh+=360;const dH=2*Math.sqrt(C1p*C2p)*Math.sin(dh*d/2);
 const Lb=(L1+L2)/2,Cbp=(C1p+C2p)/2;let hb=h1+h2;if(C1p*C2p!==0){if(Math.abs(h1-h2)>180)hb+=(hb<360?360:-360);hb/=2;}
 const T=1-0.17*Math.cos((hb-30)*d)+0.24*Math.cos(2*hb*d)+0.32*Math.cos((3*hb+6)*d)-0.2*Math.cos((4*hb-63)*d);const dth=30*Math.exp(-(((hb-275)/25)**2));
 const RC=2*Math.sqrt(Cbp**7/(Cbp**7+25**7)),SL=1+0.015*(Lb-50)**2/Math.sqrt(20+(Lb-50)**2),SC=1+0.045*Cbp,SH=1+0.015*Cbp*T,RT=-Math.sin(2*dth*d)*RC;
 return Math.sqrt((dL/SL)**2+(dC/SC)**2+(dH/SH)**2+RT*(dC/SC)*(dH/SH));}
const dE = (a,b,t='normal') => de2000(lab(sim(a,t)),lab(sim(b,t)));

const fs=require('fs');
const css=fs.readFileSync(process.argv[2],'utf8');
const grab=b=>{const o={};for(const m of b.matchAll(/--([\w-]+):\s*(#[0-9A-Fa-f]{6})\b/g))o[m[1]]=m[2].toUpperCase();return o;};
const i0=css.indexOf(':root {'), i1=css.indexOf('@media (prefers-color-scheme: dark)'), i2=css.indexOf('/* ---------- 3. Base');
const light=grab(css.slice(i0,i1)); const dark={...light,...grab(css.slice(i1,i2))};
let fails=0; const rows=[];
const chk=(th,T,fg,bg,min,what)=>{const r=cr(T[fg],T[bg]);const ok=r>=min;if(!ok)fails++;rows.push(`${ok?'  ':'XX'} ${th.padEnd(5)} ${r.toFixed(2).padStart(5)} ≥${min}  ${fg} on ${bg}  ${what}`);};
for(const [th,T] of [['light',light],['dark',dark]]){
 for(const bg of ['paper','paper-2','card']) for(const fg of ['ink','ink-2','ink-3']) chk(th,T,fg,bg,4.5,'text');
 chk(th,T,'edge','paper',3,'control edge'); chk(th,T,'edge','field',3,'control edge'); chk(th,T,'edge','paper-2',3,'control edge');
 chk(th,T,'on-primary','primary',4.5,'primary button'); chk(th,T,'focus','paper',3,'focus ring');
 chk(th,T,'link','paper',4.5,'link');
 for(const s of ['vera','ok']) chk(th,T,s,'paper',4.5,'signal text');
 chk(th,T,'warn','paper',4.5,'warn text'); chk(th,T,'warn','warn-soft',4.5,'warn on soft');
 chk(th,T,'alert','paper',4.5,'late text'); chk(th,T,'alert','alert-soft',4.5,'late on soft');
 chk(th,T,'ok','ok-soft',4.5,'ok on soft');
 chk(th,T,'on-today','today-bg',4.5,'today stamp'); chk(th,T,'on-vera','vera-bg',4.5,'done tick');
 chk(th,T,'on-band','band',4.5,'panel text'); chk(th,T,'on-band-2','band',4.5,'panel text 2'); chk(th,T,'on-band-2','band-hi',4.5,'panel plate text');
 chk(th,T,'band','on-band',4.5,'you-are-here plate'); chk(th,T,'on-alert-plate','alert-plate',4.5,'late plate');
 chk(th,T,'everyone-ink','everyone',4.5,'Everyone icon'); chk(th,T,'everyone-ink','everyone-soft',4.5,'Everyone name'); chk(th,T,'everyone-mark','paper',3,'Everyone stripe');
 for(let i=1;i<=8;i++){const p='p'+i;
  chk(th,T,p+'-on',p,4.5,'avatar letter'); chk(th,T,p+'-ink',p+'-soft',4.5,'name on wash'); chk(th,T,p+'-ink','paper',4.5,'name on paper');
  chk(th,T,p+'-mark','paper',3,'route stripe'); chk(th,T,p+'-mark',p+'-soft',2.5,'event rule on wash (aux)');}
 chk(th,T,'phosphor','glass',4.5,'phosphor on glass'); chk(th,T,'on-send','send',4.5,'Send label');
}
// panel vs Vera's glass
rows.push(`   panel vs glass ΔE: light ${dE(light.band,light['ask-bg']).toFixed(1)}  dark ${dE(dark.band,dark['ask-bg']).toFixed(1)}  ·  panel vs page dark ${cr(dark.band,dark.paper).toFixed(2)}:1`);
console.log(rows.join('\n'));
// colour-blind: closest pairs among the eight people (base and mark), plus distance to Vera's green and the late red
for(const [th,T] of [['light',light],['dark',dark]]) for(const v of ['','-mark']){
 const ids=[1,2,3,4,5,6,7,8].map(i=>'p'+i+v);
 for(const t of ['normal','protan','deutan','tritan']){let best=[1e9];
  for(let a=0;a<8;a++)for(let b=a+1;b<8;b++){const d=dE(T[ids[a]],T[ids[b]],t);if(d<best[0])best=[d,ids[a],ids[b]];}
  let near=[1e9];for(const id of ids)for(const s of ['vera-bg','phosphor','alert','everyone-mark']){const d=dE(T[id],T[s],t);if(d<near[0])near=[d,id,s];}
  console.log(`${th.padEnd(5)} ${(v||'base').padEnd(5)} ${t.padEnd(6)} closest pair ${best[1]}/${best[2]} ΔE ${best[0].toFixed(1)} · nearest signal ${near[1]}~${near[2]} ΔE ${near[0].toFixed(1)}`);}}
console.log(fails?`${fails} FAIL`:'all floors pass');
