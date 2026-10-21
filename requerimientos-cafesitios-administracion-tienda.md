# Especificación Funcional: Catálogo Público y Panel de Administración de Tiendas (Cafe-sitios)

Documento de especificación funcional y justificación de negocio para el backlog de desarrollo en **Antigravity**. Define la interacción, el valor aportado y el comportamiento esperado para la plataforma pública y el módulo administrativo multi-inquilino (*multi-tenant*).

---

## Parte 1: Catálogo Público y Experiencia de Usuario

### 1.1. Búsqueda Global y Filtrado Lateral Reactivo (CU-01)

* **Descripción Funcional:**
* Barra de búsqueda con tolerancia a variaciones léxicas (ej. *bourbon/borbón*, *gesha/geisha*) y búsqueda por origen, proceso, notas o tostaduría.


* Panel lateral izquierdo (*Sidebar*) que concentra filtros mediante casillas de verificación (*checkboxes*) simples: tostadurías con conteo de cafés disponibles, origen geográfico, perfil de proceso (Lavado, Natural, Honey, Anaeróbico) y rango de precio por kilo ($/kg).


* La grilla de productos reacciona en tiempo real a cada cambio de filtro sin requerir botones manuales de confirmación.



* **Justificación de Negocio:**
Elimina la sobrecarga cognitiva en el área superior del sitio (*above the fold*). Permite al usuario encontrar granos específicos en segundos sin recargas de página completas.



### 1.2. Normalización y Visualización de Precio Estandarizado ($/kg y $/100g) (CU-02)

* **Descripción Funcional:**
* Cálculo automatizado que divide el precio de la bolsa por su peso neto en gramos, proyectándolo a valor unitario ($/kg y complemento $/100g para formatos pequeños de cata).


* Insignia destacada en color de contraste en cada tarjeta de producto y en la ficha de detalle.


* Regla de negocio estricta: las variantes de molienda (grano entero, espresso, prensa francesa, filtro) no alteran el gramaje ni el precio por kilo, agrupándose bajo la misma entidad de peso.




* **Justificación de Negocio:**
Es la propuesta de valor principal de Cafesitios. Permite comparar de forma transparente una bolsa de 200g, 250g o 1kg entre diferentes tostadurías chilenas sin sesgos por tamaño de empaque.



### 1.3. Matriz Comparativa Directa Cara a Cara (Side-by-Side) (CU-03)

* **Descripción Funcional:**
* Control interactivo `[+ Comparar]` en cada tarjeta de café y botón `[Comparar con...]` en la ficha de detalle.


* Barra flotante inferior que indica el estado (`1 de 2 cafés seleccionados`, escalable hasta 4 en desktop).


* Modal/vista en matriz de columnas que contrasta cara a cara: formatos disponibles, precio por bolsa, $/kg resaltando la opción más económica, notas de cata, proceso, tostaduría y botón de derivación a tienda externa.




* **Justificación de Negocio:**
Resuelve la indecisión del comprador entre dos o más cafés de similar perfil organoléptico o precio sin obligarlo a alternar entre múltiples pestañas del navegador.



### 1.4. Comparador de Disponibilidad de Lote Compartido (CU-04)

* **Descripción Funcional:**
* En la vista de detalle de un grano identificado como lote botánico común, despliega un bloque con las distintas tostadurías o cafeterías que comercializan el mismo café.


* Muestra tabla comparativa de stock, precio por formato y enlace directo de compra a cada comercio.




* **Justificación de Negocio:**
Transparencia de mercado. Si un importador distribuyó el mismo lote a tres tostadurías locales, el consumidor puede elegir a quién comprar según cercanía física o conveniencia de precio.



### 1.5. Ordenamiento de Tiendas por Proximidad Física (CU-05)

* **Descripción Funcional:**
* Cálculo de distancia lineal (fórmula de Haversine) entre la ubicación del usuario (GPS o selección manual de comuna) y las sucursales físicas registradas de cada tostaduría.


* Ordena el listado de cafeterías/tiendas de menor a mayor distancia en kilómetros con degradación elegante a orden alfabético si no se otorgan permisos de ubicación.




* **Justificación de Negocio:**
Fomenta el retiro en local (*pick-up*) y el consumo presencial en tostadurías de barrio, ahorrando costos y tiempos de despacho al cliente final.



### 1.6. Histórico y Gráfico de Evolución de Precios (CU-06)

* **Descripción Funcional:**
* En la ficha de producto (`/producto/[id]`), dibuja una curva temporal con lecturas periódicas de precio histórico.


* Destaca métricas resumen: Precio Actual, Mínimo Histórico y Promedio.




* **Justificación de Negocio:**
Genera credibilidad. El comprador comprueba si una rebaja corresponde a una oportunidad real o si el valor se ha mantenido estable en el tiempo.



### 1.7. Quiz Recomendador por Perfil de Taza (CU-07)

* **Descripción Funcional:**
* Asistente interactivo de 3 pasos: Método de extracción (Espresso, Filtrados, Prensa, AeroPress), Perfil organoléptico (Frutal/Cítrico, Chocolate/Frutos secos, Floral) y Nivel de tueste.


* Algoritmo determinista de ponderación léxica que evalúa notas SCA y método, sugiriendo las 3 opciones óptimas con stock vigente ordenadas por mejor $/kg.


* Enlace directo para guardar la receta base sugerida en la bitácora.




* **Justificación de Negocio:**
Reduce la barrera de entrada para principiantes que no dominan orígenes o procesos, guiándolos directo a una compra satisfactoria sin requerir modelos LLM costosos en runtime.



### 1.8. Bitácora de Calibración de Recetas (Dial-in) (CU-08)

* **Descripción Funcional:**
* Herramienta orientada al barista casero para registrar variables de extracción: dosis (g), agua (ml), ratio automático (ej. 1:16), molino, clics de molienda, temperatura (°C), tiempo y nota de cata (1-10).


* Persistencia *Local-First* en el navegador del usuario (`localStorage`) vinculable opcionalmente a un café del catálogo.




* **Justificación de Negocio:**
Convierte a Cafesitios de un comparador transaccional esporádico en una herramienta de uso cotidiano cada mañana, generando retención recurrente y lealtad comunitaria.



### 1.9. Detección Automática y Filtro de Ofertas Verificadas (CU-09)

* **Descripción Funcional:**
* Detección en la ingesta del precio de comparación (`compare_at_price` o precio tachado) frente al precio de venta real.


* Cálculo del porcentaje de descuento y despliegue de insignia visible `-X% OFF` en tarjeta y filtro dedicado en el Sidebar.




* **Justificación de Negocio:**
Captura las compras por oportunidad económica inmediata, validando que el descuento sea real respecto al historial del producto.



### 1.10. Favoritos con Detección de Baja de Precio y Retorno de Stock (CU-10 / CU-12)

* **Descripción Funcional:**
* Marcado con icono corazón (♡/♥) sin registro obligatorio de cuentas (*Local-First* sobre `localStorage`).


* Guarda una instantánea (*snapshot*) con precio y disponibilidad. Al contrastar con datos frescos del catálogo, emite alertas visuales: *"Bajó de precio"* o *"Volvió a estar disponible"*.


* Prioriza automáticamente los productos marcados como favoritos al tope de la grilla del catálogo antes de aplicar otros ordenamientos.




* **Justificación de Negocio:**
Fidelización sin fricción. Notifica al usuario en el momento exacto en que conviene comprar su grano preferido sin invadir su privacidad ni pedirle contraseñas.



### 1.11. Historial de Cafés Vistos y Comparaciones Recientes (CU-10)

* **Descripción Funcional:**
* Cola circular en cliente (FIFO, máx. 10 cafés vistos y máx. 5 comparativas) guardada en `localStorage`.


* Despliega un carrusel compacto inferior que permite retomar vistas o reabrir matrices comparativas previas con un solo clic.




* **Justificación de Negocio:**
Facilita la navegación del comprador indeciso que exploró múltiples tostadurías y desea volver a un café visto minutos antes sin rehacer búsquedas manuales.



### 1.12. Filtros Especializados de Nicho: Nivel de Tueste, Métodos, Descafeinado y Packs

* **Descripción Funcional:**
* Filtros específicos en Sidebar: Tueste (Claro, Medio, Oscuro), Destino sugerido (Espresso vs. Filtrados), Sellos de café descafeinado con mención de proceso (*Swiss Water, Sugar Cane*) y categoría para *Packs de Degustación / Sample Boxes*.


* Normalización del cálculo $/kg o $/100g sumando el gramaje total del pack de muestras.




* **Justificación de Negocio:**
Atiende a nichos de alta conversión (consumidores de *decaf*, compradores de sets de regalo y usuarios de máquinas de espresso que descartan tuestes claros).



### 1.13. Ficha de Detalle con Barra Flotante de Compra Directa (Sticky Bottom Bar)

* **Descripción Funcional:**
* En la vista de producto, una barra flotante fija al tercio inferior acompaña el scroll del usuario.


* Contiene miniatura del producto, nombre, badges de proceso y botón principal destacado: *"Ir a comprar en [Nombre Tienda] ↗"*.




* **Justificación de Negocio:**
Maximiza la tasa de conversión y clics salientes (*outbound clicks*), evitando que el usuario deba hacer scroll hacia arriba para encontrar el enlace de compra tras analizar tablas y notas técnicas.



---

## Parte 2: Plataforma de Administración de Cada Tienda

### 2.1. Acceso Protegido y Aislamiento Multitienda (Multi-Tenant RBAC)

* **Descripción Funcional:**
* Portal administrativo alojado en subdominio dedicado (ej. `admin.cafesitios.cl`) con autenticación OAuth/OIDC (Google/GitHub) o credenciales seguras.


* Control de acceso basado en roles (`STORE_ADMIN`). Políticas RLS en PostgreSQL y dependencias en FastAPI que aseguran que ningún encargado pueda leer o modificar datos ajenos a su `tienda_id`.


* Defensas anti-abuso: *Rate limiting* estricto y protección anti-fuerza bruta en login.




* **Justificación de Negocio:**
Seguridad y confidencialidad entre tostadurías competidoras. Otorga un entorno profesional y aislado a cada marca.



### 2.2. Panel de Telemetría Comercial e Intención de Compra

* **Descripción Funcional:**
* Cuadro de mandos con métricas de demanda en tiempo real: total de clics derivados hacia su e-commerce (`click_outbound_store`), Top 3 de cafés con mayor interés, cantidad de usuarios con sus productos en listas de favoritos y frecuencia de aparición en la matriz comparativa.




* **Justificación de Negocio:**
Es la demostración de valor cuantitativa de Cafesitios hacia la tostaduría. El comercio constata con datos duros el volumen de clientes potenciales que la plataforma le deriva mes a mes.



### 2.3. Disparador de Sincronización Manual Voluntaria Bajo Demanda

* **Descripción Funcional:**
* Botón en panel `[ 🔄 Sincronizar catálogo ahora ]` que ejecuta el driver de scraping respectivo en segundo plano.


* Retroalimentación visual de estado (en progreso / finalizado) y mecanismo de enfriamiento (*cooldown*) estricto de 30 minutos por tienda para proteger la infraestructura.




* **Justificación de Negocio:**
Autonomía para el tostador. Si lanza una edición limitada o actualiza precios de su catálogo, puede refrescar Cafesitios al instante sin esperar el barrido nocturno programado.



### 2.4. Gestión de Múltiples URLs de Colección por Tienda

* **Descripción Funcional:**
* Módulo para registrar y administrar múltiples enlaces de colecciones bajo una misma tostaduría (ej. `/collections/cafe-250g`, `/collections/cafe-de-kg`, `/collections/linea-insignia`).


* Evita la duplicidad de tiendas en base de datos asociando todas las ofertas a la misma entidad principal.




* **Justificación de Negocio:**
Permite una ingesta completa y fidedigna del catálogo real de tiendas que dividen sus productos por formato o línea de tueste sin fragmentar su marca.



### 2.5. Asistente Probador de Nuevas URLs de Colección

* **Descripción Funcional:**
* Campo interactivo para probar nuevas rutas del e-commerce. El backend ejecuta un ensayo en seco (*dry-run*) con los drivers (Shopify, WooCommerce, PrestaShop, Jumpseller, Odoo, SumUp) y previsualiza los productos detectados antes de confirmarla.




* **Justificación de Negocio:**
Autoservicio total. Si la tostaduría rediseña su web o crea una categoría temporal, puede darla de alta sin intervención técnica del equipo de Cafesitios.



### 2.6. Curación Rápida de Catálogo y Flags de Visibilidad (Override)

* **Descripción Funcional:**
* Tabla con el inventario extraído. Permite alternar la visibilidad de un café (`Toggle On/Off`) para apagarlo temporalmente si se agotó en bodega física pero el e-commerce no lo actualiza.
* Corrección manual de gramajes detectados erróneamente (recalculando el $/kg) y asignación de notas SCA para optimizar su aparición en el Quiz de recomendación.




* **Justificación de Negocio:**
Control y precisión de marca. La tostaduría subsana discrepancias del scraping en segundos sin alterar el código de su tienda original.



### 2.7. Bandeja de Inconsistencias de Scraping

* **Descripción Funcional:**
* Alertas preventivas que aíslan automáticamente productos leídos con precio $0 CLP, formatos de peso ambiguos o artículos no cafeteros (poleras, tazas, métodos colados en la categoría).


* Permite al encargado descartar o corregir la alerta con un clic.




* **Justificación de Negocio:**
Garantiza la higiene de datos del catálogo público, protegiendo la imagen de seriedad tanto de la tostaduría como de Cafesitios.



### 2.8. Perfil de Marca y Sucursales Físicas (Geolocalización)

* **Descripción Funcional:**
* Formulario de configuración institucional: carga de logotipo, descripción/especialidad de la tostaduría, enlaces a redes sociales, dominio oficial normalizado (`[https://mitienda.cl](https://mitienda.cl)`).


* Registro de cafeterías y sucursales físicas con dirección, comuna y resolución de coordenadas geográficas (latitud/longitud).




* **Justificación de Negocio:**
Habilita la presencia de la tienda en el ordenamiento por cercanía geográfica (CU-05) y potencia el reconocimiento visual de marca en todo el portal.



### 2.9. Configuración de Políticas de Despacho y Retiro en Local

* **Descripción Funcional:**
* Configuración de retiro gratuito en cafetería física y umbral de compra para despacho gratis (ej. *"Envío gratis en RM sobre $30.000"*).
* Estas condiciones alimentan badges informativos destacados en las tarjetas de sus productos en el catálogo público.




* **Justificación de Negocio:**
Aumenta la tasa de clics y compra efectiva. Elimina el abandono de carrito generado por costos de despacho inesperados al llegar a la tienda externa.

### 2.10. Calendario y Políticas de Tueste

* **Descripción Funcional:**
* Registro de días fijos de tueste semanal (ej. *"Tostamos martes y jueves"*) o fecha del lote activo más reciente.
* Habilita la etiqueta destacada *"Recién tostado"* en la plataforma.


* **Justificación de Negocio:**
Diferencia al tostador artesanal de marcas industriales masivas, atrayendo a los clientes de especialidad más exigentes que buscan máxima frescura.



### 2.11. Generador y Auditor de Atribución Comercial (UTM Builder)

* **Descripción Funcional:**
* Visualización y parametrización de etiquetas UTM añadidas a los enlaces salientes (`?utm_source=cafesitios&utm_medium=referral&utm_campaign=...`).




* **Justificación de Negocio:**
Transparencia analítica. Facilita que el encargado audite directamente en su propio Google Analytics o panel de Shopify el volumen exacto de pedidos y dinero facturado gracias al tráfico derivado de Cafesitios.



### 2.12. Benchmark Privado de Mercado y Posicionamiento de Precios

* **Descripción Funcional:**
* Panel analítico que contrasta el $/kg de los cafés de la tostaduría frente a las medianas y promedios del mercado nacional para categorías similares (mismo origen geográfico, proceso o formato de bolsa).




* **Justificación de Negocio:**
Inteligencia de negocios de alto valor. Ayuda a los tostadores a calibrar sus listas de precios de forma competitiva basándose en datos reales del ecosistema nacional.

### 2.13. Registro Inmutable de Auditoría Interna (Audit Log)

* **Descripción Funcional:**
* Bitácora cronológica inmutable (`auditoria_acciones_tienda`) que registra: usuario, acción ejecutada (creación, edición, toggle de visibilidad, sync forzada), diff de valores previos y nuevos (JSONB), IP y marca de tiempo.




* **Justificación de Negocio:**
Seguridad operativa y trazabilidad cuando una tostaduría cuenta con múltiples colaboradores o baristas gestionando su cuenta.



### 2.14. Inteligencia de Demanda No Satisfecha y Búsquedas sin Stock

* **Descripción Funcional:**
* Módulo que expone reportes agregados y anónimos de los términos de búsqueda o perfiles de sabor que los usuarios solicitaron en la plataforma pero que no contaban con stock disponible en el mercado.




* **Justificación de Negocio:**
Orienta las decisiones de compra de café verde e importación de la tostaduría hacia los orígenes y procesos con demanda real insatisfecha.



### 2.15. Widget Oficial Embebible "Verificado en Cafesitios"

* **Descripción Funcional:**
* Generador de snippet HTML/JS para que la tostaduría inserte en el pie de página de su propia web un sello dinámico de tienda verificada y transparencia de precio por kilo.




* **Justificación de Negocio:**
Aporta prestigio y confianza al comercio ante sus clientes, a la vez que genera una red de enlaces entrantes (*backlinks*) de alta autoridad hacia Cafesitios, fortaleciendo el posicionamiento orgánico en motores de búsqueda (SEO).