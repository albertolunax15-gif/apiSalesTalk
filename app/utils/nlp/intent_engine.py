from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

from dateutil import parser as dateparser
from rapidfuzz import fuzz, process

# ===== NUEVO: import ligero con guard =====
try:
    # Ajusta el import si tu ruta real difiere
    from app.services.product_service import ProductService
except Exception:
    ProductService = None  # Permite testear este módulo sin backend

# =========================
# Configuración / Diccionarios
# =========================
PAYMENT_METHODS = ["Efectivo", "Tarjeta", "Yape", "Plin", "Transferencia"]
PAYMENT_ALIASES = {
    "efectivo": "Efectivo",
    "cash": "Efectivo",
    "tarjeta": "Tarjeta",
    "visa": "Tarjeta",
    "mastercard": "Tarjeta",
    "yape": "Yape",
    "plin": "Plin",
    "transferencia": "Transferencia",
    "transf": "Transferencia",
    "banco": "Transferencia",
}

CREAR_VENTA_PATTERNS = [
    r"\b(registrar|registra|registrame)\b.*\b(venta|compra)?\b",
    r"\b(generar|genera|crear|crea|agrega|anade|añade)\b.*\b(venta|compra)?\b",
    r"\b(vender|vende|venta)\b",
    r"\b(compra|comprar|compro|compraron)\b",
]

LISTAR_VENTAS_PATTERNS = [
    r"\b(lista(r)?|ver|mostrar|muestrame|muestreme|ensename)\b.*\b(ventas?)\b",
]

AYUDA_PATTERNS = [
    r"\bayuda\b",
    r"\bque puedes hacer\b",
    r"\bcomo te uso\b",
]

# =========================
# Modelos de datos
# =========================
@dataclass
class ParsedSale:
    quantity: Optional[int] = None
    product_name: Optional[str] = None
    price: Optional[float] = None
    payment_method: Optional[str] = None
    date: Optional[datetime] = None

@dataclass
class NLPResult:
    intent: str
    confidence: float
    entities: Dict[str, Any]
    original_text: str
    notes: List[str]

# =========================
# Utilitarios
# =========================
def _norm(s: str) -> str:
    if s is None:
        return ""
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _match_any(patterns: List[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)

# =========================
# Detección de intent
# =========================
def _guess_intent(text: str) -> tuple[str, float]:
    nt = _norm(text)
    if _match_any(CREAR_VENTA_PATTERNS, nt):
        return "crear_venta", 1.0
    if _match_any(LISTAR_VENTAS_PATTERNS, nt):
        return "listar_ventas", 0.95
    if _match_any(AYUDA_PATTERNS, nt):
        return "ayuda", 0.9

    INTENT_KEYWORDS = {
        "crear_venta": [
            "vende", "venta", "registrar venta", "registrame",
            "agrega venta", "añade venta", "compro", "compraron",
            "compra", "crear venta", "genera venta"
        ],
        "listar_ventas": [
            "lista ventas", "listar ventas", "muestrame ventas", "ver ventas", "mostrar ventas"
        ],
        "ayuda": [
            "ayuda", "que puedes hacer", "como te uso"
        ],
    }
    best_intent, best_score = "ayuda", 0.0
    for intent, keys in INTENT_KEYWORDS.items():
        score = max(fuzz.partial_ratio(nt, _norm(k)) for k in keys)
        if score > best_score:
            best_intent, best_score = intent, score / 100.0
    return best_intent, best_score

# =========================
# Extracciones
# =========================
def _extract_quantity(text: str) -> Optional[int]:
    t = _norm(text)
    m = re.search(r"(?:x\s*)?(\d+)\s*(?:u|und|unid|unidades)?\b", t)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    words_map = {"una":1,"un":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,"diez":10}
    for w, n in words_map.items():
        if re.search(rf"\b{w}\b", t):
            return n
    return None

def _extract_price(text: str) -> Optional[float]:
    t = text.lower()
    m = re.search(r"(?:s\/\.?|soles?\s*)?(\d{1,4}(?:[\.,]\d{1,2})?)\s*(?:soles?)?", t)
    if m:
        raw = m.group(1).replace(",", ".")
        try:
            return float(raw)
        except:
            return None
    return None

def _extract_payment_method(text: str) -> Optional[str]:
    t = _norm(text)
    for k, norm_pm in PAYMENT_ALIASES.items():
        if re.search(rf"\b{_norm(k)}\b", t):
            return norm_pm
    match = process.extractOne(t, PAYMENT_METHODS, scorer=fuzz.partial_ratio)
    if match and match[1] >= 85:
        return match[0]
    return None

def _extract_date(text: str) -> Optional[datetime]:
    t = _norm(text)
    if "hoy" in t:
        return datetime.now()
    if "ayer" in t:
        return datetime.now() - timedelta(days=1)
    if "manana" in t:
        return datetime.now() + timedelta(days=1)
    try:
        dt = dateparser.parse(text, dayfirst=True, fuzzy=True)
        return dt
    except:
        return None

def _extract_product_name(text: str) -> Optional[str]:
    t = _norm(text)
    t = re.sub(r"\b\d+\b", " ", t)
    t = re.sub(r"(s\/\.?\s*\d+(?:[\.,]\d+)?|soles?)", " ", t)
    for alias in PAYMENT_ALIASES.keys():
        t = re.sub(rf"\b{_norm(alias)}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    verb_pattern = r"(?:vende(r)?|venta|registrar|registra|registrame|agrega|anade|añade|crear|crea|generar|genera|compra|comprar)"
    m = re.search(rf"{verb_pattern}\s+(?:venta|compra)?\s*(?:de\s+)?(.+)", t)

    candidate = None
    if m:
        captured = m.group(1) if (m.lastindex and m.group(1) is not None) else ""
        candidate = captured.strip()
        if candidate:
            candidate = re.sub(r"\b(o|y)\b", " ", candidate)  # "o nigiris" -> "nigiris"
            candidate = re.sub(r"\s+", " ", candidate).strip()

    if candidate:
        return candidate

    parts = t.split()
    return " ".join(parts[-4:]) if parts else None

# =========================
# Resolución de product_id via RTDB (clave)
# =========================
def _search_products_in_backend(name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Usa ProductService.find_by_name para traer candidatos (id, name, price, status, created_at).
    Si ProductService no está disponible (tests), retorna [].
    """
    if not name or not ProductService:
        return []
    try:
        return ProductService.find_by_name(name, limit=limit) or []
    except Exception:
        return []

def _select_best_candidate(name: str, candidates: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Ordena candidatos por similitud con 'name' (token_sort_ratio).
    Retorna (mejor_candidato_o_None, candidatos_rankeados_con_score).
    """
    ranked = []
    for c in candidates:
        pname = (c.get("name") or "").strip()
        score = fuzz.token_sort_ratio(name, pname)
        ranked.append({**c, "_score": int(score)})
    ranked.sort(key=lambda x: x["_score"], reverse=True)
    best = ranked[0] if ranked else None
    return best, ranked

# =========================
# Orquestador principal
# =========================
def interpret_text(text: str) -> NLPResult:
    intent, conf = _guess_intent(text)
    notes: List[str] = []
    entities: Dict[str, Any] = {}

    if intent == "crear_venta":
        sale = ParsedSale()
        sale.quantity = _extract_quantity(text) or 1
        sale.price = _extract_price(text)  # opcional/telemetría
        sale.payment_method = _extract_payment_method(text) or "Efectivo"
        sale.date = _extract_date(text) or datetime.now()
        sale.product_name = _extract_product_name(text)

        product_id: Optional[str] = None
        candidates_aux: List[Dict[str, Any]] = []

        if sale.product_name:
            raw_candidates = _search_products_in_backend(sale.product_name, limit=10)
            best, ranked = _select_best_candidate(sale.product_name, raw_candidates)

            # Guardamos candidatos (id, name, _score) para UI (no enviar al backend)
            candidates_aux = [{"id": c.get("id"), "name": c.get("name"), "score": c.get("_score", 0)} for c in ranked]

            if best and best.get("_score", 0) >= 85:
                product_id = best.get("id")
                notes.append(f"Producto seleccionado automáticamente: '{best.get('name')}' (score={best.get('_score')}%).")
            elif ranked:
                notes.append("Coincidencia ambigua: se requieren confirmación del producto.")
            else:
                notes.append("No se encontraron productos en el catálogo para ese nombre.")

        else:
            notes.append("No se pudo extraer un nombre de producto desde el texto.")

        # === Payload que espera tu POST ===
        entities = {
            "payment_method": sale.payment_method,
            "product_id": product_id,   # None si ambiguo/no encontrado
            "quantity": sale.quantity,
            # Auxiliar para la UI (NO enviar al endpoint de creación):
            "_candidates": candidates_aux
        }

        if sale.price is None:
            notes.append("No se detectó precio en el comando (se usará el del catálogo/backend).")

    return NLPResult(
        intent=intent,
        confidence=conf,
        entities=entities,
        original_text=text,
        notes=notes
    )