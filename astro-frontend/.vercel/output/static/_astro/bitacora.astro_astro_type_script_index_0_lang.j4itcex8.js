import{L as p,R as H}from"./LocalStorageAdapter.CYPMhrtX.js";import{H as M}from"./HttpClient.S6ExdqAs.js";import{A as F}from"./AnalyticsTracker.FmDP4B-W.js";class G{constructor(e=new M){this.http=e}getLocalRecipes(){return p.getRecipes()}saveLocalRecipe(e){const a=new H(e);return p.saveRecipe(a)}deleteLocalRecipe(e){return p.deleteRecipe(e)}async syncToCloud(){const e=this.getLocalRecipes();if(e.length===0)return{success:!1,message:"No hay recetas para respaldar",count:0};const a=p.getDeviceId(),n=e[0],o={device_id:a,nombre_cafe:n.cafe,metodo:n.metodo,gramos_cafe:n.gramos_cafe,gramos_agua:n.gramos_agua,tiempo_segundos:180,molienda:n.molienda||"Media",notas:n.notas||"Bitácora Astro",calificacion:n.calificacion||5,catacion_sca:n.catacion_sca,puntuacion_sca_total:n.puntuacion_sca_total};return await this.http.post("/api/v1/recetas",o),{success:!0,message:"¡Recetas respaldadas exitosamente en la nube!",count:e.length}}}const u=new G,r=document.getElementById("recipe-slide-drawer"),l=document.getElementById("recipe-drawer-backdrop"),O=document.getElementById("btn-open-drawer"),q=document.getElementById("btn-empty-create"),U=document.getElementById("btn-close-drawer"),P=document.getElementById("btn-cancel-drawer"),N=document.getElementById("drawer-recipe-form"),J=document.getElementById("btn-sync-cloud-page"),R=document.getElementById("recipes-empty-state"),c=document.getElementById("recipes-grid"),C=document.getElementById("recipes-counter-text"),f=document.getElementById("input-rec-gramos-cafe"),v=document.getElementById("input-rec-gramos-agua"),g=document.getElementById("preview-ratio"),i=document.getElementById("label-sca-total");function S(){l?.classList.remove("opacity-0","pointer-events-none"),l?.classList.add("opacity-100","pointer-events-auto"),r?.classList.remove("translate-x-full"),r?.classList.add("translate-x-0"),document.body.classList.add("overflow-hidden"),document.getElementById("input-rec-cafe")?.focus()}function d(){l?.classList.remove("opacity-100","pointer-events-auto"),l?.classList.add("opacity-0","pointer-events-none"),r?.classList.remove("translate-x-0"),r?.classList.add("translate-x-full"),document.body.classList.remove("overflow-hidden")}O?.addEventListener("click",S);q?.addEventListener("click",S);U?.addEventListener("click",d);P?.addEventListener("click",d);l?.addEventListener("click",d);window.addEventListener("keydown",t=>{t.key==="Escape"&&!r?.classList.contains("translate-x-full")&&d()});function m(){if(!f||!v||!g)return;const t=parseFloat(f.value),e=parseFloat(v.value);if(t>0&&e>0){const a=(e/t).toFixed(1);g.textContent=`Ratio 1:${a}`}else g.textContent="Ratio --:--"}f?.addEventListener("input",m);v?.addEventListener("input",m);function A(){const t=document.querySelectorAll(".input-sca-attr");let e=0,a=0;return t.forEach(n=>{const o=parseFloat(n.value);!isNaN(o)&&o>0&&(e+=o,a++)}),a>0&&i?(i.textContent=`★ ${e.toFixed(2)} / 100 pts SCA (${a}/10 atributos)`,parseFloat(e.toFixed(2))):(i&&(i.textContent="Sin calificar"),null)}document.querySelectorAll(".input-sca-attr").forEach(t=>{t.addEventListener("input",A)});function b(){const t=u.getLocalRecipes();if(C&&(C.textContent=`${t.length} receta${t.length===1?"":"s"} registrada${t.length===1?"":"s"}`),t.length===0){R?.classList.remove("hidden"),c?.classList.add("hidden"),c&&(c.innerHTML="");return}R?.classList.add("hidden"),c?.classList.remove("hidden"),c&&(c.innerHTML=t.map(e=>{const a=e.fecha?new Date(e.fecha).toLocaleDateString("es-CL",{day:"2-digit",month:"short",year:"numeric"}):"Hoy";return`
        <article class="group rounded-3xl border border-stone-200/90 bg-white p-5 shadow-2xs hover:shadow-md hover:border-emerald-200 transition-all duration-200 flex flex-col justify-between space-y-4">
          <div class="space-y-3">
            <!-- Header de Tarjeta -->
            <div class="flex items-start justify-between gap-2">
              <div class="space-y-1">
                <span class="inline-block text-[10px] font-extrabold uppercase tracking-wider text-emerald-800 bg-emerald-50 border border-emerald-200/60 rounded-full px-2.5 py-0.5">
                  ${e.metodo}
                </span>
                <h3 class="text-base font-bold text-stone-900 group-hover:text-emerald-950 transition line-clamp-2">
                  ${e.cafe}
                </h3>
              </div>
              <span class="text-amber-500 text-xs shrink-0 font-bold" title="${e.calificacion} de 5 estrellas">
                ${"⭐".repeat(e.calificacion)}
              </span>
            </div>

            <!-- Badge SCA si existe -->
            ${e.puntuacion_sca_total?`
              <div class="inline-flex items-center gap-1.5 rounded-xl bg-amber-50 border border-amber-200 px-2.5 py-1 text-xs font-black text-amber-900 shadow-2xs">
                <span>★</span>
                <span>${e.puntuacion_sca_total} pts SCA</span>
                <span class="text-[10px] font-normal text-amber-700">(${Object.keys(e.catacion_sca||{}).length} atributos)</span>
              </div>
            `:""}

            <!-- Parámetros de Extracción -->
            <div class="grid grid-cols-2 gap-2 text-xs bg-stone-50/80 rounded-2xl p-3 border border-stone-100">
              <div>
                <span class="block text-[10px] uppercase font-bold text-stone-400">Ratio</span>
                <span class="font-extrabold text-stone-800">${e.getRatio()}</span>
              </div>
              <div>
                <span class="block text-[10px] uppercase font-bold text-stone-400">Dosis / Agua</span>
                <span class="font-semibold text-stone-700">${e.gramos_cafe}g / ${e.gramos_agua}g</span>
              </div>
              ${e.molienda?`
                <div class="col-span-2 pt-1 border-t border-stone-200/40">
                  <span class="block text-[10px] uppercase font-bold text-stone-400">Molienda</span>
                  <span class="text-stone-700 truncate block">${e.molienda}</span>
                </div>
              `:""}
              ${e.tiempo?`
                <div class="col-span-2">
                  <span class="block text-[10px] uppercase font-bold text-stone-400">Tiempo</span>
                  <span class="text-stone-700">${e.tiempo}</span>
                </div>
              `:""}
            </div>

            <!-- Notas de cata -->
            ${e.notas?`
              <div class="text-xs text-stone-600 bg-stone-50/50 p-2.5 rounded-xl border border-stone-100/80 italic">
                "${e.notas}"
              </div>
            `:""}
          </div>

          <!-- Footer con Fecha y Borrar -->
          <div class="pt-3 border-t border-stone-100 flex items-center justify-between text-[11px] text-stone-400">
            <span>📅 ${a}</span>
            <button 
              type="button" 
              class="btn-delete-recipe text-stone-400 hover:text-rose-600 hover:bg-rose-50 p-1.5 rounded-lg transition"
              data-recipe-id="${e.id}"
              title="Eliminar receta de la bitácora"
            >
              🗑️
            </button>
          </div>
        </article>
      `}).join(""),document.querySelectorAll(".btn-delete-recipe").forEach(e=>{e.addEventListener("click",()=>{const a=e.getAttribute("data-recipe-id");a&&confirm("¿Deseas eliminar esta receta de tu bitácora?")&&(u.deleteLocalRecipe(a),b())})}))}N?.addEventListener("submit",t=>{t.preventDefault();const e=document.getElementById("input-rec-cafe").value.trim(),a=document.getElementById("select-rec-metodo").value,n=parseFloat(document.getElementById("input-rec-gramos-cafe").value),o=parseFloat(document.getElementById("input-rec-gramos-agua").value),D=document.getElementById("input-rec-molienda").value.trim(),T=document.getElementById("input-rec-tiempo").value.trim(),x=parseInt(document.getElementById("select-rec-calificacion").value,10),z=document.getElementById("textarea-rec-notas").value.trim(),y=parseFloat(document.getElementById("input-sca-aroma")?.value),E=parseFloat(document.getElementById("input-sca-sabor")?.value),h=parseFloat(document.getElementById("input-sca-retrogusto")?.value),L=parseFloat(document.getElementById("input-sca-acidez")?.value),B=parseFloat(document.getElementById("input-sca-cuerpo")?.value),I=parseFloat(document.getElementById("input-sca-balance")?.value),w=parseFloat(document.getElementById("input-sca-uniformidad")?.value),_=parseFloat(document.getElementById("input-sca-taza-limpia")?.value),k=parseFloat(document.getElementById("input-sca-dulzor")?.value),$=parseFloat(document.getElementById("input-sca-global")?.value),s={};isNaN(y)||(s.fragancia_aroma=y),isNaN(E)||(s.sabor=E),isNaN(h)||(s.retrogusto=h),isNaN(L)||(s.acidez=L),isNaN(B)||(s.cuerpo=B),isNaN(I)||(s.balance=I),isNaN(w)||(s.uniformidad=w),isNaN(_)||(s.taza_limpia=_),isNaN(k)||(s.dulzor=k),isNaN($)||(s.puntaje_global=$);const j=A();u.saveLocalRecipe({id:`rec-${Date.now()}`,cafe:e,metodo:a,gramos_cafe:n,gramos_agua:o,molienda:D,tiempo:T,calificacion:x,notas:z,catacion_sca:Object.keys(s).length>0?s:void 0,puntuacion_sca_total:j||void 0,fecha:new Date().toISOString()}),N.reset(),i&&(i.textContent="Sin calificar"),m(),d(),b(),F.trackRecipeSaved(a,e,x)});J?.addEventListener("click",async()=>{try{const t=await u.syncToCloud();t.success?(alert("☁️ "+t.message),F.trackRecipeCloudSynced(t.count)):alert(t.message)}catch{alert("Modo sin conexión: Tus recetas siguen guardadas en este dispositivo.")}});b();m();
