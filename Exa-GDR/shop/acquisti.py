"""
shop/acquisti.py — Gestione acquisti e verifica possesso asset
"""

from database.modelli import registra_acquisto, ha_acquistato, acquisti_utente
from auth.sessione_utente import utente_corrente


def acquista(asset_id: str, tipo_asset: str) -> tuple[bool, str]:
    utente = utente_corrente()
    if not utente:
        return False, "Nessun utente loggato."
    if ha_acquistato(utente["id"], asset_id):
        return False, "Hai già acquistato questo asset."
    registra_acquisto(utente["id"], asset_id, tipo_asset)
    return True, ""


def possiede(asset_id: str) -> bool:
    utente = utente_corrente()
    if not utente:
        return False
    return ha_acquistato(utente["id"], asset_id)


def lista_posseduti(tipo: str = None) -> list:
    utente = utente_corrente()
    if not utente:
        return []
    tutti = acquisti_utente(utente["id"])
    if tipo:
        return [a for a in tutti if a["tipo_asset"] == tipo]
    return tutti
