export interface StoreProps {
  id: number;
  nombre: string;
  url_web?: string;
  plataforma?: string;
  comuna?: string;
  latitud?: number;
  longitud?: number;
  cantidad_productos: number;
  distancia_km?: number;
  activa?: boolean;
}

export class Store {
  readonly id: number;
  readonly nombre: string;
  readonly url_web?: string;
  readonly plataforma?: string;
  readonly comuna?: string;
  readonly latitud?: number;
  readonly longitud?: number;
  readonly cantidad_productos: number;
  readonly distancia_km?: number;
  readonly activa: boolean;

  constructor(props: StoreProps) {
    this.id = props.id;
    this.nombre = props.nombre;
    this.url_web = props.url_web;
    this.plataforma = props.plataforma;
    this.comuna = props.comuna;
    this.latitud = props.latitud;
    this.longitud = props.longitud;
    this.cantidad_productos = props.cantidad_productos || 0;
    this.distancia_km = props.distancia_km;
    this.activa = props.activa !== undefined ? props.activa : true;
  }
}

