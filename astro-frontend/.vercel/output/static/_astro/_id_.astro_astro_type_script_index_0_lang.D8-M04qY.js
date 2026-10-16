const B=document.getElementById("variant-selector"),I=document.getElementById("display-kilo-price"),M=document.getElementById("display-unit-price"),C=document.getElementById("sticky-kilo-price");document.getElementById("btn-main-outbound-store");document.getElementById("btn-sticky-outbound");const F=document.getElementById("metric-current-price"),H=document.getElementById("metric-min-price"),A=document.getElementById("metric-avg-price"),V=document.getElementById("price-chart-svg-wrapper"),D=document.getElementById("chart-legend-label"),y=document.getElementById("btn-chart-kilo"),$=document.getElementById("btn-chart-unit"),h=window.variantsJson?JSON.parse(window.variantsJson):[];let v=0,k="kilo";const i=r=>`$${Math.round(r).toLocaleString("es-CL")}`;function K(){return h.length>0&&h[v]?h[v]:{precio_clp:0,precio_por_kilo:0,historial_precios:[]}}function u(){if(!V)return;const r=K(),s=k==="kilo",e=s?r.precio_por_kilo||0:r.precio_clp||0;let l=[];r.historial_precios&&r.historial_precios.length>1?l=r.historial_precios.map((t,o)=>({label:t.fecha_registro?new Date(t.fecha_registro).toLocaleDateString("es-CL",{day:"2-digit",month:"short"}):`P${o+1}`,value:s?t.precio_por_kilo||e:t.precio_clp||e})):l=[{label:"Hace 30d",value:e},{label:"Hace 20d",value:e},{label:"Hace 10d",value:e},{label:"Hoy",value:e}];const x=l.map(t=>t.value),m=Math.min(...x),P=Math.max(...x),b=Math.round(x.reduce((t,o)=>t+o,0)/x.length);F&&(F.textContent=s?`${i(e)}/kg`:i(e)),H&&(H.textContent=s?`${i(m)}/kg`:i(m)),A&&(A.textContent=s?`${i(b)}/kg`:i(b)),D&&(D.textContent=s?"Mostrando: Precio por Kilo ($/kg)":"Mostrando: Precio por Bolsa ($ CLP)");const f=560,c=150,G=25,g=25,d=60,w=30,S=c-G-g,E=f-d-w;let n=m*.92,a=P*1.08;(n===a||a-n<10)&&(n=Math.max(0,e*.85),a=e*1.15);const L=t=>{const o=(t-n)/(a-n);return c-g-o*S},T=t=>l.length<=1?d+E/2:d+t*(E/(l.length-1)),p=l.map((t,o)=>({x:T(o),y:L(t.value),label:t.label,val:t.value})),_=p.reduce((t,o,N)=>`${t} ${N===0?"M":"L"} ${o.x.toFixed(1)},${o.y.toFixed(1)}`,""),j=`${_} L ${p[p.length-1].x.toFixed(1)},${(c-g).toFixed(1)} L ${p[0].x.toFixed(1)},${(c-g).toFixed(1)} Z`,z=[n+(a-n)*.2,n+(a-n)*.5,n+(a-n)*.8].map(t=>{const o=L(t).toFixed(1);return`
        <line x1="${d}" y1="${o}" x2="${f-w}" y2="${o}" stroke="#E7E5E4" stroke-dasharray="3 3" stroke-width="1" />
        <text x="${d-8}" y="${parseFloat(o)+3}" text-anchor="end" font-size="9" fill="#A8A29E" font-weight="600">${i(t)}</text>
      `}).join(""),J=p.map(t=>`
      <g class="cursor-pointer group">
        <circle cx="${t.x.toFixed(1)}" cy="${t.y.toFixed(1)}" r="4.5" fill="#047857" stroke="#ffffff" stroke-width="2" class="transition-all hover:r-6" />
        <text x="${t.x.toFixed(1)}" y="${t.y-10}" text-anchor="middle" font-size="9" font-weight="700" fill="#064E3B">${i(t.val)}</text>
        <text x="${t.x.toFixed(1)}" y="${c-8}" text-anchor="middle" font-size="9" fill="#78716C" font-weight="500">${t.label}</text>
      </g>
    `).join("");V.innerHTML=`
      <svg viewBox="0 0 ${f} ${c}" class="w-full h-full overflow-visible" preserveAspectRatio="none">
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#059669" stop-opacity="0.22" />
            <stop offset="100%" stop-color="#059669" stop-opacity="0.0" />
          </linearGradient>
        </defs>
        ${z}
        <path d="${j}" fill="url(#priceGrad)" />
        <path d="${_}" fill="none" stroke="#047857" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
        ${J}
      </svg>
    `}y?.addEventListener("click",()=>{k="kilo",y.className="rounded-lg bg-white shadow-2xs px-3 py-1 text-emerald-800 font-bold transition",$?.setAttribute("class","rounded-lg px-3 py-1 text-stone-500 hover:text-stone-800 transition"),u()});$?.addEventListener("click",()=>{k="unit",$.className="rounded-lg bg-white shadow-2xs px-3 py-1 text-emerald-800 font-bold transition",y?.setAttribute("class","rounded-lg px-3 py-1 text-stone-500 hover:text-stone-800 transition"),u()});B&&B.addEventListener("change",r=>{const s=r.target;v=parseInt(s.value,10)||0;const e=K();M&&(M.innerHTML=`${i(e.precio_clp)} <span class="text-xs font-semibold text-stone-500">CLP</span>`),I&&(I.innerHTML=`${i(e.precio_por_kilo)} <span class="text-[10px] font-semibold text-emerald-600">/kg</span>`),C&&(C.textContent=`${i(e.precio_por_kilo)}/kg`),u()});u();
