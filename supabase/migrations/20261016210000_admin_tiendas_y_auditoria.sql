-- Migration: 20261016210000_admin_tiendas_y_auditoria.sql
-- Descripción: Módulo de administración multi-inquilino para administradores de tiendas, auditoría y RLS

-- 1. Tabla de vínculo Usuario - Tienda
CREATE TABLE IF NOT EXISTS usuarios_tienda (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL,
    tienda_id INT NOT NULL REFERENCES tiendas(id) ON DELETE CASCADE,
    rol VARCHAR(50) DEFAULT 'STORE_ADMIN',
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(usuario_id, tienda_id)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_tienda_usuario_id ON usuarios_tienda(usuario_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_tienda_tienda_id ON usuarios_tienda(tienda_id);

-- 2. Tabla de Auditoría y Trazabilidad (Audit Logs)
CREATE TABLE IF NOT EXISTS auditoria_acciones_tienda (
    id SERIAL PRIMARY KEY,
    tienda_id INT NOT NULL REFERENCES tiendas(id) ON DELETE CASCADE,
    usuario_id UUID NOT NULL,
    accion VARCHAR(50) NOT NULL, -- 'CREAR_PRODUCTO', 'EDITAR_PRODUCTO', 'INICIAR_SYNC', etc.
    entidad VARCHAR(50) NOT NULL, -- 'ofertas_tienda', 'productos', 'tiendas'
    entidad_id INT,
    valores_previos JSONB,
    valores_nuevos JSONB,
    ip_origen VARCHAR(45),
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auditoria_tienda_id ON auditoria_acciones_tienda(tienda_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria_acciones_tienda(fecha_registro DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria_acciones_tienda(usuario_id);

-- 3. Políticas de Seguridad a Nivel de Fila (RLS) en Supabase/PostgreSQL
ALTER TABLE usuarios_tienda ENABLE ROW LEVEL SECURITY;
ALTER TABLE auditoria_acciones_tienda ENABLE ROW LEVEL SECURITY;
ALTER TABLE ofertas_tienda ENABLE ROW LEVEL SECURITY;
ALTER TABLE sincronizaciones_log ENABLE ROW LEVEL SECURITY;

-- Política usuarios_tienda: el usuario solo puede ver sus propias asignaciones
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'usuarios_tienda' AND policyname = 'policy_usuarios_tienda_read'
    ) THEN
        CREATE POLICY policy_usuarios_tienda_read ON usuarios_tienda
            FOR SELECT
            USING (auth.uid() = usuario_id);
    END IF;
END $$;

-- Política auditoria_acciones_tienda: administradores de tienda solo ven auditoría de su tienda
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'auditoria_acciones_tienda' AND policyname = 'policy_auditoria_store_admin'
    ) THEN
        CREATE POLICY policy_auditoria_store_admin ON auditoria_acciones_tienda
            FOR ALL
            USING (
                tienda_id IN (
                    SELECT ut.tienda_id FROM usuarios_tienda ut WHERE ut.usuario_id = auth.uid()
                )
            );
    END IF;
END $$;

-- Política ofertas_tienda: lectura pública, mutaciones acotadas a tienda asignada
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'ofertas_tienda' AND policyname = 'policy_ofertas_tienda_select_public'
    ) THEN
        CREATE POLICY policy_ofertas_tienda_select_public ON ofertas_tienda
            FOR SELECT
            USING (TRUE);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'ofertas_tienda' AND policyname = 'policy_ofertas_tienda_store_admin_mutation'
    ) THEN
        CREATE POLICY policy_ofertas_tienda_store_admin_mutation ON ofertas_tienda
            FOR ALL
            USING (
                tienda_id IN (
                    SELECT ut.tienda_id FROM usuarios_tienda ut WHERE ut.usuario_id = auth.uid()
                )
            );
    END IF;
END $$;
