from __future__ import annotations
import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import os
import csv

from dateutil import parser as dateparser
from rapidfuzz import fuzz, process

# ===== Import al backend con guarda (ajusta la ruta si difiere) =====
try:
    from app.services.product_service import ProductService
except Exception:
    ProductService = None  # Permite ejecutar este módulo sin backend

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

# Umbrales de selección
AUTO_SELECT_SCORE = 85
CONFIRM_SCORE_MIN = 70  # para UI; no autoselecciona por debajo de 85

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
    """Minúsculas, sin tildes, sin puntuación, espacios normalizados."""
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

    # Reglas determinísticas
    if _match_any(CREAR_VENTA_PATTERNS, nt):
        return "crear_venta", 1.0
    if _match_any(LISTAR_VENTAS_PATTERNS, nt):
        return "listar_ventas", 0.95
    if _match_any(AYUDA_PATTERNS, nt):
        return "ayuda", 0.9

    # Respaldo fuzzy
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
    # Dígitos: "x2", "2u", "2 und"
    m = re.search(r"(?:x\s*)?(\d+)\s*(?:u|und|unid|unidades)?\b", t)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    # Palabras
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
    # Alias exacto
    for k, norm_pm in PAYMENT_ALIASES.items():
        if re.search(rf"\b{_norm(k)}\b", t):
            return norm_pm
    # Fuzzy sobre label oficial
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
    # Normal base
    t = _norm(text)

    # Quita números, montos y palabras de pago
    t = re.sub(r"\b\d+\b", " ", t)
    t = re.sub(r"(s\/\.?\s*\d+(?:[\.,]\d+)?|soles?)", " ", t)
    for alias in PAYMENT_ALIASES.keys():
        t = re.sub(rf"\b{_norm(alias)}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Normalizaciones de STT para "onigiri(s)" y variantes comunes
    t = re.sub(r"\boni\s*giri(s)?\b", " onigiris ", t)      # "oni giri", "onigiri(s)"
    t = re.sub(r"\boni?guiri(s)?\b", " onigiris ", t)       # "oniguiri(s)"
    t = re.sub(r"\bnigui?ri(s)?\b", " onigiris ", t)        # "niguiri(s)", "niguri(s)"
    t = re.sub(r"\bo\s+nigui?ri(s)?\b", " onigiris ", t)    # "o niguiri(s)"
    t = re.sub(r"\s+", " ", t).strip()

    # Verbo + (venta|compra)? + (de)? + producto
    verb_pattern = r"(?:vende(r)?|venta|registrar|registra|registrame|agrega|anade|añade|crear|crea|generar|genera|compra|comprar)"
    m = re.search(rf"{verb_pattern}\s+(?:venta|compra)?\s*(?:de\s+)?(.+)", t)

    candidate = None
    if m:
        captured = m.group(1) if (m.lastindex and m.group(1) is not None) else ""
        candidate = captured.strip()

        if candidate:
            # Elimina conectores de 1 letra (o, y, e) aislados
            tokens = [tok for tok in candidate.split() if tok not in {"o", "y", "e"}]
            # Si el STT partió una palabra en 2 tokens, vuelve a unir si son muy cortos
            if len(tokens) == 2 and len(tokens[0]) <= 3 and len(tokens[1]) <= 5:
                joined = "".join(tokens)
                if re.search(r"onigiri(s)?", joined):
                    tokens = [joined]
            candidate = " ".join(tokens).strip()

    if candidate:
        return candidate

    # Fallback: últimas 4 palabras
    parts = t.split()
    return " ".join(parts[-4:]) if parts else None

# =========================
# Búsqueda de productos: backend + locales
# =========================
def _dedupe(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def _variants_for_lookup(name: str) -> List[str]:
    """
    Genera variantes tolerantes:
      - original normalizado
      - sin 'o|y|e' sueltos
      - sin espacios
      - sin stopwords básicas
      - prefijos de 6 y 4 letras (útil para RTDB por prefijo)
    """
    n = _norm(name)
    if not n:
        return []
    toks = n.split()

    # sin conectores de 1 letra
    no_single = [tok for tok in toks if len(tok) > 1 or tok not in {"o", "y", "e"}]
    v1 = " ".join(no_single).strip()

    # sin espacios (p.ej. "coca cola" -> "cocacola")
    v2 = v1.replace(" ", "")

    # sin stopwords sencillas
    stop = {"de", "del", "la", "el", "los", "las", "un", "una", "para", "por", "en", "con"}
    v3 = " ".join([t for t in no_single if t not in stop]).strip()

    # prefijos útiles
    v4 = v2[:6]
    v5 = v2[:4]

    candidates = [n, v1, v2, v3, v4, v5]
    return [v for v in _dedupe(candidates) if v]

def _search_products_in_backend(name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Intenta varias variantes con find_by_name (prefijo en RTDB).
    Si no encuentra nada, hace fallback a ProductService.list(200) y aplica ranking fuzzy local.
    """
    if not name or not ProductService:
        return []
    try:
        # 1) buscar por varias variantes
        agg: List[Dict[str, Any]] = []
        seen_ids = set()

        for q in _variants_for_lookup(name):
            res = ProductService.find_by_name(q, limit=limit) or []
            for r in res:
                rid = r.get("id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    agg.append(r)

        if agg:
            return agg

        # 2) fallback: listar y rankear localmente
        all_items = ProductService.list(limit=200) or []
        nn = _norm(name)
        ranked = []
        for item in all_items:
            pname = _norm(item.get("name") or "")
            score = fuzz.token_sort_ratio(nn, pname)
            ranked.append({**item, "_score": int(score)})
        ranked.sort(key=lambda x: x["_score"], reverse=True)
        ranked = [r for r in ranked if r["_score"] >= 60][:limit]
        return ranked
    except Exception:
        return []

def _normalize_local_candidates(items: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """
    Acepta:
      - list[str]                     -> {'id': None, 'name': str}
      - list[dict{id,name}]           -> {'id': id|None, 'name': name}
      - list[tuple(id, name)]         -> {'id': id|None, 'name': name}
    """
    out: List[Dict[str, Any]] = []
    if not items:
        return out
    for it in items:
        if isinstance(it, str) and it.strip():
            out.append({"id": None, "name": it.strip()})
        elif isinstance(it, dict):
            name = str(it.get("name") or "").strip()
            _id  = str(it.get("id") or "").strip() or None
            if name:
                out.append({"id": _id, "name": name})
        elif isinstance(it, (tuple, list)) and len(it) >= 2:
            _id  = str(it[0] or "").strip() or None
            name = str(it[1] or "").strip()
            if name:
                out.append({"id": _id, "name": name})
    return out

def _select_best_candidate(name: str, candidates: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Ordena por similitud (token_sort_ratio) y retorna (mejor, ranked)."""
    nn = _norm(name)
    ranked: List[Dict[str, Any]] = []
    for c in candidates:
        pname = _norm((c.get("name") or "").strip())
        score = fuzz.token_sort_ratio(nn, pname)
        ranked.append({**c, "_score": int(score)})
    ranked.sort(key=lambda x: x["_score"], reverse=True)
    best = ranked[0] if ranked else None
    return best, ranked

# =========================
# Soporte de DATASETS (CSV en misma carpeta)
# =========================

_DEFAULT_CATALOG_CANDIDATES: Optional[List[Dict[str, Any]]] = None
_DEFAULT_DATASET_ROWS: Optional[List[Dict[str, str]]] = None

def _here(*parts: str) -> str:
    """Ruta absoluta relativa a este archivo."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)

def load_product_catalog_csv(path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Lee products_catalog.csv (id,name,price) y devuelve [{'id','name'}, ...].
    Si path es None, busca en la misma carpeta que este archivo.
    """
    global _DEFAULT_CATALOG_CANDIDATES
    if _DEFAULT_CATALOG_CANDIDATES is not None:
        return _DEFAULT_CATALOG_CANDIDATES

    if path is None:
        path = _here("products_catalog.csv")
    if not os.path.exists(path):
        _DEFAULT_CATALOG_CANDIDATES = []
        return _DEFAULT_CATALOG_CANDIDATES

    items: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # normaliza nombres de columnas a lower
        fieldnames = [c.lower() for c in (reader.fieldnames or [])]
        # columnas mínimas
        has_id = "id" in fieldnames
        has_name = "name" in fieldnames
        for row in reader:
            # Si vienen con mayúsculas, DictReader ya da las claves tal cual;
            # usamos get flexible (prueba ambas variantes)
            name = (row.get("name") or row.get("Name") or row.get("NAME") or "").strip()
            _id  = (row.get("id") or row.get("Id") or row.get("ID") or "").strip()
            if not has_name:
                # intenta detectar columna de nombre
                for k in row.keys():
                    if k.lower() == "name":
                        name = (row.get(k) or "").strip()
                        break
            if not has_id:
                for k in row.keys():
                    if k.lower() == "id":
                        _id = (row.get(k) or "").strip()
                        break
            if name:
                items.append({"id": _id or None, "name": name})
    _DEFAULT_CATALOG_CANDIDATES = items
    return items

def load_training_dataset_csv(path: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Lee sales_assistant_dataset.csv (text,intent,...) y devuelve lista de dicts.
    Si path es None, busca en la misma carpeta que este archivo.
    """
    global _DEFAULT_DATASET_ROWS
    if _DEFAULT_DATASET_ROWS is not None:
        return _DEFAULT_DATASET_ROWS

    if path is None:
        path = _here("sales_assistant_dataset.csv")
    if not os.path.exists(path):
        _DEFAULT_DATASET_ROWS = []
        return _DEFAULT_DATASET_ROWS

    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: v for k, v in row.items()})
    _DEFAULT_DATASET_ROWS = rows
    return rows

def get_default_candidates() -> List[Dict[str, Any]]:
    """Devuelve candidatos del catálogo CSV (cacheado)."""
    return load_product_catalog_csv()

# =========================
# Orquestador principal
# =========================
def interpret_text(text: str, candidate_products: Optional[List[Any]] = None) -> NLPResult:
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
            # Backend (find_by_name con variantes) + fallback list(200)
            raw_candidates = _search_products_in_backend(sale.product_name, limit=10)

            # Si no hay backend o no devolvió nada, usa catálogo CSV por defecto
            if not raw_candidates:
                default_cands = get_default_candidates()
                raw_candidates = (raw_candidates or []) + default_cands

            # Fusiona candidatos locales del front (opcionales)
            local_candidates = _normalize_local_candidates(candidate_products)
            raw_candidates = (raw_candidates or []) + local_candidates

            best, ranked = _select_best_candidate(sale.product_name, raw_candidates)
            candidates_aux = [{"id": c.get("id"), "name": c.get("name"), "score": c.get("_score", 0)} for c in ranked]

            if best and best.get("_score", 0) >= AUTO_SELECT_SCORE:
                product_id = best.get("id")
                notes.append(f"Producto seleccionado automáticamente: '{best.get('name')}' (score={best.get('_score')}%).")
            elif ranked:
                notes.append("Coincidencia ambigua: se requiere confirmación del producto.")
            else:
                notes.append("No se encontraron productos en el catálogo para ese nombre.")
        else:
            notes.append("No se pudo extraer un nombre de producto desde el texto.")

        # === Payload que espera tu POST /sales ===
        entities = {
            "payment_method": sale.payment_method,
            "product_id": product_id,     # None si ambiguo/no encontrado
            "quantity": sale.quantity,
            # Auxiliar para la UI (NO enviar al endpoint de creación)
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