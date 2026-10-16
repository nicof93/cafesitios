const o=document.getElementById("products-grid"),y=document.getElementById("infinite-scroll-sentinel"),p=document.getElementById("infinite-loading-spinner"),u=document.getElementById("infinite-error-container"),w=document.getElementById("infinite-retry-btn"),$=document.getElementById("infinite-end-msg"),E=document.getElementById("scroll-to-top-btn"),k=document.getElementById("catalog-count-current");E&&E.addEventListener("click",()=>{window.scrollTo({top:0,behavior:"smooth"})});if(o&&y){let l=!1,r=parseInt(o.getAttribute("data-loaded")||"0",10);const d=parseInt(o.getAttribute("data-total")||"0",10),L=18,A=t=>{const e=t.variante||{},n=e.precio_clp===0,s=!!(e.en_oferta&&!n),a=e.precio_por_kilo||0,i=e.precio_clp||0,C=e.precio_original_clp||0,f=e.formato_gramos||250,j=e.opcion||"Grano",B=!!e.es_estimado,I=t.imagen||"https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop",m=c=>c.toLocaleString("es-CL"),h=t.origen||t.pais_origen||"",v=t.proceso||"",g=Array.isArray(t.notas_cata)?t.notas_cata.map(c=>typeof c=="string"?c:c.nombre||c.nota||"").filter(Boolean):[];return`
        <article 
          class="product-clickable-card group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-stone-200/80 bg-white p-3.5 shadow-2xs transition-all duration-200 hover:border-emerald-300 hover:shadow-md cursor-pointer"
          data-product-url="/product/${t.id}"
        >
          <div>
            <div class="relative flex h-52 items-center justify-center overflow-hidden rounded-xl bg-[#F4F3ED] p-4 transition-colors group-hover:bg-[#EFECE3]">
              <img 
                src="${I}" 
                alt="Café ${t.nombre} - ${t.tienda}" 
                width="280"
                height="208"
                loading="lazy"
                decoding="async"
                referrerpolicy="no-referrer"
                onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=400&auto=format&fit=crop';"
                class="h-full w-full object-contain drop-shadow-md transition-transform duration-300 group-hover:scale-105 aspect-[4/3]"
              />
              <span class="absolute top-3 left-3 bg-white/95 backdrop-blur-xs text-stone-700 text-[10px] font-bold px-2.5 py-1 rounded-full shadow-2xs border border-stone-200/50">
                ${t.tienda}
              </span>
              ${n?`
                <span class="absolute top-3 right-3 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-extrabold text-emerald-800 shadow-2xs">
                  🎁 Muestra Gratis
                </span>
              `:s?`
                <span class="absolute top-3 right-3 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-900 shadow-2xs">
                  -${e.descuento_porcentaje}% OFF
                </span>
              `:""}
            </div>

            <div class="pt-3.5 space-y-2">
              <div class="flex flex-wrap items-center gap-1.5 text-[10px] font-medium text-stone-500">
                <span class="rounded bg-stone-100 px-1.5 py-0.5 text-stone-700">
                  ${f}g &bull; ${j}
                </span>
                ${h?`
                  <span class="rounded bg-stone-100/70 px-1.5 py-0.5 text-stone-600">
                    🌍 ${h}
                  </span>
                `:""}
                ${v?`
                  <span class="rounded bg-stone-100/70 px-1.5 py-0.5 text-stone-600">
                    ${v}
                  </span>
                `:""}
              </div>

              <h3 class="font-bold text-stone-900 text-sm leading-snug line-clamp-2 group-hover:text-emerald-800 transition">
                <a href="/product/${t.id}" class="focus:outline-none focus-visible:underline">
                  ${t.nombre}
                </a>
              </h3>

              ${g.length>0?`
                <p class="text-[11px] text-stone-500 truncate" title="${g.join(", ")}">
                  <span class="font-semibold text-stone-400">Notas:</span> ${g.slice(0,3).join(", ")}
                </p>
              `:""}
            </div>
          </div>

          <div class="mt-4 pt-3 border-t border-stone-100 space-y-3">
            <div class="flex items-end justify-between gap-2">
              <div>
                <span class="block text-[10px] uppercase font-bold tracking-wider text-stone-400">
                  Precio Formato (${f}g)
                </span>
                ${n?`
                  <span class="inline-block px-2.5 py-0.5 rounded-lg bg-emerald-50 text-emerald-800 font-extrabold text-sm">
                    ¡Muestra Gratis!
                  </span>
                `:`
                  <div class="flex items-baseline gap-1.5">
                    <span class="text-lg font-extrabold text-stone-900 tracking-tight">
                      $${m(i)}
                    </span>
                    <span class="text-[11px] font-semibold text-stone-500">CLP</span>
                    ${s?`
                      <span class="text-[10px] text-stone-400 line-through">
                        $${m(C)}
                      </span>
                    `:""}
                  </div>
                `}
              </div>

              <div class="text-right">
                <span class="block text-[9px] uppercase font-bold tracking-wider text-stone-400">
                  Ref. $/kg
                </span>
                ${n?`
                  <span class="text-[11px] font-medium text-emerald-700">$0/kg</span>
                `:`
                  <div class="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-md bg-stone-100/90 border border-stone-200/60 text-stone-600">
                    <span class="text-xs font-bold text-stone-700">
                      $${m(a)}
                    </span>
                    <span class="text-[9px] font-medium text-stone-400">/kg</span>
                    ${B?`
                      <span class="ml-0.5 rounded bg-amber-100 text-amber-800 px-0.5 text-[7px] font-bold uppercase tracking-wider" title="Gramaje estimado por defecto (250g)">Est.</span>
                    `:""}
                  </div>
                `}
              </div>
            </div>

            <div class="flex items-center justify-between text-xs pt-0.5">
              <label class="inline-flex items-center gap-1.5 cursor-pointer text-stone-500 hover:text-stone-800 select-none py-1 px-0.5" onclick="event.stopPropagation();">
                <input type="checkbox" class="compare-cb h-3.5 w-3.5 rounded border-stone-300 text-emerald-700 focus:ring-emerald-500" data-id="${t.id}" data-name="${t.nombre}" />
                <span class="text-[11px] font-medium">+ Comparar</span>
              </label>
            </div>

            <a 
              href="${t.url_detalle}" 
              target="_blank" 
              rel="noopener noreferrer"
              data-track-outbound="true"
              data-store="${t.tienda}"
              data-product-name="${t.nombre}"
              data-price="${i}"
              onclick="event.stopPropagation();"
              class="inline-flex items-center justify-center gap-1.5 w-full rounded-xl bg-stone-900 hover:bg-emerald-800 text-white font-semibold text-xs py-2.5 px-3 transition-colors duration-150 shadow-2xs"
            >
              <span>Comprar en tienda</span>
              <span aria-hidden="true">↗</span>
            </a>
          </div>
        </article>
      `},_=t=>{t.querySelectorAll(".product-clickable-card").forEach(e=>{e.addEventListener("click",n=>{if(n.target.closest("a, button, input, label"))return;const a=e.getAttribute("data-product-url");a&&(window.location.href=a)})}),t.querySelectorAll(".compare-cb").forEach(e=>{e.addEventListener("change",n=>{const s=n.target,a=s.getAttribute("data-id"),i=s.getAttribute("data-name");window.dispatchEvent(new CustomEvent("cafesitios:toggle-compare",{detail:{id:a,name:i,checked:s.checked}}))})})},x=async()=>{if(!(l||r>=d)){l=!0,u?.classList.add("hidden"),u?.classList.remove("flex"),p?.classList.remove("hidden"),p?.classList.add("flex");try{const t=new URLSearchParams({limit:String(L),offset:String(r),sort_by:o.getAttribute("data-sort")||"kilo",category:o.getAttribute("data-category")||"cafe",search_query:o.getAttribute("data-search")||"",store_name:o.getAttribute("data-store")||"",country:o.getAttribute("data-country")||"",process:o.getAttribute("data-process")||"",variety:o.getAttribute("data-variety")||"",notes:o.getAttribute("data-notes")||"",min_price:o.getAttribute("data-min-price")||"",max_price:o.getAttribute("data-max-price")||""}),e=await fetch(`/api/v1/products?${t.toString()}`);if(!e.ok)throw new Error(`HTTP error ${e.status}`);const n=await e.json(),s=n.data||n.items||[];if(s.length>0){const a=document.createElement("div");for(a.innerHTML=s.map(A).join("");a.firstChild;){const i=a.firstChild;o.appendChild(i)}_(o),r+=s.length,o.setAttribute("data-loaded",String(r)),k&&(k.textContent=String(r))}(s.length===0||r>=d)&&(b.disconnect(),$?.classList.remove("hidden"),$?.classList.add("flex"))}catch(t){console.error("Error cargando más productos en scroll infinito:",t),u?.classList.remove("hidden"),u?.classList.add("flex")}finally{l=!1,p?.classList.add("hidden"),p?.classList.remove("flex")}}};w&&w.addEventListener("click",()=>{x()});const b=new IntersectionObserver(t=>{t.forEach(e=>{e.isIntersecting&&!l&&r<d&&x()})},{rootMargin:"300px"});r<d&&b.observe(y)}
