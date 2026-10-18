export interface RecipeProps {
  id: string;
  cafe: string;
  metodo: string;
  gramos_cafe: number;
  gramos_agua: number;
  molienda?: string;
  tiempo?: string;
  calificacion: number;
  notas?: string;
  catacion_sca?: Record<string, number>;
  puntuacion_sca_total?: number;
  fecha: string;
  producto_id?: number | string;
  producto_url?: string;
  tienda?: string;
}

export class Recipe {
  readonly id: string;
  readonly cafe: string;
  readonly metodo: string;
  readonly gramos_cafe: number;
  readonly gramos_agua: number;
  readonly molienda?: string;
  readonly tiempo?: string;
  readonly calificacion: number;
  readonly notas?: string;
  readonly catacion_sca?: Record<string, number>;
  readonly puntuacion_sca_total?: number;
  readonly fecha: string;
  readonly producto_id?: number | string;
  readonly producto_url?: string;
  readonly tienda?: string;

  constructor(props: RecipeProps) {
    this.id = props.id || `rec-${Date.now()}`;
    this.cafe = props.cafe;
    this.metodo = props.metodo;
    this.gramos_cafe = Math.max(1, props.gramos_cafe);
    this.gramos_agua = Math.max(10, props.gramos_agua);
    this.molienda = props.molienda;
    this.tiempo = props.tiempo;
    this.calificacion = Math.min(5, Math.max(1, props.calificacion || 5));
    this.notas = props.notas;
    this.catacion_sca = props.catacion_sca;
    this.puntuacion_sca_total = props.puntuacion_sca_total;
    this.fecha = props.fecha || new Date().toISOString();
    this.producto_id = props.producto_id;
    this.producto_url = props.producto_url;
    this.tienda = props.tienda;
  }

  getRatio(): string {
    const ratio = (this.gramos_agua / this.gramos_cafe).toFixed(1);
    return `1:${ratio}`;
  }
}

