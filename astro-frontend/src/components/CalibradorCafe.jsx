/*  */import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { DialInCalculator, DIAL_IN_METHODS } from '../core/domain/DialInCalculator';

export default function CalibradorCafe() {
  // 1. Estado del Método y Parámetros Iniciales
  const [metodoKey, setMetodoKey] = useState('v60');
  const [dosis, setDosis] = useState(15);
  const [agua, setAgua] = useState(240);
  const [clicks, setClicks] = useState(18);
  const [temperatura, setTemperatura] = useState(93);
  const [tiempo, setTiempo] = useState(180);
  const [modoAjuste, setModoAjuste] = useState('agua'); // 'agua' | 'dosis'

  // 2. Estado del Plano Cartesiano [-1 a +1]
  // Coordenadas iniciales: ligeramente subextraído y pesado para incentivar interacción
  const [posicion, setPosicion] = useState({ x: -0.4, y: 0.3 });
  const [isDragging, setIsDragging] = useState(false);

  // 3. Estado de UI y Feedback
  const [guardadoToast, setGuardadoToast] = useState(null);
  const svgRef = useRef(null);
  const lastEmittedEventRef = useRef('');

  // Sincronizar parámetros al cambiar de método
  const seleccionarMetodo = (key) => {
    const preset = DIAL_IN_METHODS[key];
    if (!preset) return;
    setMetodoKey(key);
    setDosis(preset.dosis);
    setAgua(preset.agua);
    setClicks(preset.clicks);
    setTemperatura(preset.temperatura);
    setTiempo(preset.tiempo);
  };

  // Cálculo del Dial-in
  const resultado = useMemo(() => {
    return DialInCalculator.calculate({
      metodo: metodoKey,
      dosis,
      agua,
      clicks,
      temperatura,
      tiempo,
      x: posicion.x,
      y: posicion.y,
      modoAjuste
    });
  }, [metodoKey, dosis, agua, clicks, temperatura, tiempo, posicion.x, posicion.y, modoAjuste]);

  // Emisión debounced a Google Tag Manager
  useEffect(() => {
    const eventKey = `${metodoKey}_${resultado.deltaRatio}_${resultado.deltaClicks}`;
    if (lastEmittedEventRef.current === eventKey) return;

    const timer = setTimeout(() => {
      if (typeof window !== 'undefined' && window.dataLayer) {
        window.dataLayer.push({
          event: 'calibracion_receta_calculada',
          metodo: metodoKey,
          ajuste_ratio: resultado.deltaRatio,
          ajuste_molienda: resultado.deltaClicks
        });
        lastEmittedEventRef.current = eventKey;
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [metodoKey, resultado.deltaRatio, resultado.deltaClicks]);

  // Mapeo coordenadas SVG: [40 a 360] -> [-1 a 1]
  // centro en (200, 200), radio 160
  const SVG_CENTER = 200;
  const SVG_RADIUS = 150;

  const coordToSvg = useCallback((x, y) => {
    return {
      cx: SVG_CENTER + x * SVG_RADIUS,
      cy: SVG_CENTER - y * SVG_RADIUS // Inversión: +Y arriba
    };
  }, []);

  const svgToCoord = useCallback((clientX, clientY) => {
    if (!svgRef.current) return { x: 0, y: 0 };
    const rect = svgRef.current.getBoundingClientRect();
    const pixelX = ((clientX - rect.left) / rect.width) * 400;
    const pixelY = ((clientY - rect.top) / rect.height) * 400;

    let x = (pixelX - SVG_CENTER) / SVG_RADIUS;
    let y = -(pixelY - SVG_CENTER) / SVG_RADIUS;

    x = Math.max(-1, Math.min(1, Math.round(x * 100) / 100));
    y = Math.max(-1, Math.min(1, Math.round(y * 100) / 100));
    return { x, y };
  }, []);

  // Manejadores de Pointer Events siguiendo guía Modern Web 'drag'
  const handlePointerDown = (e) => {
    if (e.button !== 0) return;
    const { x, y } = svgToCoord(e.clientX, e.clientY);
    setPosicion({ x, y });
    setIsDragging(true);
    if (svgRef.current) {
      svgRef.current.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e) => {
    if (!isDragging) return;
    const { x, y } = svgToCoord(e.clientX, e.clientY);
    setPosicion({ x, y });
  };

  const handlePointerUp = (e) => {
    if (isDragging) {
      setIsDragging(false);
      if (svgRef.current && svgRef.current.hasPointerCapture(e.pointerId)) {
        svgRef.current.releasePointerCapture(e.pointerId);
      }
    }
  };

  // Accesibilidad por Teclado
  const handleKeyDown = (e) => {
    const STEP = 0.05;
    let newX = posicion.x;
    let newY = posicion.y;

    if (e.key === 'ArrowLeft') {
      newX = Math.max(-1, newX - STEP);
      e.preventDefault();
    } else if (e.key === 'ArrowRight') {
      newX = Math.min(1, newX + STEP);
      e.preventDefault();
    } else if (e.key === 'ArrowUp') {
      newY = Math.min(1, newY + STEP);
      e.preventDefault();
    } else if (e.key === 'ArrowDown') {
      newY = Math.max(-1, newY - STEP);
      e.preventDefault();
    } else {
      return;
    }

    setPosicion({
      x: Math.round(newX * 100) / 100,
      y: Math.round(newY * 100) / 100
    });
  };

  // Guardar en Mis Recetas (localStorage compatible con ManageRecipesUseCase)
  const guardarEnBitacora = () => {
    try {
      const KEY_RECIPES = 'cafesitios_recetas_v1';
      const raw = localStorage.getItem(KEY_RECIPES);
      const lista = raw ? JSON.parse(raw) : [];

      const metodoActual = DIAL_IN_METHODS[metodoKey]?.nombre || metodoKey;
      const minutos = Math.floor(resultado.tiempoSugerido / 60);
      const segundos = resultado.tiempoSugerido % 60;
      const tiempoStr = `${minutos}:${segundos.toString().padStart(2, '0')} min`;

      const nuevaReceta = {
        id: `dialin-${Date.now()}`,
        cafe: `Calibrado: ${metodoActual}`,
        metodo: metodoActual,
        gramos_cafe: modoAjuste === 'agua' ? dosis : resultado.dosisSugerida,
        gramos_agua: modoAjuste === 'agua' ? resultado.aguaSugerida : agua,
        molienda: `${resultado.clicksSugeridos} clicks (${resultado.deltaClicks <= 0 ? 'fino' : 'grueso'})`,
        tiempo: tiempoStr,
        calificacion: 5,
        notas: `[Calibrador Sensorial Cafesitios] Diagnóstico: ${resultado.cuadrante}. ${resultado.pasosTacticos.join(' ')}`,
        fecha: new Date().toISOString()
      };

      lista.unshift(nuevaReceta);
      localStorage.setItem(KEY_RECIPES, JSON.stringify(lista));

      setGuardadoToast({
        id: nuevaReceta.id,
        mensaje: '¡Receta calibrada guardada exitosamente en Mis Recetas!'
      });

      setTimeout(() => {
        setGuardadoToast(null);
      }, 5000);
    } catch (err) {
      console.error('Error al guardar en bitácora:', err);
    }
  };

  const { cx, cy } = coordToSvg(posicion.x, posicion.y);

  // Formato de tiempo para visualización
  const formatearTiempo = (segundos) => {
    const m = Math.floor(segundos / 60);
    const s = segundos % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8 font-sans text-stone-800">
      
      {/* CABECERA HERO DEL CALIBRADOR */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-stone-900 via-emerald-950 to-stone-900 text-white p-6 sm:p-10 shadow-xl border border-emerald-900/40">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/20 px-3.5 py-1 text-xs font-semibold text-emerald-300 border border-emerald-400/30">
            <span>🎯</span>
            <span>Dial-in Assistant • Calibrador Sensorial de Extracción</span>
          </div>

          <h2 className="text-2xl sm:text-4xl font-black tracking-tight text-white">
            Calibra tu Café hacia la <span className="text-emerald-400">Zona Ideal</span>
          </h2>

          <p className="text-xs sm:text-sm text-stone-300 leading-relaxed">
            Ubica el sabor que percibes en tu taza actual sobre el mapa sensorial 2D. Nuestro motor calculará en tiempo real los ajustes exactos de molienda, ratio, temperatura y tiempo para desbloquear el máximo dulzor y claridad.
          </p>
        </div>
      </div>

      {/* SECCIÓN PRINCIPAL: 2 COLUMNAS (CONTROLES/PLANO + PANEL RESULTADOS) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* COLUMNA IZQUIERDA: CONFIGURACIÓN Y PLANO SENSORIAL (7 COLS) */}
        <div className="lg:col-span-7 space-y-6">

          {/* 1. SELECTOR DE MÉTODO */}
          <div className="bg-white rounded-3xl p-5 sm:p-6 border border-stone-200/80 shadow-xs space-y-3">
            <label className="block text-xs font-bold uppercase tracking-wider text-stone-500">
              1. Selecciona tu Método de Preparación
            </label>

            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
              {Object.values(DIAL_IN_METHODS).map((metodo) => {
                const activo = metodoKey === metodo.id;
                return (
                  <button
                    key={metodo.id}
                    type="button"
                    onClick={() => seleccionarMetodo(metodo.id)}
                    className={`flex flex-col items-center justify-center p-3 rounded-2xl border transition text-center ${
                      activo
                        ? 'bg-emerald-900 border-emerald-800 text-white shadow-sm ring-2 ring-emerald-600/30 font-bold'
                        : 'bg-stone-50 hover:bg-stone-100 border-stone-200 text-stone-700 font-medium'
                    }`}
                  >
                    <span className="text-xl mb-1">{metodo.icono}</span>
                    <span className="text-xs leading-tight">{metodo.nombre}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. PARÁMETROS DE LA RECETA ACTUAL */}
          <div className="bg-white rounded-3xl p-5 sm:p-6 border border-stone-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-bold uppercase tracking-wider text-stone-500">
                2. Parámetros de tu Receta Actual
              </label>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-stone-100 text-stone-600 border border-stone-200">
                Ratio actual: 1:{resultado.ratioActual}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Dosis Café (g)</label>
                <input
                  type="number"
                  min="5"
                  max="60"
                  step="0.5"
                  value={dosis}
                  onChange={(e) => setDosis(parseFloat(e.target.value) || 1)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Agua Total (ml)</label>
                <input
                  type="number"
                  min="20"
                  max="1000"
                  step="5"
                  value={agua}
                  onChange={(e) => setAgua(parseFloat(e.target.value) || 10)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Molienda (clicks)</label>
                <input
                  type="number"
                  min="1"
                  max="45"
                  step="1"
                  value={clicks}
                  onChange={(e) => setClicks(parseInt(e.target.value, 10) || 1)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Temperatura (°C)</label>
                <input
                  type="number"
                  min="75"
                  max="98"
                  step="1"
                  value={temperatura}
                  onChange={(e) => setTemperatura(parseInt(e.target.value, 10) || 90)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Tiempo (segundos)</label>
                <input
                  type="number"
                  min="15"
                  max="600"
                  step="5"
                  value={tiempo}
                  onChange={(e) => setTiempo(parseInt(e.target.value, 10) || 60)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-stone-600 mb-1">Ajustar Ratio Vía</label>
                <select
                  value={modoAjuste}
                  onChange={(e) => setModoAjuste(e.target.value)}
                  className="w-full rounded-xl bg-stone-50 border border-stone-200 px-3 py-2 text-xs font-bold text-stone-800 focus:bg-white focus:border-emerald-600 focus:outline-none cursor-pointer"
                >
                  <option value="agua">Agua (Dosis fija)</option>
                  <option value="dosis">Dosis café (Agua fija)</option>
                </select>
              </div>
            </div>
          </div>

          {/* 3. PLANO CARTESIANO INTERACTIVO */}
          <div className="bg-white rounded-3xl p-5 sm:p-6 border border-stone-200/80 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-100 pb-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-stone-500">
                  3. Sitúa el Sabor Percibido en el Plano 2D
                </label>
                <span className="text-[11px] text-stone-400">
                  Haz clic, arrastra el círculo o usa las flechas del teclado.
                </span>
              </div>

              {/* Botón Reset */}
              <button
                type="button"
                onClick={() => setPosicion({ x: 0, y: 0 })}
                className="self-start sm:self-auto text-[11px] font-bold text-stone-600 hover:text-emerald-800 bg-stone-100 hover:bg-stone-200 px-3 py-1 rounded-lg transition"
              >
                Centrar en Zona Ideal
              </button>
            </div>

            {/* PRESETS RÁPIDOS DE SABOR */}
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              <span className="text-stone-400 font-medium py-0.5">Probar perfiles:</span>
              <button
                type="button"
                onClick={() => setPosicion({ x: -0.65, y: -0.1 })}
                className="rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200/80 px-2 py-0.5 font-semibold transition"
              >
                🍋 Agrio / Ácido punzante
              </button>
              <button
                type="button"
                onClick={() => setPosicion({ x: 0.65, y: 0.1 })}
                className="rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-800 border border-stone-200 px-2 py-0.5 font-semibold transition"
              >
                🪵 Amargo seco / Astringente
              </button>
              <button
                type="button"
                onClick={() => setPosicion({ x: 0.05, y: 0.7 })}
                className="rounded-lg bg-red-50 hover:bg-red-100 text-red-800 border border-red-200/80 px-2 py-0.5 font-semibold transition"
              >
                💥 Muy pesado / Saturado
              </button>
              <button
                type="button"
                onClick={() => setPosicion({ x: -0.05, y: -0.7 })}
                className="rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200/80 px-2 py-0.5 font-semibold transition"
              >
                💧 Acuoso / Ralo
              </button>
              <button
                type="button"
                onClick={() => setPosicion({ x: 0.0, y: 0.0 })}
                className="rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 font-semibold transition"
              >
                🌟 Zona Ideal
              </button>
            </div>

            {/* CONTENEDOR SVG CON POINTER EVENTS */}
            <div className="relative aspect-square w-full max-w-md mx-auto select-none touch-none">
              <svg
                ref={svgRef}
                viewBox="0 0 400 400"
                tabIndex={0}
                role="slider"
                aria-label="Plano sensorial de extracción de café"
                aria-valuenow={Math.round(posicion.x * 100)}
                aria-valuemin={-100}
                aria-valuemax={100}
                onKeyDown={handleKeyDown}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                className="w-full h-full rounded-2xl bg-[#FAF8F5] border-2 border-stone-300 shadow-inner cursor-crosshair focus:outline-none focus:ring-2 focus:ring-emerald-600 transition"
                style={{
                  touchAction: 'none',
                  WebkitUserSelect: 'none',
                  userSelect: 'none'
                }}
              >
                <defs>
                  {/* Flecha vector de corrección */}
                  <marker
                    id="arrowhead"
                    markerWidth="8"
                    markerHeight="8"
                    refX="6"
                    refY="3"
                    orient="auto"
                  >
                    <polygon points="0 0, 6 3, 0 6" fill="#059669" />
                  </marker>

                  {/* Gradiente radial para la Zona Ideal */}
                  <radialGradient id="idealGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0.05" />
                  </radialGradient>
                </defs>

                {/* CUADRANTES DE FONDO */}
                {/* Cuadrante 1: Subextraído & Fuerte (Top-Left) */}
                <rect x="20" y="20" width="180" height="180" fill="#fef3c7" fillOpacity="0.25" />
                {/* Cuadrante 2: Sobreextraído & Fuerte (Top-Right) */}
                <rect x="200" y="20" width="180" height="180" fill="#fee2e2" fillOpacity="0.25" />
                {/* Cuadrante 3: Subextraído & Débil (Bottom-Left) */}
                <rect x="20" y="200" width="180" height="180" fill="#f0fdf4" fillOpacity="0.25" />
                {/* Cuadrante 4: Sobreextraído & Débil (Bottom-Right) */}
                <rect x="200" y="200" width="180" height="180" fill="#e0f2fe" fillOpacity="0.25" />

                {/* ETIQUETAS DE LOS CUADRANTES */}
                <text x="35" y="45" fontSize="10" fontWeight="bold" fill="#b45309" fillOpacity="0.8">
                  Subextraído + Saturado
                </text>
                <text x="215" y="45" fontSize="10" fontWeight="bold" fill="#b91c1c" fillOpacity="0.8">
                  Sobreextraído + Saturado
                </text>
                <text x="35" y="375" fontSize="10" fontWeight="bold" fill="#047857" fillOpacity="0.8">
                  Subextraído + Acuoso
                </text>
                <text x="215" y="375" fontSize="10" fontWeight="bold" fill="#0369a1" fillOpacity="0.8">
                  Sobreextraído + Acuoso
                </text>

                {/* LÍNEAS DE LOS EJES CARTESIANOS */}
                <line x1="20" y1="200" x2="380" y2="200" stroke="#a8a29e" strokeWidth="1.5" strokeDasharray="3 3" />
                <line x1="200" y1="20" x2="200" y2="380" stroke="#a8a29e" strokeWidth="1.5" strokeDasharray="3 3" />

                {/* ZONA IDEAL CENTRAL (|X| <= 0.2, |Y| <= 0.2 -> 60x60 en centro 200,200) */}
                <rect
                  x="170"
                  y="170"
                  width="60"
                  height="60"
                  rx="10"
                  fill="url(#idealGlow)"
                  stroke="#059669"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />
                <text x="200" y="195" fontSize="9" fontWeight="900" textAnchor="middle" fill="#065f46">
                  ZONA IDEAL
                </text>
                <text x="200" y="208" fontSize="8" fontWeight="bold" textAnchor="middle" fill="#047857">
                  ✨ Dulzor Alto
                </text>

                {/* RÓTULOS DE LOS EJES */}
                {/* Eje Y: Concentración */}
                <text x="200" y="15" fontSize="11" fontWeight="bold" textAnchor="middle" fill="#44403c">
                  ▲ Pesado / Saturado (+1.0)
                </text>
                <text x="200" y="395" fontSize="11" fontWeight="bold" textAnchor="middle" fill="#44403c">
                  ▼ Ligero / Acuoso (-1.0)
                </text>

                {/* Eje X: Extracción */}
                <text x="25" y="215" fontSize="10" fontWeight="bold" textAnchor="start" fill="#78350f">
                  ◄ Subextraído (Ácido)
                </text>
                <text x="375" y="215" fontSize="10" fontWeight="bold" textAnchor="end" fill="#991b1b">
                  Sobreextraído (Amargo) ►
                </text>

                {/* VECTOR DE CORRECCIÓN (Línea desde la posición actual hacia el centro 200,200) */}
                {!resultado.zonaIdeal && (
                  <line
                    x1={cx}
                    y1={cy}
                    x2={200 + (cx > 200 ? 12 : cx < 200 ? -12 : 0)}
                    y2={200 + (cy > 200 ? 12 : cy < 200 ? -12 : 0)}
                    stroke="#059669"
                    strokeWidth="2.5"
                    strokeDasharray="4 3"
                    markerEnd="url(#arrowhead)"
                    opacity="0.8"
                  />
                )}

                {/* PUNTO ACTUAL DEL BARISTA (DRAGGABLE HANDLE) */}
                <g className="cursor-grab active:cursor-grabbing">
                  {/* Halo exterior animado */}
                  <circle
                    cx={cx}
                    cy={cy}
                    r="18"
                    fill={resultado.zonaIdeal ? '#10b981' : '#b45309'}
                    fillOpacity="0.25"
                    className="animate-ping"
                    style={{ animationDuration: '3s' }}
                  />

                  {/* Círculo base interactivo */}
                  <circle
                    cx={cx}
                    cy={cy}
                    r="12"
                    fill={resultado.zonaIdeal ? '#059669' : '#d97706'}
                    stroke="#ffffff"
                    strokeWidth="3"
                    className="filter drop-shadow-md transition-transform"
                  />

                  {/* Icono central dentro del punto */}
                  <text
                    x={cx}
                    y={cy + 3.5}
                    fontSize="9"
                    fontWeight="bold"
                    textAnchor="middle"
                    fill="#ffffff"
                    pointerEvents="none"
                  >
                    {resultado.zonaIdeal ? '★' : '☕'}
                  </text>
                </g>
              </svg>
            </div>

            {/* COORDENADAS NUMÉRICAS Y ESTADO */}
            <div className="flex items-center justify-between text-xs bg-stone-50 rounded-xl px-4 py-2 border border-stone-200 text-stone-600">
              <span className="font-semibold">
                Extracción (X): <strong className={posicion.x < -0.2 ? 'text-amber-700' : posicion.x > 0.2 ? 'text-red-700' : 'text-emerald-700'}>{posicion.x}</strong>
              </span>
              <span className="font-semibold">
                Cuerpo (Y): <strong className={posicion.y > 0.2 ? 'text-red-700' : posicion.y < -0.2 ? 'text-sky-700' : 'text-emerald-700'}>{posicion.y}</strong>
              </span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${resultado.zonaIdeal ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>
                {resultado.cuadrante}
              </span>
            </div>
          </div>
        </div>

        {/* COLUMNA DERECHA: PANEL DE RESULTADOS DINÁMICOS Y NUEVA RECETA (5 COLS) */}
        <div className="lg:col-span-5 space-y-6">

          {/* TARJETA DE DIAGNÓSTICO SENSORIAL */}
          <div className={`rounded-3xl p-6 border shadow-xs transition-all ${
            resultado.zonaIdeal
              ? 'bg-emerald-50/80 border-emerald-300 text-emerald-950'
              : 'bg-amber-50/70 border-amber-200 text-amber-950'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{resultado.zonaIdeal ? '🌟' : '🔍'}</span>
              <h3 className="text-base sm:text-lg font-black tracking-tight">
                {resultado.zonaIdeal ? '¡Estás en la Zona Ideal!' : 'Diagnóstico de tu Taza'}
              </h3>
            </div>

            <p className="text-xs font-semibold leading-relaxed mb-3">
              {resultado.descriptorSabor}
            </p>

            <div className="text-[11px] space-y-1.5 opacity-90 border-t border-black/10 pt-3">
              <div className="flex items-start gap-1.5">
                <span className="font-bold">Extracción:</span>
                <span>{resultado.diagnosticoExtraccion}</span>
              </div>
              <div className="flex items-start gap-1.5">
                <span className="font-bold">Cuerpo:</span>
                <span>{resultado.diagnosticoConcentracion}</span>
              </div>
              <p className="text-[11px] italic mt-2 text-stone-600 bg-white/60 p-2.5 rounded-xl border border-black/5">
                💡 {resultado.explicacionBarista}
              </p>
            </div>
          </div>

          {/* TARJETA COMPARATIVA: NUEVA RECETA CALIBRADA */}
          <div className="bg-white rounded-3xl p-6 border border-stone-200/80 shadow-md space-y-5">
            <div className="flex items-center justify-between border-b border-stone-100 pb-3">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md">
                  Nueva Receta Calibrada
                </span>
                <h4 className="text-base font-black text-stone-900 mt-1">
                  Parámetros Sugeridos
                </h4>
              </div>

              <div className="text-right">
                <span className="text-xs text-stone-400">Ratio sugerido</span>
                <div className="text-sm font-black text-emerald-800">
                  1:{resultado.ratioSugerido}
                  {resultado.deltaRatio !== 0 && (
                    <span className="text-[10px] ml-1 font-bold text-emerald-600">
                      ({resultado.deltaRatio > 0 ? `+${resultado.deltaRatio}` : resultado.deltaRatio})
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* GRILLA DE PARÁMETROS CALIBRADOS */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              
              {/* Dosis de Café */}
              <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
                <span className="block text-[10px] text-stone-500 font-bold uppercase">Dosis Café</span>
                <div className="flex items-baseline justify-between mt-1">
                  <span className="text-sm font-extrabold text-stone-900">
                    {modoAjuste === 'agua' ? `${dosis} g` : `${resultado.dosisSugerida} g`}
                  </span>
                  {modoAjuste === 'dosis' && resultado.deltaDosis !== 0 && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                      resultado.deltaDosis > 0 ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                    }`}>
                      {resultado.deltaDosis > 0 ? `+${resultado.deltaDosis}g` : `${resultado.deltaDosis}g`}
                    </span>
                  )}
                </div>
              </div>

              {/* Agua Total */}
              <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
                <span className="block text-[10px] text-stone-500 font-bold uppercase">Agua Total</span>
                <div className="flex items-baseline justify-between mt-1">
                  <span className="text-sm font-extrabold text-stone-900">
                    {modoAjuste === 'agua' ? `${resultado.aguaSugerida} ml` : `${agua} ml`}
                  </span>
                  {modoAjuste === 'agua' && resultado.deltaAgua !== 0 && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                      resultado.deltaAgua > 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {resultado.deltaAgua > 0 ? `+${resultado.deltaAgua}ml` : `${resultado.deltaAgua}ml`}
                    </span>
                  )}
                </div>
              </div>

              {/* Molienda en Clicks */}
              <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
                <span className="block text-[10px] text-stone-500 font-bold uppercase">Molienda (Clicks)</span>
                <div className="flex items-baseline justify-between mt-1">
                  <span className="text-sm font-extrabold text-stone-900">
                    {resultado.clicksSugeridos} clicks
                  </span>
                  {resultado.deltaClicks !== 0 && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                      resultado.deltaClicks < 0 ? 'bg-sky-100 text-sky-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {resultado.deltaClicks < 0 ? `${resultado.deltaClicks} más fino` : `+${resultado.deltaClicks} más grueso`}
                    </span>
                  )}
                </div>
              </div>

              {/* Temperatura */}
              <div className="p-3 rounded-2xl bg-stone-50 border border-stone-200/80">
                <span className="block text-[10px] text-stone-500 font-bold uppercase">Temperatura</span>
                <div className="flex items-baseline justify-between mt-1">
                  <span className="text-sm font-extrabold text-stone-900">
                    {resultado.temperaturaSugerida}°C
                  </span>
                  {resultado.deltaTemperatura !== 0 && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                      resultado.deltaTemperatura > 0 ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
                    }`}>
                      {resultado.deltaTemperatura > 0 ? `+${resultado.deltaTemperatura}°C` : `${resultado.deltaTemperatura}°C`}
                    </span>
                  )}
                </div>
              </div>

              {/* Tiempo Objetivo */}
              <div className="col-span-2 p-3 rounded-2xl bg-stone-50 border border-stone-200/80 flex items-center justify-between">
                <div>
                  <span className="block text-[10px] text-stone-500 font-bold uppercase">Tiempo Objetivo</span>
                  <span className="text-sm font-extrabold text-stone-900">
                    {formatearTiempo(resultado.tiempoSugerido)} min
                  </span>
                </div>
                {resultado.deltaTiempo !== 0 && (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-stone-200 text-stone-700">
                    Delta: {resultado.deltaTiempo > 0 ? `+${resultado.deltaTiempo}s` : `${resultado.deltaTiempo}s`}
                  </span>
                )}
              </div>
            </div>

            {/* PASOS TÁCTICOS PRIORIZADOS */}
            <div className="space-y-2 border-t border-stone-100 pt-4">
              <span className="block text-xs font-bold uppercase tracking-wider text-stone-500">
                Plan de Acción para tu Próxima Taza
              </span>
              <ol className="space-y-2 text-xs text-stone-700">
                {resultado.pasosTacticos.map((paso, idx) => (
                  <li key={idx} className="flex items-start gap-2 bg-stone-50/80 p-2.5 rounded-xl border border-stone-200/60">
                    <span className="flex-shrink-0 flex items-center justify-center h-5 w-5 rounded-full bg-emerald-800 text-white text-[10px] font-bold">
                      {idx + 1}
                    </span>
                    <span className="leading-snug">{paso}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* BOTÓN PARA GUARDAR EN LA BITÁCORA */}
            <div className="pt-2">
              <button
                type="button"
                onClick={guardarEnBitacora}
                className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-stone-900 hover:bg-emerald-900 text-white font-bold text-xs py-3.5 px-4 shadow-md hover:shadow-lg transition hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-emerald-600"
              >
                <span>💾</span>
                <span>Guardar Receta Calibrada en Mis Recetas</span>
                <span>☕</span>
              </button>
            </div>

            {/* TOAST / ALERTA DE GUARDADO EXITOSO */}
            {guardadoToast && (
              <div className="rounded-2xl bg-emerald-50 border border-emerald-300 p-3.5 text-xs text-emerald-950 flex items-center justify-between animate-fade-in shadow-sm">
                <div className="flex items-center gap-2">
                  <span className="text-base">✅</span>
                  <span className="font-semibold">{guardadoToast.mensaje}</span>
                </div>
                <a
                  href="/mis-recetas"
                  className="font-bold underline text-emerald-800 hover:text-emerald-950 text-[11px] ml-2 flex-shrink-0"
                >
                  Ver en Bitácora →
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

