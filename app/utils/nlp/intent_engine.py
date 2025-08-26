from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from rapidfuzz import fuzz, process

# Diccionarios base (ajústalos según tu dominio)
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

# Reglas: palabras clave por intent
INTENT_KEYWORDS = {
    "crear_venta": ["vende", "venta", "registrar venta", "registrame", "agrega venta", "añade venta", "compró", "compraron"],
    "listar_ventas": ["lista ventas", "listar ventas", "muéstrame ventas", "ver ventas"],
    "ayuda": ["ayuda", "qué puedes hacer", "como te uso"]
}

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

def _guess_intent(text: str) -> tuple[str, float]:
    t = text.lower()
    best_intent, best_score = "ayuda", 0.0
    for intent, keys in INTENT_KEYWORDS.items():
        score = max(fuzz.partial_ratio(t, k) for k in keys)
        if score > best_score:
            best_intent, best_score = intent, score / 100.0
    return best_intent, best_score

def _extract_quantity(text: str) -> Optional[int]:
    # patrones comunes: "2", "x2", "2u", "2 und", "dos" (num palabras simple)
    m = re.search(r"(?:x\s*)?(\d+)\s*(?:u|und|unid|unidades)?\b", text.lower())
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    # muy básico para palabras
    words_map = {"una":1,"un":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,"diez":10}
    for w, n in words_map.items():
        if re.search(rf"\b{w}\b", text.lower()):
            return n
    return None

def _extract_price(text: str) -> Optional[float]:
    # "a 3.50", "S/ 4", "4 soles", "precio 2"
    m = re.search(r"(?:s\/\.?|soles?\s*)?(\d{1,4}(?:[\.,]\d{1,2})?)\s*(?:soles?)?", text.lower())
    if m:
        raw = m.group(1).replace(",", ".")
        try:
            return float(raw)
        except:
            return None
    return None

def _extract_payment_method(text: str) -> Optional[str]:
    t = text.lower()
    # alias exacto
    for k, norm in PAYMENT_ALIASES.items():
        if re.search(rf"\b{k}\b", t):
            return norm
    # fuzzy sobre label oficial
    match = process.extractOne(t, PAYMENT_METHODS, scorer=fuzz.partial_ratio)
    if match and match[1] >= 85:
        return match[0]
    return None

def _extract_date(text: str) -> Optional[datetime]:
    t = text.lower()
    if "hoy" in t:
        return datetime.now()
    if "ayer" in t:
        return datetime.now() - timedelta(days=1)
    if "mañana" in t or "manana" in t:
        return datetime.now() + timedelta(days=1)
    # intenta parseo general (soporta "25/08 5pm", "2025-08-25", etc.)
    try:
        dt = dateparser.parse(text, dayfirst=True, fuzzy=True)
        return dt
    except:
        return None

def _extract_product_name(text: str, candidate_products: Optional[List[str]]=None) -> Optional[str]:
    # Heurística: quita números y palabras de pago para dejar el núcleo
    t = re.sub(r"\d+|s\/\.?\s*\d+(?:[\.,]\d+)?|soles?", " ", text.lower())
    for alias in PAYMENT_ALIASES.keys():
        t = re.sub(rf"\b{alias}\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # Si hay catálogo, busca difuso
    if candidate_products:
        match = process.extractOne(t, candidate_products, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 70:
            return match[0]
    # fallback: toma frases después de verbos de venta
    m = re.search(r"(?:vende(?:r)?|venta|registrar|agrega|añade)\s+(.*)", t)
    if m:
        return m.group(1).strip()
    # si no, devuelve algo acotado (últimas 4 palabras)
    parts = t.split()
    if len(parts) >= 1:
        return " ".join(parts[-4:])
    return None

def interpret_text(text: str, candidate_products: Optional[List[str]]=None) -> NLPResult:
    intent, conf = _guess_intent(text)
    notes: List[str] = []
    entities: Dict[str, Any] = {}

    if intent == "crear_venta":
        sale = ParsedSale()
        sale.quantity = _extract_quantity(text) or 1
        sale.price = _extract_price(text)
        sale.payment_method = _extract_payment_method(text) or "Efectivo"
        sale.date = _extract_date(text) or datetime.now()
        sale.product_name = _extract_product_name(text, candidate_products)
        entities = {
            "quantity": sale.quantity,
            "price": sale.price,
            "payment_method": sale.payment_method,
            "date": sale.date.isoformat(),
            "product_name": sale.product_name,
        }
        # notas de calidad
        if sale.product_name is None:
            notes.append("No se pudo identificar el producto con confianza.")
        if sale.price is None:
            notes.append("No se encontró precio explícito (puede tomarse el del catálogo).")

    return NLPResult(
        intent=intent,
        confidence=conf,
        entities=entities,
        original_text=text,
        notes=notes
    )