import { H as HttpClient } from './HttpClient_Dd_rjSA5.mjs';

class Store {
  id;
  nombre;
  url_web;
  plataforma;
  comuna;
  latitud;
  longitud;
  cantidad_productos;
  distancia_km;
  activa;
  constructor(props) {
    this.id = props.id;
    this.nombre = props.nombre;
    this.url_web = props.url_web;
    this.plataforma = props.plataforma;
    this.comuna = props.comuna;
    this.latitud = props.latitud;
    this.longitud = props.longitud;
    this.cantidad_productos = props.cantidad_productos || 0;
    this.distancia_km = props.distancia_km;
    this.activa = props.activa !== void 0 ? props.activa : true;
  }
}

class GetStoresUseCase {
  constructor(http = new HttpClient()) {
    this.http = http;
  }
  async execute(params = {}) {
    const queryParams = {
      page: params.page || 1,
      page_size: params.pageSize || 50,
      sort_by: params.sortBy || "product_count_desc",
      lat: params.lat,
      lon: params.lon
    };
    const response = await this.http.get("/api/v1/stores", {
      params: queryParams
    });
    return (response.items || []).map((s) => new Store(s));
  }
}

export { GetStoresUseCase as G };
