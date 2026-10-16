/**
 * Diccionario de Telemetría (Data Layer GTM & GA4) - Cafesitios MVP
 * Sección 7 de Especificación Técnica
 */
(function configureAnalytics() {
    const config = window.APP_CONFIG || {};
    const googleTagManagerId = config.googleTagManagerId || "";
    const googleAnalyticsId = config.googleAnalyticsId || "";

    window.dataLayer = window.dataLayer || [];

    if (googleTagManagerId) {
        window.dataLayer.push({
            "gtm.start": new Date().getTime(),
            event: "gtm.js"
        });

        const firstScript = document.getElementsByTagName("script")[0];
        const tagManagerScript = document.createElement("script");
        tagManagerScript.async = true;
        tagManagerScript.src =
            `https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(googleTagManagerId)}`;
        firstScript.parentNode.insertBefore(tagManagerScript, firstScript);
    }

    if (googleAnalyticsId) {
        window.gtag = function gtag() {
            window.dataLayer.push(arguments);
        };

        const analyticsScript = document.createElement("script");
        analyticsScript.async = true;
        analyticsScript.src =
            `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(googleAnalyticsId)}`;
        document.head.appendChild(analyticsScript);

        window.gtag("js", new Date());
        window.gtag("config", googleAnalyticsId, { send_page_view: true });
    }

    // Helper centralizado para emitir eventos dataLayer y registrar en backend
    window.CafesitiosAnalytics = {
        pushEvent: function (eventName, payload) {
            window.dataLayer.push({
                event: eventName,
                ...payload,
                timestamp: new Date().toISOString()
            });
        },

        // 1. search
        trackSearch: function (searchTerm, resultadosTotales) {
            this.pushEvent("search", {
                search_term: searchTerm,
                resultados_totales: resultadosTotales
            });
        },

        // 2. aplicar_filtro
        trackApplyFilter: function (tipoFiltro, valorFiltro) {
            this.pushEvent("aplicar_filtro", {
                tipo_filtro: tipoFiltro,
                valor_filtro: valorFiltro
            });
        },

        // 3. ordenar_catalogo
        trackOrderCatalog: function (criterioOrden) {
            this.pushEvent("ordenar_catalogo", {
                criterio_orden: criterioOrden
            });
        },

        // 4. select_item
        trackSelectItem: function (tiendaNombre, nombreCafe, precioPorKilo, esPrecioEstimado) {
            this.pushEvent("select_item", {
                tienda_nombre: tiendaNombre,
                nombre_cafe: nombreCafe,
                precio_por_kilo: precioPorKilo,
                es_precio_estimado: Boolean(esPrecioEstimado)
            });
        },

        // 5. comparar_productos
        trackCompareProducts: function (cafeAId, cafeBId) {
            this.pushEvent("comparar_productos", {
                cafe_a_id: cafeAId,
                cafe_b_id: cafeBId
            });
        },

        // 6. comparar_con_tienda
        trackCompareWithStore: function (cafeId, tiendaActual, tiendaComparada, diferenciaPrecioClp) {
            this.pushEvent("comparar_con_tienda", {
                cafe_id: cafeId,
                tienda_actual: tiendaActual,
                tienda_comparada: tiendaComparada,
                diferencia_precio_clp: diferenciaPrecioClp
            });
        },

        // 7. clic_tienda_externa (Outbound click)
        trackOutboundClick: function (tiendaDestino, nombreCafe, formatoGramos, precioClp, precioPorKilo, productoId, varianteId) {
            this.pushEvent("clic_tienda_externa", {
                tienda_destino: tiendaDestino,
                nombre_cafe: nombreCafe,
                formato_gramos: formatoGramos,
                precio_clp: precioClp,
                precio_por_kilo: precioPorKilo
            });

            // Registrar en backend para métricas de plataforma
            const apiUrl = (window.APP_CONFIG && window.APP_CONFIG.apiBaseUrl !== undefined)
                ? window.APP_CONFIG.apiBaseUrl
                : "";
            try {
                fetch(`${apiUrl}/api/v1/telemetry/event`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        tipo_evento: "clic_tienda_externa",
                        producto_id: productoId || null,
                        variante_id: varianteId || null,
                        metadata_evento: {
                            tienda_destino: tiendaDestino,
                            nombre_cafe: nombreCafe,
                            formato_gramos: formatoGramos,
                            precio_clp: precioClp,
                            precio_por_kilo: precioPorKilo
                        }
                    })
                }).catch(() => {});
            } catch (e) {}
        },

        // 8. completar_quiz_recomendador
        trackCompleteQuiz: function (metodoExtraccion, perfilSabor, nivelTueste) {
            this.pushEvent("completar_quiz_recomendador", {
                metodo_extraccion: metodoExtraccion,
                perfil_sabor: perfilSabor,
                nivel_tueste: nivelTueste
            });
        },

        // 9. guardar_receta
        trackSaveRecipe: function (metodoPreparacion, molinoUsado, calificacion) {
            this.pushEvent("guardar_receta", {
                metodo_preparacion: metodoPreparacion,
                molino_usado: molinoUsado,
                calificacion: calificacion
            });
        },

        // 10. interes_sincronizacion_recetas (Fake Door)
        trackRecipeSyncInterest: function (origenInteraccion, totalRecetasLocales) {
            this.pushEvent("interes_sincronizacion_recetas", {
                origen_interaccion: origenInteraccion,
                total_recetas_locales: totalRecetasLocales
            });
        },

        // 11. enviar_feedback
        trackSendFeedback: function (categoriaFeedback) {
            this.pushEvent("enviar_feedback", {
                categoria_feedback: categoriaFeedback
            });
        }
    };
})();
