import React, { useState, useId } from 'react';
import { COFFEE_ANATOMY_LAYERS, type CoffeeAnatomyLayer } from '../../core/domain/coffeeAnatomyData';

type ViewMode = 'corte' | 'explotada' | 'tueste';

export default function AnatomiaGrano3D() {
  const [selectedLayerId, setSelectedLayerId] = useState<string>('mesocarpio');
  const [viewMode, setViewMode] = useState<ViewMode>('corte');
  const [rotation, setRotation] = useState<{ x: number; y: number }>({ x: 18, y: -22 });
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const baseId = useId();

  const selectedLayer: CoffeeAnatomyLayer =
    COFFEE_ANATOMY_LAYERS.find(l => l.id === selectedLayerId) || COFFEE_ANATOMY_LAYERS[1];

  const handleLayerClick = (id: string) => {
    setSelectedLayerId(id);
  };

  const handleScrollToGlossary = (slug?: string) => {
    if (!slug) return;
    const targetElement = document.getElementById(slug);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      targetElement.classList.add('ring-4', 'ring-emerald-400', 'ring-offset-2', 'ring-offset-stone-900');
      setTimeout(() => {
        targetElement.classList.remove('ring-4', 'ring-emerald-400', 'ring-offset-2', 'ring-offset-stone-900');
      }, 3000);
    }
  };

  return (
    <section 
      id="anatomia-grano"
      aria-label="Infografía 3D de la Anatomía del Grano y la Cereza de Café"
      className="rounded-3xl bg-gradient-to-br from-stone-950 via-stone-900 to-emerald-950/80 border border-emerald-900/40 text-white p-6 sm:p-10 shadow-2xl relative overflow-hidden"
    >
      {/* Luces decorativas ambientales */}
      <div className="absolute -top-32 -right-32 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -left-32 w-80 h-80 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />

      {/* CABECERA DE LA INFOGRAFÍA */}
      <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-stone-800/80">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-950/80 border border-emerald-500/30 px-3 py-1 text-xs font-bold text-emerald-300">
            <span>🔬 Botánica & Estructura 3D</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Anatomía 3D de la Cereza y el Grano de Café
          </h2>
          <p className="text-xs sm:text-sm text-stone-300 leading-relaxed font-normal">
            Explora interactivamente las 7 capas concéntricas que transforman una flor silvestre en los aromas más complejos de tu taza. Haz clic en cualquier capa o punto caliente para desglosar su impacto químico y de beneficio.
          </p>
        </div>

        {/* SELECTOR DE MODO DE VISTA */}
        <div className="flex items-center gap-1.5 p-1 rounded-2xl bg-stone-900/90 border border-stone-800 shadow-inner shrink-0 self-start md:self-auto">
          <button
            type="button"
            onClick={() => setViewMode('corte')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
              viewMode === 'corte'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-stone-400 hover:text-white hover:bg-stone-800/60'
            }`}
          >
            <span>🔪</span>
            <span>Corte 3D</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('explotada')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
              viewMode === 'explotada'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-stone-400 hover:text-white hover:bg-stone-800/60'
            }`}
          >
            <span>💥</span>
            <span>Explotada</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('tueste')}
            className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center gap-1.5 ${
              viewMode === 'tueste'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-stone-400 hover:text-white hover:bg-stone-800/60'
            }`}
          >
            <span>🔥</span>
            <span>Tueste</span>
          </button>
        </div>
      </div>

      {/* ÁREA PRINCIPAL: VISUALIZADOR 3D + FICHA TÉCNICA */}
      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 pt-6 items-start">
        
        {/* COLUMNA IZQUIERDA: CANVAS/SVG 3D INTERACTIVO */}
        <div className="lg:col-span-7 flex flex-col items-center">
          
          {/* Selector rápido de capas (Barra horizontal en móvil / pastillas) */}
          <div className="w-full flex items-center justify-start sm:justify-center gap-1.5 overflow-x-auto pb-3 mb-2 no-scrollbar text-xs">
            {COFFEE_ANATOMY_LAYERS.map(layer => {
              const isSelected = layer.id === selectedLayerId;
              return (
                <button
                  key={layer.id}
                  type="button"
                  onClick={() => handleLayerClick(layer.id)}
                  className={`px-2.5 py-1 rounded-xl text-xs font-bold whitespace-nowrap transition flex items-center gap-1.5 border ${
                    isSelected
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/60 shadow-xs'
                      : 'bg-stone-900/60 text-stone-400 border-stone-800 hover:border-stone-700 hover:text-stone-200'
                  }`}
                >
                  <span
                    className="w-2.5 h-2.5 rounded-full inline-block"
                    style={{ backgroundColor: layer.colorHex }}
                  />
                  <span>{layer.numero}. {layer.nombreComun.split(' ')[0]}</span>
                </button>
              );
            })}
          </div>

          {/* ESCENARIO 3D CON PERSPECTIVA ISOMÉTRICA */}
          <div 
            className="w-full h-80 sm:h-96 rounded-2xl bg-gradient-to-b from-stone-900/80 via-stone-950 to-stone-900 border border-stone-800/80 flex items-center justify-center relative overflow-hidden group select-none shadow-inner"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            style={{ perspective: '1000px' }}
          >
            {/* Rejilla isométrica sutil de fondo */}
            <div className="absolute inset-0 bg-[radial-gradient(#10b98115_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none opacity-40" />

            {/* CONTENEDOR 3D TRANSFORMADO */}
            <div 
              className="w-full h-full flex items-center justify-center transition-transform duration-500 ease-out"
              style={{
                transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
                transformStyle: 'preserve-3d'
              }}
            >
              {viewMode === 'corte' && (
                /* 1. MODO CORTE TRANSVERSAL 3D */
                <svg
                  viewBox="0 0 500 400"
                  className="w-72 sm:w-96 h-72 sm:h-96 drop-shadow-2xl transition-all"
                  aria-label="Corte transversal de cereza y grano"
                >
                  <defs>
                    <radialGradient id={`${baseId}-glow`} cx="50%" cy="50%" r="50%">
                      <stop offset="0%" stopColor="#10B981" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
                    </radialGradient>
                    <linearGradient id={`${baseId}-exocarpio-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#EF4444" />
                      <stop offset="60%" stopColor="#DC2626" />
                      <stop offset="100%" stopColor="#7F1D1D" />
                    </linearGradient>
                    <linearGradient id={`${baseId}-mesocarpio-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#FDE68A" />
                      <stop offset="40%" stopColor="#F59E0B" />
                      <stop offset="100%" stopColor="#B45309" />
                    </linearGradient>
                    <linearGradient id={`${baseId}-endocarpio-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#FEF3C7" />
                      <stop offset="60%" stopColor="#D97706" />
                      <stop offset="100%" stopColor="#92400E" />
                    </linearGradient>
                    <linearGradient id={`${baseId}-silverskin-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#F1F5F9" />
                      <stop offset="50%" stopColor="#CBD5E1" />
                      <stop offset="100%" stopColor="#64748B" />
                    </linearGradient>
                    <linearGradient id={`${baseId}-endospermo-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#6EE7B7" />
                      <stop offset="40%" stopColor="#10B981" />
                      <stop offset="100%" stopColor="#065F46" />
                    </linearGradient>
                    <filter id={`${baseId}-shadow`} x="-20%" y="-20%" width="140%" height="140%">
                      <feDropShadow dx="0" dy="12" stdDeviation="10" floodColor="#000000" floodOpacity="0.6" />
                    </filter>
                  </defs>

                  {/* Sombra proyectada en la base */}
                  <ellipse cx="250" cy="360" rx="150" ry="25" fill="#000000" opacity="0.45" filter="blur(6px)" />

                  {/* 1. EXOCARPIO (Piel / Cáscara exterior) */}
                  <g 
                    onClick={() => handleLayerClick('exocarpio')}
                    className="cursor-pointer group/exo transition-opacity"
                  >
                    <ellipse
                      cx="250" cy="200" rx="175" ry="145"
                      fill={`url(#${baseId}-exocarpio-grad)`}
                      stroke={selectedLayerId === 'exocarpio' ? '#FFFFFF' : '#B91C1C'}
                      strokeWidth={selectedLayerId === 'exocarpio' ? 4 : 1.5}
                      filter={`url(#${baseId}-shadow)`}
                      className="transition-all duration-300"
                    />
                    {/* Brillo especular 3D de la cereza madura */}
                    <ellipse cx="200" cy="130" rx="45" ry="25" fill="#FFFFFF" opacity="0.35" transform="rotate(-20 200 130)" />
                  </g>

                  {/* 2. MESOCARPIO (Pulpa y mucílago) */}
                  <g 
                    onClick={() => handleLayerClick('mesocarpio')}
                    className="cursor-pointer group/meso"
                  >
                    <ellipse
                      cx="250" cy="205" rx="145" ry="120"
                      fill={`url(#${baseId}-mesocarpio-grad)`}
                      stroke={selectedLayerId === 'mesocarpio' ? '#FFFFFF' : '#D97706'}
                      strokeWidth={selectedLayerId === 'mesocarpio' ? 4 : 1.5}
                      opacity={selectedLayerId === 'mesocarpio' ? 1 : 0.95}
                    />
                  </g>

                  {/* 3. ENDOCARPIO (Pergamino rígido) */}
                  <g 
                    onClick={() => handleLayerClick('endocarpio')}
                    className="cursor-pointer group/endo"
                  >
                    <ellipse
                      cx="250" cy="208" rx="118" ry="98"
                      fill={`url(#${baseId}-endocarpio-grad)`}
                      stroke={selectedLayerId === 'endocarpio' ? '#FFFFFF' : '#92400E'}
                      strokeWidth={selectedLayerId === 'endocarpio' ? 4 : 1.5}
                    />
                  </g>

                  {/* 4. ESPERMODERMA (Película Plateada / Silverskin) */}
                  <g 
                    onClick={() => handleLayerClick('espermoderma')}
                    className="cursor-pointer group/silver"
                  >
                    <ellipse
                      cx="250" cy="210" rx="96" ry="80"
                      fill={`url(#${baseId}-silverskin-grad)`}
                      stroke={selectedLayerId === 'espermoderma' ? '#FFFFFF' : '#94A3B8'}
                      strokeWidth={selectedLayerId === 'espermoderma' ? 3.5 : 1}
                      strokeDasharray="4 2"
                    />
                  </g>

                  {/* 5. ENDOSPERMO (Semilla / Grano Verde) */}
                  <g 
                    onClick={() => handleLayerClick('endospermo')}
                    className="cursor-pointer group/seed"
                  >
                    {/* Semilla 1 (Lado izquierdo) */}
                    <path
                      d="M 248 140 C 200 140 180 170 180 215 C 180 260 205 285 248 285 Z"
                      fill={`url(#${baseId}-endospermo-grad)`}
                      stroke={selectedLayerId === 'endospermo' ? '#FFFFFF' : '#047857'}
                      strokeWidth={selectedLayerId === 'endospermo' ? 3 : 1.5}
                    />
                    {/* Semilla 2 (Lado derecho) */}
                    <path
                      d="M 252 140 C 300 140 320 170 320 215 C 320 260 295 285 252 285 Z"
                      fill={`url(#${baseId}-endospermo-grad)`}
                      stroke={selectedLayerId === 'endospermo' ? '#FFFFFF' : '#047857'}
                      strokeWidth={selectedLayerId === 'endospermo' ? 3 : 1.5}
                    />
                  </g>

                  {/* 6. SURCO CENTRAL (Center cut) */}
                  <g 
                    onClick={() => handleLayerClick('surcoCentral')}
                    className="cursor-pointer group/cut"
                  >
                    <path
                      d="M 248 145 Q 252 210 249 280"
                      stroke={selectedLayerId === 'surcoCentral' ? '#FCD34D' : '#1E293B'}
                      strokeWidth={selectedLayerId === 'surcoCentral' ? 5 : 3}
                      strokeLinecap="round"
                    />
                    <path
                      d="M 252 145 Q 248 210 251 280"
                      stroke={selectedLayerId === 'surcoCentral' ? '#FCD34D' : '#0F172A'}
                      strokeWidth={selectedLayerId === 'surcoCentral' ? 5 : 3}
                      strokeLinecap="round"
                    />
                  </g>

                  {/* 7. EMBRIÓN (Eje germinal basal) */}
                  <g 
                    onClick={() => handleLayerClick('embrion')}
                    className="cursor-pointer group/emb"
                  >
                    <circle
                      cx="250" cy="275" r={selectedLayerId === 'embrion' ? 8 : 6}
                      fill="#FBBF24"
                      stroke={selectedLayerId === 'embrion' ? '#FFFFFF' : '#B45309'}
                      strokeWidth={2}
                      className="animate-pulse"
                    />
                  </g>

                  {/* PUNTOS CALIENTES / HOTSPOTS NUMERADOS */}
                  <g className="text-[11px] font-black pointer-events-none select-none">
                    {/* 1. Exocarpio */}
                    <circle cx="390" cy="180" r="10" fill="#DC2626" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="390" y="184" textAnchor="middle" fill="#FFFFFF">1</text>

                    {/* 2. Mesocarpio */}
                    <circle cx="360" cy="235" r="10" fill="#D97706" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="360" y="239" textAnchor="middle" fill="#FFFFFF">2</text>

                    {/* 3. Endocarpio */}
                    <circle cx="150" cy="210" r="10" fill="#B45309" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="150" y="214" textAnchor="middle" fill="#FFFFFF">3</text>

                    {/* 4. Espermoderma */}
                    <circle cx="175" cy="245" r="10" fill="#64748B" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="175" y="249" textAnchor="middle" fill="#FFFFFF">4</text>

                    {/* 5. Endospermo */}
                    <circle cx="285" cy="215" r="10" fill="#059669" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="285" y="219" textAnchor="middle" fill="#FFFFFF">5</text>
                  </g>
                </svg>
              )}

              {viewMode === 'explotada' && (
                /* 2. MODO VISTA EXPLOTADA POR CAPAS EN EL ESPACIO 3D */
                <svg
                  viewBox="0 0 500 450"
                  className="w-72 sm:w-96 h-72 sm:h-96 drop-shadow-2xl transition-all"
                  aria-label="Vista explotada isométrica por capas"
                >
                  <g className="transition-all duration-300">
                    {/* Eje guía punteado de ensamble */}
                    <line x1="250" y1="50" x2="250" y2="390" stroke="#10B981" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.3" />

                    {/* Capa 1: Exocarpio (Arriba) */}
                    <g 
                      onClick={() => handleLayerClick('exocarpio')} 
                      className="cursor-pointer group"
                      transform="translate(0, 0)"
                    >
                      <ellipse cx="250" cy="70" rx="140" ry="32" fill="#DC2626" opacity="0.85" stroke={selectedLayerId === 'exocarpio' ? '#FFFFFF' : '#7F1D1D'} strokeWidth={selectedLayerId === 'exocarpio' ? 3 : 1} />
                      <text x="250" y="75" textAnchor="middle" fill="#FFFFFF" className="text-xs font-bold pointer-events-none">1. Exocarpio (Piel)</text>
                    </g>

                    {/* Capa 2: Mesocarpio */}
                    <g 
                      onClick={() => handleLayerClick('mesocarpio')} 
                      className="cursor-pointer group"
                      transform="translate(0, 50)"
                    >
                      <ellipse cx="250" cy="90" rx="125" ry="28" fill="#F59E0B" opacity="0.85" stroke={selectedLayerId === 'mesocarpio' ? '#FFFFFF' : '#B45309'} strokeWidth={selectedLayerId === 'mesocarpio' ? 3 : 1} />
                      <text x="250" y="95" textAnchor="middle" fill="#FFFFFF" className="text-xs font-bold pointer-events-none">2. Mesocarpio (Mucílago)</text>
                    </g>

                    {/* Capa 3: Endocarpio */}
                    <g 
                      onClick={() => handleLayerClick('endocarpio')} 
                      className="cursor-pointer group"
                      transform="translate(0, 100)"
                    >
                      <ellipse cx="250" cy="110" rx="110" ry="25" fill="#D97706" opacity="0.85" stroke={selectedLayerId === 'endocarpio' ? '#FFFFFF' : '#78350F'} strokeWidth={selectedLayerId === 'endocarpio' ? 3 : 1} />
                      <text x="250" y="115" textAnchor="middle" fill="#FFFFFF" className="text-xs font-bold pointer-events-none">3. Endocarpio (Pergamino)</text>
                    </g>

                    {/* Capa 4: Espermoderma */}
                    <g 
                      onClick={() => handleLayerClick('espermoderma')} 
                      className="cursor-pointer group"
                      transform="translate(0, 150)"
                    >
                      <ellipse cx="250" cy="130" rx="95" ry="22" fill="#94A3B8" opacity="0.85" stroke={selectedLayerId === 'espermoderma' ? '#FFFFFF' : '#475569'} strokeWidth={selectedLayerId === 'espermoderma' ? 3 : 1} strokeDasharray="3 2" />
                      <text x="250" y="135" textAnchor="middle" fill="#0F172A" className="text-xs font-bold pointer-events-none">4. Espermoderma (Silverskin)</text>
                    </g>

                    {/* Capa 5 & 6: Endospermo y Surco Central */}
                    <g 
                      onClick={() => handleLayerClick('endospermo')} 
                      className="cursor-pointer group"
                      transform="translate(0, 200)"
                    >
                      <ellipse cx="250" cy="150" rx="80" ry="22" fill="#10B981" opacity="0.9" stroke={selectedLayerId === 'endospermo' ? '#FFFFFF' : '#065F46'} strokeWidth={selectedLayerId === 'endospermo' ? 3 : 1} />
                      <path d="M 235 150 Q 250 152 265 150" stroke="#064E3B" strokeWidth="3" />
                      <text x="250" y="155" textAnchor="middle" fill="#FFFFFF" className="text-xs font-bold pointer-events-none">5. Grano Verde & Surco</text>
                    </g>

                    {/* Capa 7: Embrión */}
                    <g 
                      onClick={() => handleLayerClick('embrion')} 
                      className="cursor-pointer group"
                      transform="translate(0, 240)"
                    >
                      <circle cx="250" cy="165" r="10" fill="#FBBF24" stroke={selectedLayerId === 'embrion' ? '#FFFFFF' : '#B45309'} strokeWidth="2" className="animate-pulse" />
                      <text x="250" y="190" textAnchor="middle" fill="#FCD34D" className="text-xs font-bold pointer-events-none">7. Embrión Vital</text>
                    </g>
                  </g>
                </svg>
              )}

              {viewMode === 'tueste' && (
                /* 3. MODO COMPARACIÓN DE TRANSFORMACIÓN DE TUESTE */
                <svg
                  viewBox="0 0 500 400"
                  className="w-72 sm:w-96 h-72 sm:h-96 drop-shadow-2xl transition-all"
                  aria-label="Transformación de grano verde a grano tostado"
                >
                  <defs>
                    <linearGradient id={`${baseId}-roasted-grad`} x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#78350F" />
                      <stop offset="50%" stopColor="#451A03" />
                      <stop offset="100%" stopColor="#1C1917" />
                    </linearGradient>
                  </defs>

                  {/* LADO IZQUIERDO: GRANO VERDE */}
                  <g className="cursor-pointer" onClick={() => handleLayerClick('endospermo')}>
                    <ellipse cx="160" cy="200" rx="70" ry="100" fill="#10B981" stroke="#047857" strokeWidth="2" />
                    <path d="M 160 115 Q 166 200 160 285" stroke="#064E3B" strokeWidth="4" strokeLinecap="round" />
                    <text x="160" y="325" textAnchor="middle" fill="#34D399" className="text-xs font-bold">Grano Verde (Crudo)</text>
                    <text x="160" y="342" textAnchor="middle" fill="#94A3B8" className="text-[10px]">Humedad: 10-12% • Denso</text>
                  </g>

                  {/* FLECHA CENTRAL DE REACCIÓN MAILLARD */}
                  <g className="text-amber-400">
                    <line x1="240" y1="200" x2="270" y2="200" stroke="#F59E0B" strokeWidth="3" markerEnd="url(#arrow)" />
                    <text x="255" y="180" textAnchor="middle" fill="#FBBF24" className="text-[10px] font-black tracking-wider uppercase">Maillard</text>
                    <text x="255" y="225" textAnchor="middle" fill="#FBBF24" className="text-[10px] font-black tracking-wider uppercase">+60% Vol</text>
                  </g>

                  {/* LADO DERECHO: GRANO TOSTADO */}
                  <g className="cursor-pointer" onClick={() => handleLayerClick('surcoCentral')}>
                    <ellipse cx="345" cy="200" rx="90" ry="118" fill={`url(#${baseId}-roasted-grad)`} stroke="#D97706" strokeWidth="2" />
                    {/* Surco central abierto con chaff residual */}
                    <path d="M 345 105 Q 355 200 345 295" stroke="#FDE68A" strokeWidth="5" strokeLinecap="round" opacity="0.9" />
                    <text x="345" y="340" textAnchor="middle" fill="#F59E0B" className="text-xs font-bold">Grano Tostado (Ready)</text>
                    <text x="345" y="357" textAnchor="middle" fill="#94A3B8" className="text-[10px]">Humedad: 1-2% • Poroso • Frágil</text>
                  </g>
                </svg>
              )}
            </div>

            {/* CONTROLES DE ROTACIÓN 3D INTERACTIVA */}
            <div className="absolute bottom-3 left-3 flex items-center gap-2 bg-stone-900/90 backdrop-blur-xs border border-stone-800 rounded-xl px-2.5 py-1 text-[11px] text-stone-400">
              <span>🔄 Ángulo:</span>
              <button 
                type="button"
                onClick={() => setRotation(r => ({ ...r, y: r.y - 15 }))}
                className="hover:text-emerald-400 transition"
                title="Girar a la izquierda"
              >
                ◀
              </button>
              <button 
                type="button"
                onClick={() => setRotation({ x: 18, y: -22 })}
                className="hover:text-white font-mono transition text-[10px]"
                title="Reiniciar perspectiva"
              >
                Reset
              </button>
              <button 
                type="button"
                onClick={() => setRotation(r => ({ ...r, y: r.y + 15 }))}
                className="hover:text-emerald-400 transition"
                title="Girar a la derecha"
              >
                ▶
              </button>
            </div>

            <span className="absolute bottom-3 right-3 text-[10px] text-stone-500 font-mono hidden sm:inline">
              Arrastra o haz clic en las capas
            </span>
          </div>

        </div>

        {/* COLUMNA DERECHA: FICHA TÉCNICA DINÁMICA DE LA CAPA SELECCIONADA */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-2xl bg-stone-900/90 border border-stone-800 p-6 space-y-4 shadow-xl">
            
            {/* ENCABEZADO DE CAPA */}
            <div className="flex items-start justify-between gap-3 border-b border-stone-800/80 pb-3">
              <div className="flex items-center gap-3">
                <span className="text-3xl p-2.5 rounded-2xl bg-stone-800/80 border border-stone-700/80 shadow-inner">
                  {selectedLayer.icono}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span 
                      className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider text-white"
                      style={{ backgroundColor: selectedLayer.colorHex }}
                    >
                      Capa #{selectedLayer.numero}
                    </span>
                    <span className="text-xs text-stone-400 font-serif italic">
                      {selectedLayer.nombreBotanico}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-0.5">
                    {selectedLayer.nombreComun}
                  </h3>
                </div>
              </div>
            </div>

            {/* RESUMEN FUNCIONAL */}
            <p className="text-xs text-stone-300 leading-relaxed font-normal">
              {selectedLayer.resumen}
            </p>

            {/* IMPACTO EN TAZA (SECCIÓN CRÍTICA DE ESPECIALIDAD) */}
            <div className="rounded-xl bg-emerald-950/40 border border-emerald-500/20 p-3.5 space-y-1.5">
              <span className="text-[11px] font-bold text-emerald-400 flex items-center gap-1.5">
                <span>☕ Impacto Directo en la Taza:</span>
              </span>
              <p className="text-xs text-stone-200 leading-relaxed">
                {selectedLayer.impactoEnTaza}
              </p>
            </div>

            {/* ROL BIOLÓGICO */}
            <div className="space-y-1">
              <span className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">
                Función en la Planta:
              </span>
              <p className="text-xs text-stone-400 leading-relaxed">
                {selectedLayer.rolBiologico}
              </p>
            </div>

            {/* COMPOSICIÓN QUÍMICA & ATRIBUTOS */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-bold text-stone-500 uppercase tracking-wider">
                Compuestos Clave:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {selectedLayer.atributosQuimicos.map(item => (
                  <span 
                    key={item}
                    className="rounded-lg bg-stone-800/90 border border-stone-700/60 px-2 py-0.5 text-[10px] text-stone-300 font-medium"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>

            {/* PROCESOS RELACIONADOS Y ANCLAJE AL GLOSARIO */}
            <div className="pt-2 border-t border-stone-800/80 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs text-stone-400">
                <span className="text-stone-500 text-[10px] uppercase font-bold">Procesos:</span>
                <span className="text-stone-300 text-xs font-medium">
                  {selectedLayer.procesosRelacionados.join(' • ')}
                </span>
              </div>

              {selectedLayer.terminoGlosarioSlug && (
                <button
                  type="button"
                  onClick={() => handleScrollToGlossary(selectedLayer.terminoGlosarioSlug)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-400 hover:text-emerald-300 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-500/30 px-3 py-1.5 rounded-xl transition shadow-2xs"
                >
                  <span>Ver concepto en el glosario</span>
                  <span>↓</span>
                </button>
              )}
            </div>

          </div>
        </div>

      </div>

    </section>
  );
}
