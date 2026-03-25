"""
mappa/livelli.py — Gestione mappe multilivello
"""

import json
from mappa.map import Griglia
from mappa.esporta import griglia_a_dizionario, dizionario_a_griglia
from config import GRIGLIA_COLONNE_DEFAULT, GRIGLIA_RIGHE_DEFAULT, HEX_DIMENSIONE, PANNELLO_LARGHEZZA


class GestoreMultilivello:
    """
    Gestisce più livelli di una stessa mappa.

    livello  0 = piano terra
    livello  1 = primo piano
    livello -1 = sotterraneo
    """

    def __init__(self, mappa_id: int = None):
        self.mappa_id   = mappa_id
        self._livelli:  dict[int, Griglia] = {}
        self._corrente: int = 0

    @property
    def livello_corrente(self) -> int:
        return self._corrente

    @property
    def griglia_corrente(self) -> Griglia | None:
        return self._livelli.get(self._corrente)

    def aggiungi_livello(self, livello: int, griglia: Griglia = None):
        if griglia is None:
            griglia = Griglia(
                GRIGLIA_COLONNE_DEFAULT, GRIGLIA_RIGHE_DEFAULT,
                HEX_DIMENSIONE,
                offset_x=PANNELLO_LARGHEZZA + 20, offset_y=40
            )
        self._livelli[livello] = griglia

    def vai_a_livello(self, livello: int) -> bool:
        if livello not in self._livelli:
            self.aggiungi_livello(livello)
        self._corrente = livello
        return True

    def livelli_disponibili(self) -> list[int]:
        return sorted(self._livelli.keys())

    def nome_livello(self, livello: int) -> str:
        if livello == 0:   return "Piano terra"
        if livello > 0:    return f"{livello}° piano"
        return f"Sotterraneo {abs(livello)}"

    def serializza(self) -> dict:
        return {
            str(lv): griglia_a_dizionario(gr)
            for lv, gr in self._livelli.items()
        }

    @classmethod
    def deserializza(cls, dati: dict, mappa_id: int = None) -> "GestoreMultilivello":
        gm = cls(mappa_id)
        for lv_str, dati_gr in dati.items():
            gm._livelli[int(lv_str)] = dizionario_a_griglia(dati_gr)
        if gm._livelli:
            gm._corrente = min(gm._livelli.keys())
        return gm

    def salva_nel_db(self):
        if self.mappa_id is None:
            return
        from database.db import esegui
        esegui(
            "UPDATE mappe SET dati_json = ? WHERE id = ?",
            (json.dumps(self.serializza(), ensure_ascii=False), self.mappa_id)
        )

    @classmethod
    def carica_dal_db(cls, mappa_id: int) -> "GestoreMultilivello | None":
        from database.modelli import carica_mappa
        dati = carica_mappa(mappa_id)
        if not dati:
            return None
        dati_json = dati["dati_json"]
        if not dati_json:
            gm = cls(mappa_id)
            gm.aggiungi_livello(0)
            return gm
        # Supporta sia il formato multilivello che quello legacy (solo griglia)
        if "meta" in dati_json:
            gm = cls(mappa_id)
            gm._livelli[0] = dizionario_a_griglia(dati_json)
            return gm
        return cls.deserializza(dati_json, mappa_id)
