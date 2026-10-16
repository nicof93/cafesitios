import{L as s}from"./LocalStorageAdapter.CYPMhrtX.js";const t=document.getElementById("recently-viewed-panel"),r=document.getElementById("recently-viewed-items"),i=document.getElementById("btn-clear-recently-viewed");function o(){const n=s.getRecentlyViewed();if(!(!t||!r)){if(n.length===0){t.classList.add("hidden");return}t.classList.remove("hidden"),r.innerHTML=n.map(e=>`
      <a href="/product/${e.id}" class="group flex items-center gap-2.5 p-2 rounded-xl hover:bg-stone-50 transition border border-stone-100/80">
        <img src="${e.imagen||"https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=100"}" alt="${e.nombre}" referrerpolicy="no-referrer" onerror="this.onerror=null; this.src='https://images.unsplash.com/photo-1559056199-641a0ac8b55e?q=80&w=100';" class="w-10 h-10 object-contain rounded-lg bg-[#F4F3ED] flex-shrink-0 p-0.5">
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold text-stone-800 truncate group-hover:text-emerald-800 transition">${e.nombre}</p>
          <p class="text-[10px] text-stone-400">${e.tienda} &bull; <strong class="text-emerald-800 font-bold">$${(e.precio||0).toLocaleString("es-CL")}</strong></p>
        </div>
      </a>
    `).join("")}}i?.addEventListener("click",()=>{s.clearRecentlyViewed(),o()});o();
