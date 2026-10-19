export interface DialInMethodPreset {
  id: string;
  nombre: string;
  icono: string;
  dosis: number;
  agua: number;
  clicks: number;
  temperatura: number;
  tiempo: number; // en segundos
  unidadMolienda: string;
}

export const DIAL_IN_METHODS: Record<string, DialInMethodPreset> = {
  v60: {
    id: 'v60',
    nombre: 'Hario V60',
    icono: '☕',
    dosis: 15,
    agua: 240,
    clicks: 18,
    temperatura: 93,
    tiempo: 180, // 3:00 min
    unidadMolienda: 'clicks'
  },
  aeropress: {
    id: 'aeropress',
    nombre: 'AeroPress',
    icono: '🧪',
    dosis: 15,
    agua: 220,
    clicks: 14,
    temperatura: 90,
    tiempo: 120, // 2:00 min
    unidadMolienda: 'clicks'
  },
  espresso: {
    id: 'espresso',
    nombre: 'Espresso',
    icono: '⚡',
    dosis: 18,
    agua: 36,
    clicks: 6,
    temperatura: 93,
    tiempo: 28, // 28 seg
    unidadMolienda: 'clicks finos'
  },
  moka: {
    id: 'moka',
    nombre: 'Moka Italiana',
    icono: '🫖',
    dosis: 16,
    agua: 180,
    clicks: 10,
    temperatura: 91,
    tiempo: 240, // 4:00 min
    unidadMolienda: 'clicks'
  },
  prensa: {
    id: 'prensa',
    nombre: 'Prensa Francesa',
    icono: '🏺',
    dosis: 20,
    agua: 300,
    clicks: 24,
    temperatura: 94,
    tiempo: 270, // 4:30 min
    unidadMolienda: 'clicks gruesos'
  }
};

export interface DialInInput {
  metodo: string;
  dosis: number;
  agua: number;
  clicks: number;
  temperatura: number;
  tiempo: number; // segundos
  x: number; // [-1 a +1] Extracción
  y: number; // [-1 a +1] Concentración
  modoAjuste?: 'agua' | 'dosis';
}

export interface DialInResult {
  zonaIdeal: boolean;
  cuadrante: string;
  descriptorSabor: string;
  
  // Parámetros actuales
  ratioActual: number;
  
  // Ajustes de Concentración / Ratio (Eje Y)
  deltaRatio: number;
  ratioSugerido: number;
  dosisSugerida: number;
  deltaDosis: number;
  aguaSugerida: number;
  deltaAgua: number;
  
  // Ajustes de Extracción (Eje X)
  deltaClicks: number;
  clicksSugeridos: number;
  deltaTemperatura: number;
  temperaturaSugerida: number;
  deltaTiempo: number;
  tiempoSugerido: number;
  
  // Diagnósticos y recomendaciones
  diagnosticoExtraccion: string;
  diagnosticoConcentracion: string;
  pasosTacticos: string[];
  explicacionBarista: string;
}

export class DialInCalculator {
  static calculate(input: DialInInput): DialInResult {
    const x = Math.max(-1, Math.min(1, input.x));
    const y = Math.max(-1, Math.min(1, input.y));
    const modoAjuste = input.modoAjuste || 'agua';
    
    const dosis = Math.max(1, input.dosis);
    const agua = Math.max(5, input.agua);
    const clicks = Math.max(1, input.clicks);
    const temperatura = Math.max(70, Math.min(96, input.temperatura));
    const tiempo = Math.max(10, input.tiempo);

    const ratioActual = Math.round((agua / dosis) * 10) / 10;
    const esIdealX = Math.abs(x) <= 0.2;
    const esIdealY = Math.abs(y) <= 0.2;
    const zonaIdeal = esIdealX && esIdealY;

    // --- CORRECCIÓN DE CONCENTRACIÓN (EJE Y - MOVIMIENTO EN ARCO) ---
    let deltaRatio = 0;
    if (y > 0.2) {
      // Muy pesado / saturado -> Abrir ratio (más agua por gramo de café o menos café)
      deltaRatio = Math.round(y * 1.8 * 10) / 10;
    } else if (y < -0.2) {
      // Muy ligero / acuoso -> Cerrar ratio (menos agua por gramo o más café)
      deltaRatio = Math.round(y * 1.8 * 10) / 10;
    }

    const ratioSugerido = Math.max(1.5, Math.round((ratioActual + deltaRatio) * 10) / 10);
    
    // Si ajustamos agua manteniendo dosis fija:
    const aguaSugerida = Math.round(dosis * ratioSugerido);
    const deltaAgua = aguaSugerida - agua;

    // Si ajustamos dosis manteniendo agua fija:
    const dosisSugerida = Math.round((agua / ratioSugerido) * 10) / 10;
    const deltaDosis = Math.round((dosisSugerida - dosis) * 10) / 10;

    // --- CORRECCIÓN DE EXTRACCIÓN (EJE X - MOVIMIENTO EN DIAGONAL) ---
    let deltaClicks = 0;
    let deltaTemperatura = 0;
    let deltaTiempo = 0;

    if (x < -0.2) {
      // Subextracción (ácido punzante, agrio, poco dulce)
      // Molienda más fina (clicks negativos)
      deltaClicks = -Math.max(1, Math.round(Math.abs(x) * 2.5));
      // Subir temperatura (+1 a +2 °C)
      deltaTemperatura = Math.abs(x) > 0.5 ? 2 : 1;
      if (temperatura + deltaTemperatura > 96) {
        deltaTemperatura = Math.max(0, 96 - temperatura);
      }
      // Aumentar tiempo de contacto / agitación
      deltaTiempo = Math.max(5, Math.round(tiempo * 0.1));
    } else if (x > 0.2) {
      // Sobreextracción (amargo seco, astringente, cenizo)
      // Molienda más gruesa (clicks positivos)
      deltaClicks = Math.max(1, Math.round(x * 2.5));
      // Bajar temperatura (-1 a -2 °C)
      deltaTemperatura = x > 0.5 ? -2 : -1;
      if (temperatura + deltaTemperatura < 85) {
        deltaTemperatura = Math.min(0, 85 - temperatura);
      }
      // Reducir tiempo de contacto
      deltaTiempo = -Math.max(5, Math.round(tiempo * 0.1));
    }

    const clicksSugeridos = Math.max(1, clicks + deltaClicks);
    const temperaturaSugerida = Math.min(96, Math.max(82, temperatura + deltaTemperatura));
    const tiempoSugerido = Math.max(15, tiempo + deltaTiempo);

    // --- DIAGNÓSTICOS Y CUADRANTE ---
    let cuadrante = 'Zona Central Ideal';
    let descriptorSabor = 'Dulzor, acidez balanceada y cuerpo sedoso';
    let diagnosticoExtraccion = 'Extracción balanceada';
    let diagnosticoConcentracion = 'Cuerpo y concentración óptimos';

    if (zonaIdeal) {
      cuadrante = 'Zona Ideal (Golden Cup)';
      descriptorSabor = 'Taza balanceada, alta claridad, dulzor pronunciado y final limpio.';
    } else {
      if (x < -0.2 && y > 0.2) {
        cuadrante = 'Subextraído y Saturado';
        descriptorSabor = 'Agrio, ácido punzante, sensación densa o abrumadora.';
        diagnosticoExtraccion = 'Subextracción: faltó disolver azúcares y notas aromáticas.';
        diagnosticoConcentracion = 'Saturación: demasiados solubles disueltos en muy poca agua.';
      } else if (x > 0.2 && y > 0.2) {
        cuadrante = 'Sobreextraído y Saturado';
        descriptorSabor = 'Amargo punzante, astringente, pesado y seco.';
        diagnosticoExtraccion = 'Sobreextracción: disolución excesiva de compuestos amargos y taninos.';
        diagnosticoConcentracion = 'Saturación: bebida extremadamente concentrada.';
      } else if (x < -0.2 && y < -0.2) {
        cuadrante = 'Subextraído y Acuoso';
        descriptorSabor = 'Ácido hueco, vegetal, plano, sensación acuosa tipo infusión rala.';
        diagnosticoExtraccion = 'Subextracción: extracción superficial de ácidos rápidos sin cuerpo.';
        diagnosticoConcentracion = 'Acuoso: porcentaje de sólidos disueltos (TDS) muy bajo.';
      } else if (x > 0.2 && y < -0.2) {
        cuadrante = 'Sobreextraído y Acuoso';
        descriptorSabor = 'Amargo seco, raspado astringente al tragar pero sin dulzor ni cuerpo.';
        diagnosticoExtraccion = 'Sobreextracción o canalización (channeling) localizada.';
        diagnosticoConcentracion = 'Acuoso: falta concentración general de la bebida.';
      } else if (x < -0.2) {
        cuadrante = 'Subextraído Puro';
        descriptorSabor = 'Acidez agresiva o salada, falta de dulzor residual.';
        diagnosticoExtraccion = 'Subextracción de origen o molienda.';
      } else if (x > 0.2) {
        cuadrante = 'Sobreextraído Puro';
        descriptorSabor = 'Amargor pronunciado, astringencia y sequedad bucal.';
        diagnosticoExtraccion = 'Sobreextracción de compuestos pesados.';
      } else if (y > 0.2) {
        cuadrante = 'Saturado Puro';
        descriptorSabor = 'Taza muy intensa o pesada, oculta notas de origen.';
        diagnosticoConcentracion = 'Concentración demasiado alta.';
      } else if (y < -0.2) {
        cuadrante = 'Acuoso Puro';
        descriptorSabor = 'Taza ligera, aguada, le falta presencia en boca.';
        diagnosticoConcentracion = 'Concentración muy baja.';
      }
    }

    // --- PASOS TÁCTICOS PRIORIZADOS ---
    const pasosTacticos: string[] = [];

    if (zonaIdeal) {
      pasosTacticos.push('¡No toques nada! Tu receta se encuentra en el rango de excelencia sensorial.');
      pasosTacticos.push('Registra esta receta en tu bitácora para replicar el mismo perfil con este café.');
    } else {
      // 1. Molienda (Extracción principal)
      if (deltaClicks < 0) {
        pasosTacticos.push(`Muele ${Math.abs(deltaClicks)} click${Math.abs(deltaClicks) > 1 ? 's' : ''} más FINO (de ${clicks} a ${clicksSugeridos}) para aumentar el área de contacto y extraer más dulzor.`);
      } else if (deltaClicks > 0) {
        pasosTacticos.push(`Muele ${deltaClicks} click${deltaClicks > 1 ? 's' : ''} más GRUESO (de ${clicks} a ${clicksSugeridos}) para acelerar el drenaje y evitar notas amargas secas.`);
      }

      // 2. Ratio (Concentración / Cuerpo)
      if (deltaRatio !== 0) {
        if (modoAjuste === 'agua') {
          if (deltaAgua > 0) {
            pasosTacticos.push(`Abre el ratio a 1:${ratioSugerido}: sube el agua en +${deltaAgua} ml (de ${agua} a ${aguaSugerida} ml) para aligerar la saturación.`);
          } else {
            pasosTacticos.push(`Cierra el ratio a 1:${ratioSugerido}: reduce el agua en ${deltaAgua} ml (de ${agua} a ${aguaSugerida} ml) para ganar cuerpo y textura.`);
          }
        } else {
          if (deltaDosis < 0) {
            pasosTacticos.push(`Abre el ratio a 1:${ratioSugerido}: reduce la dosis en ${Math.abs(deltaDosis)} g (de ${dosis} a ${dosisSugerida} g).`);
          } else {
            pasosTacticos.push(`Cierra el ratio a 1:${ratioSugerido}: sube la dosis en +${deltaDosis} g (de ${dosis} a ${dosisSugerida} g) para ganar cuerpo.`);
          }
        }
      }

      // 3. Temperatura y Flujo
      if (deltaTemperatura !== 0) {
        const accionTemp = deltaTemperatura > 0 ? `Sube la temperatura +${deltaTemperatura}°C` : `Baja la temperatura ${deltaTemperatura}°C`;
        pasosTacticos.push(`${accionTemp} (a ${temperaturaSugerida}°C) para modular la solubilidad.`);
      }
      if (deltaTiempo !== 0) {
        const signoTiempo = deltaTiempo > 0 ? `+${deltaTiempo}s` : `${deltaTiempo}s`;
        pasosTacticos.push(`Ajusta el tiempo de vertido objetivo en ${signoTiempo} para coordinar con la nueva molienda.`);
      }
    }

    let explicacionBarista = '';
    if (zonaIdeal) {
      explicacionBarista = 'Has alcanzado el punto de equilibrio donde los ácidos orgánicos brillantes están armonizados por azúcares caramelo, sin alcanzar los taninos astringentes finales.';
    } else if (x < -0.2) {
      explicacionBarista = 'Los primeros compuestos en disolverse son los ácidos y sales. Al no haber suficiente extracción (molienda gruesa, agua fría o paso rápido), no lograste extraer los azúcares que suavizan la taza.';
    } else if (x > 0.2) {
      explicacionBarista = 'Has sobrepasado el tiempo de contacto óptimo o la molienda es demasiado fina, disolviendo fenoles y compuestos celulósicos que generan sensación seca en el paladar.';
    } else if (y > 0.2) {
      explicacionBarista = 'La extracción en sabor está equilibrada, pero la cantidad de partículas disueltas respecto al agua total es muy alta, opacando las notas sutiles por exceso de fuerza.';
    } else {
      explicacionBarista = 'El balance de extracción es bueno, pero la bebida tiene demasiada agua para la cantidad de café usado, resultando en una taza aguada con poca textura.';
    }

    return {
      zonaIdeal,
      cuadrante,
      descriptorSabor,
      ratioActual,
      deltaRatio,
      ratioSugerido,
      dosisSugerida,
      deltaDosis,
      aguaSugerida,
      deltaAgua,
      deltaClicks,
      clicksSugeridos,
      deltaTemperatura,
      temperaturaSugerida,
      deltaTiempo,
      tiempoSugerido,
      diagnosticoExtraccion,
      diagnosticoConcentracion,
      pasosTacticos,
      explicacionBarista
    };
  }
}
