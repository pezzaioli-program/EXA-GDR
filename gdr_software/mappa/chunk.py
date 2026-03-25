"""
mappa/chunk.py — Chunk system per mappe potenzialmente infinite
===============================================================
La mappa world è divisa in chunk di CHUNK_SIZE×CHUNK_SIZE esagoni.
Solo i chunk nella viewport corrente vengono caricati in memoria.
Gli altri vengono scaricati e salvati nel DB quando escono dalla vista.

Coordinate chunk: (cx, cy) dove cx = q // CHUNK_SIZE, cy = r // CHUNK_SIZE
Coordinate locali: (lq, lr) dove lq = q % CHUNK_SIZE, lr = r % CHUNK_SIZE
Coordinate globali: (q, r) = (cx * CHUNK_SIZE + lq, cy * CHUNK_SIZE + lr)
"""

import json
import math
from mappa.map import Esagono

CHUNK_SIZE = 16   # esagoni per lato di ogni chunk


class Chunk:
    """Un blocco 32×32 di esagoni."""

    def __init__(self, cx: int, cy: int):
        self.cx = cx
        self.cy = cy
        self.celle: dict[tuple, Esagono] = {}
        self.modificato = False
        self._costruisci()

    def _costruisci(self):
        for lr in range(CHUNK_SIZE):
            for lq in range(CHUNK_SIZE):
                q = self.cx * CHUNK_SIZE + lq
                r = self.cy * CHUNK_SIZE + lr
                self.celle[(q, r)] = Esagono(q, r)

    def serializza(self) -> dict:
        celle_s = {}
        for (q, r), e in self.celle.items():
            # Salva solo celle non default per risparmiare spazio
            if (e.terreno != "vuoto" or e.evento or
                    any(v for v in e.oggetti.values() if v)):
                celle_s[f"{q},{r}"] = {
                    "terreno":  e.terreno,
                    "visibile": e.visibile,
                    "evento":   e.evento,
                    "oggetti":  _oggetti_a_dict(e.oggetti),
                    "sottolivello_id": getattr(e, "sottolivello_id", None),
                }
        return {"cx": self.cx, "cy": self.cy, "celle": celle_s}

    @classmethod
    def deserializza(cls, dati: dict) -> "Chunk":
        from config import OGGETTI
        chunk = cls(dati["cx"], dati["cy"])
        for chiave, dc in dati.get("celle", {}).items():
            q, r = map(int, chiave.split(","))
            e = chunk.celle.get((q, r))
            if not e:
                continue
            e.terreno  = dc.get("terreno", "vuoto")
            e.visibile = dc.get("visibile", True)
            e.evento   = dc.get("evento")
            e.oggetti  = _dict_a_oggetti(dc.get("oggetti", {}))
            e.sottolivello_id = dc.get("sottolivello_id")
        return chunk


def _oggetti_a_dict(oggetti: dict) -> dict:
    def ser(ist):
        if not ist:
            return None
        return {"id_oggetto": ist["def"]["id"],
                "origine": list(ist["origine"]),
                "rotazione": ist["rotazione"]}
    return {
        "struttura": ser(oggetti.get("struttura")),
        "viabilita": ser(oggetti.get("viabilita")),
        "mobile":    [ser(m) for m in oggetti.get("mobile", []) if m],
    }


def _dict_a_oggetti(d: dict) -> dict:
    from config import OGGETTI, OGGETTI_INTERNI
    tutti = {**OGGETTI, **OGGETTI_INTERNI}

    def des(x):
        if not x:
            return None
        oid = x.get("id_oggetto")
        if oid not in tutti:
            return None
        return {"def": tutti[oid],
                "origine": tuple(x["origine"]),
                "rotazione": x["rotazione"]}

    return {
        "struttura": des(d.get("struttura")),
        "viabilita": des(d.get("viabilita")),
        "mobile":    [des(m) for m in d.get("mobile", []) if m],
    }


class GestoreChunk:
    """
    Gestisce il caricamento/scaricamento dei chunk in base alla viewport.
    Mantiene in memoria solo i chunk visibili + un bordo di 1 chunk.
    """

    def __init__(self, mappa_id: int, e_sottolivello: bool = False):
        self.mappa_id        = mappa_id
        self.e_sottolivello  = e_sottolivello
        self._chunk_caricati: dict[tuple, Chunk] = {}   # (cx,cy) → Chunk

    # ── Accesso celle ─────────────────────────────────────────────────────────

    def ottieni_cella(self, q: int, r: int) -> Esagono | None:
        cx, cy = q // CHUNK_SIZE, r // CHUNK_SIZE
        chunk  = self._chunk_caricati.get((cx, cy))
        if chunk is None:
            chunk = self._carica_chunk(cx, cy)
        return chunk.celle.get((q, r))

    def segna_modificato(self, q: int, r: int):
        cx, cy = q // CHUNK_SIZE, r // CHUNK_SIZE
        chunk  = self._chunk_caricati.get((cx, cy))
        if chunk:
            chunk.modificato = True

    # ── Chunk nella viewport ──────────────────────────────────────────────────

    def aggiorna_viewport(self, q_min: int, r_min: int,
                          q_max: int, r_max: int):
        """Carica i chunk necessari, scarica quelli fuori dalla viewport."""
        cx_min = max(0, q_min // CHUNK_SIZE - 1)
        cy_min = max(0, r_min // CHUNK_SIZE - 1)
        cx_max = q_max // CHUNK_SIZE + 1
        cy_max = r_max // CHUNK_SIZE + 1

        necessari = {(cx, cy)
                     for cx in range(cx_min, cx_max + 1)
                     for cy in range(cy_min, cy_max + 1)}

        # Scarica chunk non più necessari
        da_rimuovere = set(self._chunk_caricati) - necessari
        for chiave in da_rimuovere:
            chunk = self._chunk_caricati.pop(chiave)
            if chunk.modificato:
                self._salva_chunk(chunk)

        # Carica chunk mancanti
        for chiave in necessari:
            if chiave not in self._chunk_caricati:
                self._carica_chunk(*chiave)

    def celle_visibili(self) -> dict:
        """Restituisce tutte le celle dei chunk caricati."""
        risultato = {}
        for chunk in self._chunk_caricati.values():
            risultato.update(chunk.celle)
        return risultato

    # ── Persistenza ───────────────────────────────────────────────────────────

    def _carica_chunk(self, cx: int, cy: int) -> Chunk:
        from database.db import leggi_uno
        riga = leggi_uno(
            "SELECT dati_json FROM chunk_mappa WHERE mappa_id=? AND cx=? AND cy=?",
            (self.mappa_id, cx, cy)
        )
        if riga:
            chunk = Chunk.deserializza(json.loads(riga["dati_json"]))
        else:
            chunk = Chunk(cx, cy)
        self._chunk_caricati[(cx, cy)] = chunk
        return chunk

    def _salva_chunk(self, chunk: Chunk):
        from database.db import esegui
        dati = json.dumps(chunk.serializza(), ensure_ascii=False)
        esegui(
            """INSERT OR REPLACE INTO chunk_mappa
               (mappa_id, cx, cy, dati_json)
               VALUES (?, ?, ?, ?)""",
            (self.mappa_id, chunk.cx, chunk.cy, dati)
        )
        chunk.modificato = False

    def salva_tutto(self):
        """Salva tutti i chunk modificati."""
        for chunk in self._chunk_caricati.values():
            if chunk.modificato:
                self._salva_chunk(chunk)

    def scarica_tutto(self):
        """Salva e svuota tutti i chunk."""
        self.salva_tutto()
        self._chunk_caricati.clear()
