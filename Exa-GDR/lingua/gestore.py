"""
lingua/gestore.py — Gestione multilingua
"""
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_lingua_corrente = "it"
_dizionario = {}

def imposta_lingua(codice: str):
    global _lingua_corrente, _dizionario
    _lingua_corrente = codice
    if codice == "en":
        from lingua.en import TESTI
    else:
        from lingua.it import TESTI
    _dizionario = TESTI

def t(chiave: str) -> str:
    """Restituisce la stringa tradotta per la chiave data."""
    return _dizionario.get(chiave, chiave)

def lingua_corrente() -> str:
    return _lingua_corrente

# Inizializza con italiano di default
imposta_lingua("it")
