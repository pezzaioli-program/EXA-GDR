"""
mondi/mondo.py — Gestione mondi (solo DM)
"""

from database.modelli import (
    crea_mondo, trova_mondo, mondi_del_dm,
    aggiorna_mondo, elimina_mondo,
    crea_mappa, mappe_del_mondo, crea_sessione
)
from auth.sessione_utente import utente_corrente


class GestoreMondo:

    @staticmethod
    def crea(nome: str, lore: str = "", descrizione: str = "") -> int:
        utente = utente_corrente()
        if not utente or utente["ruolo"] != "dm":
            raise PermissionError("Solo il DM può creare mondi.")
        return crea_mondo(utente["id"], nome, lore, descrizione)

    @staticmethod
    def lista() -> list:
        utente = utente_corrente()
        if not utente:
            return []
        return mondi_del_dm(utente["id"])

    @staticmethod
    def carica(mondo_id: int) -> dict | None:
        return trova_mondo(mondo_id)

    @staticmethod
    def aggiorna(mondo_id: int, nome: str, lore: str, descrizione: str):
        aggiorna_mondo(mondo_id, nome, lore, descrizione)

    @staticmethod
    def elimina(mondo_id: int):
        elimina_mondo(mondo_id)

    @staticmethod
    def aggiungi_mappa(mondo_id: int, nome: str, livello: int = 0) -> int:
        return crea_mappa(mondo_id, nome, livello)

    @staticmethod
    def mappe(mondo_id: int) -> list:
        return mappe_del_mondo(mondo_id)

    @staticmethod
    def crea_sessione(mondo_id: int, mappa_id: int = None) -> int:
        return crea_sessione(mondo_id, mappa_id)
