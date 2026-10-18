import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from core.normalizer import SCAFlavorWheelNormalizer, sanitize_text
from scrapper.coffee_metadata import generar_resumen_corto

logger = logging.getLogger("core.extractor")

# =====================================================================
# CONSTANTES Y LISTAS MAESTRAS DE ATRIBUTOS BOTÁNICOS / ORGANOLÉPTICOS
# =====================================================================

VARIEDADES_CONOCIDAS = [
    "gesha", "geisha", "bourbon", "bourbon rosado", "pink bourbon", "red bourbon",
    "yellow bourbon", "caturra", "castillo", "pacamara", "typica", "catuai",
    "maragogipe", "maracaturra", "sl28", "sl34", "tabi", "wush wush", "sidra",
    "java", "colombia", "moka", "pacas", "parainema", "san bernardo", "catimor",
    "villa sarchi", "villalobos", "heirloom", "etiopia silvestre", "chiroso"
]

PROCESOS_CONOCIDOS = {
    "lavado": "Lavado",
    "washed": "Lavado",
    "wash": "Lavado",
    "totalmente lavado": "Lavado",
    "fully washed": "Lavado",
    "natural": "Natural",
    "dry": "Natural",
    "honey": "Honey",
    "miel": "Honey",
    "red honey": "Red Honey",
    "yellow honey": "Yellow Honey",
    "black honey": "Black Honey",
    "white honey": "White Honey",
    "anaerobico": "Anaeróbico",
    "anaerobic": "Anaeróbico",
    "maceracion carbonica": "Maceración Carbónica",
    "carbonic maceration": "Maceración Carbónica",
    "doble fermentacion": "Doble Fermentación",
    "double fermentation": "Doble Fermentación",
    "fermentacion lactica": "Fermentación Láctica",
    "koji": "Koji",
}

PAISES_ORIGEN: Dict[str, str] = {
    "etiopia": "Etiopía",
    "ethiopia": "Etiopía",
    "colombia": "Colombia",
    "kenia": "Kenia",
    "kenya": "Kenia",
    "guatemala": "Guatemala",
    "costa rica": "Costa Rica",
    "brasil": "Brasil",
    "brazil": "Brasil",
    "panama": "Panamá",
    "peru": "Perú",
    "ruanda": "Ruanda",
    "rwanda": "Ruanda",
    "burundi": "Burundi",
    "honduras": "Honduras",
    "mexico": "México",
    "el salvador": "El Salvador",
    "ecuador": "Ecuador",
    "bolivia": "Bolivia",
    "indonesia": "Indonesia",
    "yemen": "Yemen",
    "nicaragua": "Nicaragua",
}


def compute_description_hash(text: Optional[str]) -> str:
    """Calcula el hash MD5 de la descripción limpia para idempotencia y hash diffing."""
    if not text:
        return ""
    normalized = re.sub(r"\s+", " ", str(text)).strip().encode("utf-8")
    return hashlib.md5(normalized).hexdigest()


class CoffeeAttributesExtractor:
    """
    Pipeline de Ingesta en Cascada (3 Capas):
    - Capa 1: Estructural / RegEx (0 ms, 100% determinista)
    - Capa 2: Zero-Shot NER (<50 ms, ~300 MB, GLiNER)
    - Capa 3: Fallback Generativo Ultraligero (<1.5 GB, Qwen 2.5 1.5B GGUF) con Hash Diffing
    """

    def __init__(
        self,
        gliner_model_name: str = "knowledgator/gliner-multilingual-v2.1",
        qwen_model_path: Optional[str] = None,
    ):
        self.gliner_model_name = gliner_model_name
        self.qwen_model_path = qwen_model_path
        self._gliner_pipeline = None
        self._llm_instance = None

    # =================================================================
    # CAPA 1: EXTRACCIÓN ESTRUCTURAL / REGEX (0 ms)
    # =================================================================
    def _extract_layer_1(self, text: str) -> Dict[str, Any]:
        """
        Analiza patrones explícitos de etiquetas y diccionarios botánicos.
        Cubre el 90%+ de fichas técnicas bien formadas en e-commerce de especialidad.
        """
        extracted = {
            "origen": None,
            "finca_productor": None,
            "variedad": None,
            "proceso": None,
            "lote": None,
            "puntuacion_sca": None,
            "tueste": None,
            "escala_agtron": None,
            "notas_cata": [],
            "capa": 1,
            "confianza": 0.0,
        }

        if not text:
            return extracted

        # 1. Notas de cata explícitas: (?:notas|perfil|descriptores|cata)\s*[:|-]\s*([^\n\.<]+)
        match_notas = re.search(
            r"(?:notas\s*(?:de\s*cata)?|perfil\s*(?:en\s*taza)?|descriptores|tasting\s*notes?|sensorial)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        if match_notas:
            raw_chunk = match_notas.group(1).strip()
            # Separadores comunes: comas, guiones, barras, 'y', '&'
            tokens = re.split(r"[,;|/•]|\s+(?:y|and|&)\s+", raw_chunk, flags=re.IGNORECASE)
            cleaned_tokens = [t.strip(" .") for t in tokens if len(t.strip(" .")) > 1]
            extracted["notas_cata"] = cleaned_tokens

        # 2. Proceso
        match_proc_label = re.search(
            r"(?:proceso|beneficio|processing(?:\s*method)?)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        if match_proc_label:
            val = match_proc_label.group(1).strip()
            val_sanitized = sanitize_text(val)
            for k, v in PROCESOS_CONOCIDOS.items():
                if k in val_sanitized:
                    extracted["proceso"] = v
                    break
            if not extracted["proceso"]:
                extracted["proceso"] = val.split(",")[0].strip().capitalize()
        else:
            # Búsqueda directa de palabras clave de proceso en el texto
            text_sanitized = sanitize_text(text)
            for k, v in PROCESOS_CONOCIDOS.items():
                if re.search(rf"\b{re.escape(k)}\b", text_sanitized):
                    extracted["proceso"] = v
                    break

        # 3. Variedad
        match_var_label = re.search(
            r"(?:variedad|varietal|variety|cultivar)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        if match_var_label:
            val = match_var_label.group(1).strip()
            val_sanitized = sanitize_text(val)
            for var in sorted(VARIEDADES_CONOCIDAS, key=len, reverse=True):
                if var in val_sanitized:
                    extracted["variedad"] = var.title()
                    break
            if not extracted["variedad"]:
                extracted["variedad"] = val.split(",")[0].strip().title()
        else:
            # Búsqueda directa de variedades conocidas
            text_sanitized = sanitize_text(text)
            for var in sorted(VARIEDADES_CONOCIDAS, key=len, reverse=True):
                if re.search(rf"\b{re.escape(var)}\b", text_sanitized):
                    extracted["variedad"] = var.title()
                    break

        # 4. Finca y Productor
        match_finca = re.search(
            r"(?:finca|farm|fazenda|estaci[oó]n|beneficio)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        match_prod = re.search(
            r"(?:productor|producer)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        finca_val = match_finca.group(1).strip() if match_finca else None
        prod_val = match_prod.group(1).strip() if match_prod else None

        if finca_val and prod_val:
            extracted["finca_productor"] = f"{finca_val} / {prod_val}"
        elif finca_val:
            extracted["finca_productor"] = finca_val
        elif prod_val:
            extracted["finca_productor"] = prod_val

        # 5. Lote
        match_lote = re.search(
            r"(?:lote|lot(?:\s*no\.?)?)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        if match_lote:
            extracted["lote"] = match_lote.group(1).strip()

        # 6. Origen / País
        match_origen = re.search(
            r"(?:pa[ií]s(?:\s*de\s*origen)?|origen|origin|country)\s*[:|–—-]\s*([^\n\.<]+)",
            text,
            re.IGNORECASE,
        )
        if match_origen:
            val = match_origen.group(1).strip()
            primera_parte = val.split(",")[0].strip()
            val_sanit = sanitize_text(primera_parte)
            for k, canonical in PAISES_ORIGEN.items():
                if k == val_sanit:
                    extracted["origen"] = canonical
                    break
            if not extracted["origen"]:
                extracted["origen"] = primera_parte.title()
        else:
            text_sanitized = sanitize_text(text)
            for k, canonical in PAISES_ORIGEN.items():
                if re.search(rf"\b{re.escape(k)}\b", text_sanitized):
                    extracted["origen"] = canonical
                    break

        # 7. Puntuación SCA (Calificación de catación Q-Grader de 80 a 99 puntos)
        match_sca = re.search(
            r"(?:puntuaci[oó]n|puntaje|score|calificaci[oó]n|nota)?\s*(?:sca|q(?:\s*grader)?)?\s*[:|–—-]?\s*([89]\d(?:\.\d{1,2})?)\s*(?:puntos|pts|ptos|sca)?",
            text,
            re.IGNORECASE,
        )
        match_sca_explicit = re.search(
            r"\b([89]\d(?:\.\d{1,2})?)\s*(?:puntos\s*sca|pts\.?\s*sca|ptos\.?\s*sca|sca\b)",
            text,
            re.IGNORECASE,
        )
        val_sca = None
        if match_sca_explicit:
            val_sca = match_sca_explicit.group(1)
        elif match_sca and (match_sca.group(0).lower().find("sca") != -1 or match_sca.group(0).lower().find("punt") != -1 or match_sca.group(0).lower().find("score") != -1):
            val_sca = match_sca.group(1)

        if val_sca:
            try:
                score_f = float(val_sca)
                if 80.0 <= score_f <= 99.5:
                    extracted["puntuacion_sca"] = round(score_f, 2)
            except (ValueError, TypeError):
                pass

        # 8. Nivel de Tueste y Escala Agtron
        match_agtron = re.search(
            r"(?:escala\s*)?agtron\s*[:|–—-]?\s*(?:#\s*)?(\d{2,3})",
            text,
            re.IGNORECASE,
        )
        if match_agtron:
            try:
                agtron_num = int(match_agtron.group(1))
                if 10 <= agtron_num <= 120:
                    extracted["escala_agtron"] = agtron_num
                    if agtron_num >= 85:
                        extracted["tueste"] = f"Muy Claro (Agtron {agtron_num})"
                    elif agtron_num >= 75:
                        extracted["tueste"] = f"Claro / Filtro (Agtron {agtron_num})"
                    elif agtron_num >= 65:
                        extracted["tueste"] = f"Medio-Claro (Agtron {agtron_num})"
                    elif agtron_num >= 55:
                        extracted["tueste"] = f"Medio (Agtron {agtron_num})"
                    elif agtron_num >= 45:
                        extracted["tueste"] = f"Medio-Oscuro (Agtron {agtron_num})"
                    elif agtron_num >= 35:
                        extracted["tueste"] = f"Oscuro (Agtron {agtron_num})"
                    else:
                        extracted["tueste"] = f"Muy Oscuro (Agtron {agtron_num})"
            except (ValueError, TypeError):
                pass

        if not extracted.get("tueste"):
            match_tueste = re.search(
                r"(?:tueste|roast(?:\s*level)?|nivel\s*de\s*tueste)\s*[:|–—-]\s*([^\n\.<,]+)",
                text,
                re.IGNORECASE,
            )
            if match_tueste:
                extracted["tueste"] = match_tueste.group(1).strip().capitalize()
            else:
                text_san = sanitize_text(text)
                if re.search(r"\b(?:tueste\s*claro|light\s*roast)\b", text_san):
                    extracted["tueste"] = "Claro (Agtron ~75-85)"
                elif re.search(r"\b(?:tueste\s*medio[- ]claro|medium[- ]light)\b", text_san):
                    extracted["tueste"] = "Medio-Claro (Agtron ~65-75)"
                elif re.search(r"\b(?:tueste\s*medio|medium\s*roast|omni[- ]?roast)\b", text_san):
                    extracted["tueste"] = "Medio (Agtron ~55-65)"
                elif re.search(r"\b(?:tueste\s*medio[- ]oscuro|medium[- ]dark)\b", text_san):
                    extracted["tueste"] = "Medio-Oscuro (Agtron ~45-55)"
                elif re.search(r"\b(?:tueste\s*oscuro|dark\s*roast|espresso\s*roast)\b", text_san):
                    extracted["tueste"] = "Oscuro (Agtron ~35-45)"

        # Medición de confianza
        # Si tiene proceso Y variedad Y notas -> alta confianza (>90%)
        puntos = 0
        if extracted["proceso"]:
            puntos += 30
        if extracted["variedad"]:
            puntos += 30
        if extracted["notas_cata"]:
            puntos += 20
        if extracted["origen"]:
            puntos += 10
        if extracted["puntuacion_sca"]:
            puntos += 10
        extracted["confianza"] = round(min(100, puntos) / 100.0, 2)

        return extracted

    # =================================================================
    # CAPA 2: ZERO-SHOT NER CON GLiNER (<50 ms, ~300 MB)
    # =================================================================
    def _extract_layer_2(self, text: str, prev_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Usa GLiNER multilingüe para token classification zero-shot si faltan atributos críticos.
        """
        data = dict(prev_data)
        data["capa"] = 2

        try:
            # Lazy import para no bloquear en entornos de pruebas sin GLiNER
            if self._gliner_pipeline is None:
                from gliner import GLiNER
                self._gliner_pipeline = GLiNER.from_pretrained(self.gliner_model_name)

            labels = [
                "nota_de_cata",
                "variedad_cafe",
                "proceso_beneficio",
                "finca_o_productor",
                "notas de cata",
                "variedad de café",
                "proceso de café",
                "finca o productor",
                "origen del café",
                "lote de café",
            ]
            entities = self._gliner_pipeline.predict_entities(text, labels, threshold=0.4)

            for ent in entities:
                lbl = ent["label"]
                val = ent["text"].strip()
                if lbl in ["variedad de café", "variedad_cafe"] and not data.get("variedad"):
                    data["variedad"] = val.title()
                elif lbl in ["proceso de café", "proceso_beneficio"] and not data.get("proceso"):
                    data["proceso"] = val.capitalize()
                elif lbl in ["origen del café", "origen"] and not data.get("origen"):
                    data["origen"] = val.capitalize()
                elif lbl in ["finca o productor", "finca_o_productor"] and not data.get("finca_productor"):
                    data["finca_productor"] = val
                elif lbl in ["lote de café", "lote"] and not data.get("lote"):
                    data["lote"] = val
                elif lbl in ["notas de cata", "nota_de_cata"]:
                    if val not in data["notas_cata"]:
                        data["notas_cata"].append(val)

            # Recalcular confianza
            puntos = 0
            if data["proceso"]:
                puntos += 35
            if data["variedad"]:
                puntos += 35
            if data["notas_cata"]:
                puntos += 20
            if data["origen"]:
                puntos += 10
            data["confianza"] = round(puntos / 100.0, 2)

        except Exception as e:
            logger.info("Capa 2 (GLiNER) no disponible o en fallback: %s", e)

        return data

    # =================================================================
    # CAPA 3: FALLBACK GENERATIVO ULTRALIGERO (Qwen 2.5 1.5B GGUF)
    # =================================================================
    def _extract_layer_3(self, text: str, prev_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta Qwen2.5-1.5B-Instruct en formato GGUF (CPU, quant q4_k_m)
        con prompt en formato JSON estricto.
        """
        data = dict(prev_data)
        data["capa"] = 3

        try:
            if self._llm_instance is None and self.qwen_model_path:
                from llama_cpp import Llama
                self._llm_instance = Llama(
                    model_path=self.qwen_model_path,
                    n_ctx=2048,
                    n_threads=2,
                    verbose=False,
                )

            if not self._llm_instance:
                return data

            prompt = (
                "<|im_start|>system\n"
                "Eres un extractor botánico y organoléptico de café de especialidad. "
                "Responde ÚNICAMENTE un objeto JSON válido con los campos: "
                "\"origen\", \"finca_productor\", \"variedad\", \"proceso\", \"lote\", \"notas\" (array de strings).<|im_end|>\n"
                f"<|im_start|>user\nExtrae la información del siguiente café:\n{text[:1000]}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )

            response = self._llm_instance(
                prompt,
                max_tokens=256,
                temperature=0.0,
                stop=["<|im_end|>"],
            )
            output_text = response["choices"][0]["text"].strip()

            # Extraer JSON del bloque de respuesta
            json_match = re.search(r"\{.*\}", output_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                for key in ["origen", "finca_productor", "variedad", "proceso", "lote"]:
                    if parsed.get(key) and not data.get(key):
                        data[key] = str(parsed[key]).strip()
                notas_list = parsed.get("notas") or parsed.get("notas_cata")
                if isinstance(notas_list, list):
                    for nota in notas_list:
                        if nota and str(nota).strip() not in data["notas_cata"]:
                            data["notas_cata"].append(str(nota).strip())
                data["confianza"] = 0.85

        except Exception as e:
            logger.info("Capa 3 (Qwen GGUF) no disponible o en fallback: %s", e)

        return data

    def _extract_from_title(self, title: str, current_data: Dict[str, Any]) -> None:
        """
        Inspecciona explícitamente el título para extraer país de origen y puntuación SCA si faltan.
        """
        if not title:
            return
        
        # 1. Origen desde el título
        if not current_data.get("origen"):
            title_sanitized = sanitize_text(title)
            for k, canonical in sorted(PAISES_ORIGEN.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(rf"\b{re.escape(k)}\b", title_sanitized):
                    current_data["origen"] = canonical
                    break

        # 2. Puntuación SCA desde el título
        if not current_data.get("puntuacion_sca"):
            match_sca = re.search(
                r"\b([89]\d(?:\.\d{1,2})?)\s*(?:puntos|pts|ptos|sca)\b|\bsca\s*[:|–—-]?\s*([89]\d(?:\.\d{1,2})?)\b",
                title,
                re.IGNORECASE,
            )
            if match_sca:
                val = match_sca.group(1) or match_sca.group(2)
                try:
                    score_f = float(val)
                    if 80.0 <= score_f <= 99.5:
                        current_data["puntuacion_sca"] = round(score_f, 2)
                except (ValueError, TypeError):
                    pass

    # =================================================================
    # ORQUESTADOR EN CASCADA
    # =================================================================
    def extract(
        self,
        text: Optional[str],
        nombre_producto: Optional[str] = "",
        existing_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline en cascada con evaluación de confianza y hash diffing:
        1. Calcula MD5 de la descripción.
        2. Ejecuta Capa 1 (RegEx). Si proceso y notas/variedad fueron detectados, retorna (0 ms).
        3. Si faltan datos críticos, intenta Capa 2 (GLiNER). Si confianza >= 0.85, retorna.
        4. Si Capa 1 y 2 no bastan Y hash es nuevo, invoca Capa 3 (Qwen GGUF).
        5. Normaliza las notas resultantes con SCAFlavorWheelNormalizer.
        """
        full_text = f"{nombre_producto or ''}\n{text or ''}".strip()
        current_hash = compute_description_hash(full_text)

        # 1. Capa 1: RegEx
        res_l1 = self._extract_layer_1(full_text)

        # Si Capa 1 detectó proceso Y notas (o proceso Y variedad), terminar inmediatamente
        capa_1_completa = bool(res_l1.get("proceso")) and (bool(res_l1.get("notas_cata")) or bool(res_l1.get("variedad")))
        if capa_1_completa or res_l1.get("confianza", 0) >= 0.85:
            final_data = res_l1
        else:
            # 2. Capa 2: NER GLiNER
            res_l2 = self._extract_layer_2(full_text, res_l1)
            if res_l2.get("confianza", 0) >= 0.85:
                final_data = res_l2
            else:
                # 3. Capa 3: Fallback LLM solo si hash es nuevo / cambió
                hash_ha_cambiado = not existing_hash or existing_hash != current_hash
                if hash_ha_cambiado and self.qwen_model_path:
                    final_data = self._extract_layer_3(full_text, res_l2)
                else:
                    final_data = res_l2

        # Análisis adicional sobre el título si faltó país o puntaje SCA
        if nombre_producto:
            self._extract_from_title(nombre_producto, final_data)

        # Normalización estricta de notas SCA
        raw_notes = final_data.get("notas_cata", [])
        clasificacion_sca = SCAFlavorWheelNormalizer.clasificar_notas(raw_notes)

        final_data["notas_cata"] = clasificacion_sca["notas_originales"]
        final_data["notas_normalizadas"] = clasificacion_sca["notas_normalizadas"]
        final_data["macro_familias"] = clasificacion_sca["macro_familias"]
        final_data["hash_descripcion"] = current_hash

        resumen = generar_resumen_corto(
            titulo=nombre_producto,
            descripcion=text,
            notas=final_data["notas_cata"] or final_data["notas_normalizadas"],
            proceso=final_data.get("proceso"),
            origen=final_data.get("origen"),
            variedad=final_data.get("variedad"),
        )
        final_data["resumen_corto"] = resumen
        final_data["descripcion_resumida"] = resumen

        return final_data
