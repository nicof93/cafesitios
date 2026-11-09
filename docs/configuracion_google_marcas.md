# Guía Operativa: Configuración de Google Tag Manager (GTM), Google Analytics 4 (GA4) y Search Console para Marcas en Cafesitios

Esta guía técnica y operativa documenta los pasos exactos para el operador/analista digital con el fin de activar, verificar y explotar la telemetría e-commerce y el ecosistema de marcas de **Cafesitios** (`https://cafesitios.cl`).

---

## 1. Google Tag Manager (GTM)

### 1.1 Variables de Capa de Datos (Data Layer Variables - DLV)
Ingresar a **Variables** > **Variables definidas por el usuario** > **Nueva** > Tipo: **Variable de capa de datos** (Versión de capa de datos: **Versión 2**). Crear las siguientes variables:

| Nombre de Variable en GTM | Nombre de la variable de capa de datos | Descripción |
| :--- | :--- | :--- |
| `dlv - tienda_destino` | `tienda_destino` | Nombre de la tostaduría externa receptora de la visita |
| `dlv - nombre_cafe` | `nombre_cafe` | Nombre del café específico clickeado |
| `dlv - precio_por_kilo` | `precio_por_kilo` | Valor normalizado en CLP por kilogramo |
| `dlv - es_precio_estimado` | `es_precio_estimado` | Booleano que indica si el gramaje fue inferido (250g) |
| `dlv - tienda_actual` | `tienda_actual` | Marca del producto base en comparador |
| `dlv - tienda_comparada` | `tienda_comparada` | Marca del segundo producto contrastado |
| `dlv - ecommerce.items` | `ecommerce.items` | Array canónico GA4 de productos interactuados |
| `dlv - item_list_id` | `item_list_id` | Identificador de lista (`directorio_marcas`) |

---

### 1.2 Activadores de Evento Personalizado (Triggers)
Ingresar a **Activadores** > **Nuevo** > Tipo: **Evento personalizado**.

1. **Activador: `CE - clic_tienda_externa`**
   * **Nombre del evento:** `clic_tienda_externa`
   * **Este activador se activa en:** *Algunos eventos personalizados*
   * **Condición de seguridad:** `Page Hostname` contiene `cafesitios.cl`

2. **Activador: `CE - seleccionar_marca`**
   * **Nombre del evento:** `seleccionar_marca`
   * **Este activador se activa en:** *Algunos eventos personalizados*
   * **Condición de seguridad:** `Page Hostname` contiene `cafesitios.cl`

3. **Activador: `CE - view_item_list (Marcas)`**
   * **Nombre del evento:** `view_item_list`
   * **Este activador se activa en:** `dlv - item_list_id` es igual a `directorio_marcas`
   * **Condición de seguridad:** `Page Hostname` contiene `cafesitios.cl`

4. **Activador: `CE - comparar_con_tienda`**
   * **Nombre del evento:** `comparar_con_tienda`
   * **Este activador se activa en:** *Algunos eventos personalizados*
   * **Condición de seguridad:** `Page Hostname` contiene `cafesitios.cl`

---

### 1.3 Etiquetas de Evento GA4 (Tags)
Ingresar a **Etiquetas** > **Nueva** > Tipo: **Google Analytics: evento de GA4**.

1. **Etiqueta: `GA4 - Evento - Clic Tienda Externa (Conversión Primaria)`**
   * **Etiqueta de configuración:** Seleccionar la etiqueta de configuración base de GA4 (`G-XXXXXXXXXX`).
   * **Nombre del evento:** `clic_tienda_externa`
   * **Parámetros del evento:**
     * `tienda_destino` -> `{{dlv - tienda_destino}}`
     * `nombre_cafe` -> `{{dlv - nombre_cafe}}`
     * `precio_por_kilo` -> `{{dlv - precio_por_kilo}}`
     * `es_precio_estimado` -> `{{dlv - es_precio_estimado}}`
   * **Más opciones de configuración > Enviar datos de comercio electrónico:** Activar casilla ☑️ (*Fuente de datos: Capa de datos*).
   * **Activador de disparo:** `CE - clic_tienda_externa`.

2. **Etiqueta: `GA4 - Evento - Seleccionar Marca Directorio`**
   * **Nombre del evento:** `seleccionar_marca`
   * **Parámetros del evento:**
     * `tienda_nombre` -> `{{dlv - tienda_destino}}`
   * **Activador de disparo:** `CE - seleccionar_marca`.

3. **Etiqueta: `GA4 - Evento - Comparar Entre Tiendas`**
   * **Nombre del evento:** `comparar_con_tienda`
   * **Parámetros del evento:**
     * `tienda_actual` -> `{{dlv - tienda_actual}}`
     * `tienda_comparada` -> `{{dlv - tienda_comparada}}`
   * **Activador de disparo:** `CE - comparar_con_tienda`.

---

## 2. Google Analytics 4 (GA4)

### 2.1 Definiciones Personalizadas (Custom Dimensions & Metrics)
En GA4, dirigirse a **Administrador** > **Visualización de datos** > **Definiciones personalizadas**.

#### Dimensiones personalizadas (Ámbito del evento):
| Nombre de la dimensión | Ámbito | Parámetro de evento | Descripción |
| :--- | :--- | :--- | :--- |
| **Tienda Destino** | Evento | `tienda_destino` | Tostaduría que recibe la intención de compra |
| **Nombre de Café** | Evento | `nombre_cafe` | Nombre del producto de especialidad |
| **Tienda Comparada** | Evento | `tienda_comparada` | Marca contrincante en side-by-side |
| **Es Precio Estimado** | Evento | `es_precio_estimado` | Indicador si el formato fue inferido |

#### Métricas personalizadas:
| Nombre de la métrica | Ámbito | Parámetro de evento | Unidad de medida |
| :--- | :--- | :--- | :--- |
| **Precio Por Kilo** | Evento | `precio_por_kilo` | Moneda (CLP) |

---

### 2.2 Marcado de Evento Clave (Key Event / Conversión)
1. En GA4, dirigirse a **Administrador** > **Visualización de datos** > **Eventos**.
2. Buscar en la lista el evento `clic_tienda_externa` (o crearlo manualmente antes de que reciba tráfico).
3. Activar el interruptor **Marcar como evento clave** (*Mark as key event*).
4. **Propósito de negocio:** Medir el Retorno de Demanda Cualificada (Outbound ROI) hacia las tostadurías chilenas aliadas.

---

### 2.3 Reporte de Exploración B2B para Marcas (Demanda Derivada)
Para justificar el valor de Cafesitios frente a las tostadurías asociadas:

1. Dirigirse a **Explorar** > **Crear una nueva exploración en blanco**.
2. **Nombre:** `Reporte Mensual B2B - Demanda Derivada a Tostadurías`.
3. **Técnica:** *Formato libre*.
4. **Dimensiones:**
   * `tienda_destino`
   * `nombre_cafe`
5. **Métricas:**
   * `Recuento de eventos` (filtrado por nombre de evento = `clic_tienda_externa`)
   * `Usuarios totales`
   * `Precio Por Kilo` (Promedio)
6. **Configuración de Tabla:**
   * **Filas:** `tienda_destino` (con anidación secundaria opcional de `nombre_cafe`).
   * **Valores:** Recuento de eventos, Usuarios totales, Promedio $/kg.
7. **Uso Operativo:** Exportar mensualmente en formato CSV / Google Sheets para enviar informes de tracción a cada tostaduría socia (ej. *"Singular Coffee: Recibiste 430 intenciones de compra cualificadas este mes"*).

---

## 3. Google Search Console & SEO Técnico

### 3.1 Verificación de Propiedad
1. Acceder a **Google Search Console** con la cuenta administradora de Cafesitios.
2. Añadir la propiedad de dominio: `https://cafesitios.cl`.
3. El registro TXT de DNS en Cloudflare/proveedor de dominio debe contener la llave `google-site-verification`.

### 3.2 Envío del Sitemap Dinámico
1. En el menú lateral, seleccionar **Sitemaps**.
2. Añadir la URL relativa: `sitemap.xml` (Ruta completa: `https://cafesitios.cl/sitemap.xml`).
3. El sitemap dinámico generado por Astro incluye:
   * URL raíz `/` (Prioridad: `1.0`, Frecuencia: `daily`)
   * Catálogo `/catalogo` (Prioridad: `0.9`, Frecuencia: `daily`)
   * Directorio Central `/tiendas` (Prioridad: `0.8`, Frecuencia: `weekly`)
   * Páginas canónicas individuales de cada marca `/tiendas/[slug]` (Prioridad: `0.8`, Frecuencia: `weekly`, con imagen de logo oficial)
   * Fichas de productos `/producto/[id]` (Prioridad: `0.8`, Frecuencia: `weekly`)
   * Novedades `/novedades` y Recetas `/recetas` (según Feature Flags activos)

---

## 4. Checklist de Validación en Navegador

Para verificar en tiempo real antes de publicar en GTM:

1. Abrir `https://cafesitios.cl/tiendas` con la extensión **Omnibug** o consola de desarrollador (`F12`).
2. Comprobar que en consola aparezca:
   ```javascript
   window.dataLayer.find(e => e.event === 'view_item_list');
   ```
3. Hacer clic en cualquier botón **"Visitar Tienda Oficial"** o **"Comprar ↗"**:
   * Verificar que se abra en nueva pestaña.
   * Verificar en la barra de direcciones que la URL contenga:
     `?utm_source=cafesitios&utm_medium=referral&utm_campaign=...`
   * Verificar en `window.dataLayer` el push de `ecommerce: null` seguido inmediatamente por el evento `clic_tienda_externa` con `tienda_destino`, `precio_clp`, `precio_por_kilo` e `items`.
