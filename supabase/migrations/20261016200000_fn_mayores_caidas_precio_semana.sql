-- Migration: 20261016200000_fn_mayores_caidas_precio_semana.sql
-- Descripción: Función y vista optimizada para consultar las mayores caídas de precio de la semana (ofertas verificadas)

CREATE OR REPLACE FUNCTION fn_obtener_mayores_caidas_semana(
    limite INT DEFAULT 10,
    dias INT DEFAULT 7
)
RETURNS TABLE (
    oferta_id INT,
    producto_id INT,
    nombre_producto VARCHAR,
    tienda VARCHAR,
    url_tienda VARCHAR,
    imagen_url TEXT,
    formato_gramos INT,
    precio_anterior INT,
    precio_actual INT,
    precio_por_kilo NUMERIC,
    monto_rebaja INT,
    porcentaje_descuento INT,
    link_detalle VARCHAR,
    fecha_cambio TIMESTAMP
) AS $$
WITH ventana_historial AS (
    SELECT
        hp.variante_id,
        hp.precio_clp,
        hp.precio_por_kilo,
        hp.fecha_registro,
        ROW_NUMBER() OVER (
            PARTITION BY hp.variante_id
            ORDER BY hp.fecha_registro ASC, hp.id ASC
        ) AS rn_primero,
        ROW_NUMBER() OVER (
            PARTITION BY hp.variante_id
            ORDER BY hp.fecha_registro DESC, hp.id DESC
        ) AS rn_ultimo
    FROM historial_precios hp
    WHERE hp.fecha_registro >= (NOW() - (dias || ' days')::INTERVAL)
),
primeros_precios AS (
    SELECT variante_id, precio_clp AS precio_inicio, fecha_registro AS fecha_inicio
    FROM ventana_historial
    WHERE rn_primero = 1
),
ultimos_precios AS (
    SELECT variante_id, precio_clp AS precio_fin, precio_por_kilo AS precio_kilo_fin, fecha_registro AS fecha_fin
    FROM ventana_historial
    WHERE rn_ultimo = 1
),
caidas_calculadas AS (
    SELECT
        v.id AS oferta_id,
        p.id AS producto_id,
        p.nombre::VARCHAR AS nombre_producto,
        t.nombre::VARCHAR AS tienda,
        COALESCE(t.sitio_oficial, t.url_web, t.url_base)::VARCHAR AS url_tienda,
        p.imagen AS imagen_url,
        v.formato_gramos,
        p_ini.precio_inicio AS precio_anterior,
        p_fin.precio_fin AS precio_actual,
        p_fin.precio_kilo_fin AS precio_por_kilo,
        (p_ini.precio_inicio - p_fin.precio_fin) AS monto_rebaja,
        ROUND(((p_ini.precio_inicio - p_fin.precio_fin)::NUMERIC / p_ini.precio_inicio::NUMERIC) * 100)::INT AS porcentaje_descuento,
        p.url_detalle::VARCHAR AS link_detalle,
        p_fin.fecha_fin AS fecha_cambio
    FROM variantes v
    INNER JOIN productos p ON p.id = v.producto_id AND p.activo = TRUE AND p.oculto_catalogo = FALSE
    INNER JOIN tiendas t ON t.id = p.tienda_id AND t.activo = TRUE
    INNER JOIN primeros_precios p_ini ON p_ini.variante_id = v.id
    INNER JOIN ultimos_precios p_fin ON p_fin.variante_id = v.id
    WHERE v.disponible = TRUE
      AND p_ini.precio_inicio IS NOT NULL
      AND p_fin.precio_fin < p_ini.precio_inicio
      AND (p_ini.precio_inicio - p_fin.precio_fin) > 0
)
SELECT
    c.oferta_id,
    c.producto_id,
    c.nombre_producto,
    c.tienda,
    c.url_tienda,
    c.imagen_url,
    c.formato_gramos,
    c.precio_anterior,
    c.precio_actual,
    c.precio_por_kilo,
    c.monto_rebaja,
    c.porcentaje_descuento,
    c.link_detalle,
    c.fecha_cambio
FROM caidas_calculadas c
ORDER BY c.porcentaje_descuento DESC, c.monto_rebaja DESC
LIMIT limite;
$$ LANGUAGE sql STABLE;

-- Vista rápida para consultas directas sin parámetros
CREATE OR REPLACE VIEW vista_mayores_caidas_semana AS
SELECT * FROM fn_obtener_mayores_caidas_semana(50, 7);
