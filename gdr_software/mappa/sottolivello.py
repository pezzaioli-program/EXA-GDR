"""
mappa/sottolivello.py — Gestione sottolivelli collegati agli oggetti
====================================================================
Ogni oggetto che supporta un sottolivello (castello, locanda, casa...)
ha un sottolivello_id salvato sulla cella della mappa world.
Il sottolivello è una mappa separata con dimensioni proprie,
tipi di pavimento e oggetti interni.
"""

import json
from database.db import esegui, leggi_uno, leggi_tutti

# Preset dimensioni sottolivelli
PRESET_DIMENSIONI = {
    "stanza":            (40,  30),
    "sotterranei_piccoli": (100, 80),
    "sotterranei_castello": (400, 300),
    "dungeon":           (650, 500),
    "grande_dungeon":    (1000, 800),
}

# Oggetti che possono avere sottolivello + preset di default
OGGETTI_CON_SOTTOLIVELLO = {
    "casa":       "stanza",
    "locanda":    "stanza",
    "villaggio":  "stanza",
    "castello":   "sotterranei_castello",
    "fattoria":   "stanza",
    # acquistabili dallo shop
    "castello_premium":  "sotterranei_castello",
    "locanda_premium":   "stanza",
    "casa_premium":      "stanza",
    "dungeon_prefab":    "dungeon",
}


def crea_sottolivello(mappa_id_parent: int, oggetto_id: str,
                      q_origine: int, r_origine: int,
                      preset: str = None) -> int:
    """
    Crea un nuovo sottolivello nel database e restituisce il suo id.
    """
    if preset is None:
        preset = OGGETTI_CON_SOTTOLIVELLO.get(oggetto_id, "stanza")

    colonne, righe = PRESET_DIMENSIONI.get(preset, (40, 30))

    cursore = esegui(
        """INSERT INTO sottolivelli
           (mappa_parent_id, oggetto_id, q_origine, r_origine,
            preset, colonne, righe, dati_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, '{}')""",
        (mappa_id_parent, oggetto_id, q_origine, r_origine,
         preset, colonne, righe)
    )
    return cursore.lastrowid


def carica_sottolivello(sottolivello_id: int) -> dict | None:
    return leggi_uno(
        "SELECT * FROM sottolivelli WHERE id=?", (sottolivello_id,))


def salva_dati_sottolivello(sottolivello_id: int, dati: dict):
    esegui(
        "UPDATE sottolivelli SET dati_json=? WHERE id=?",
        (json.dumps(dati, ensure_ascii=False), sottolivello_id)
    )


def sottolivelli_di_mappa(mappa_id: int) -> list:
    return leggi_tutti(
        "SELECT * FROM sottolivelli WHERE mappa_parent_id=?", (mappa_id,))


def inizializza_tabella_sottolivelli():
    """Chiamata da database/db.py in inizializza_db()."""
    esegui("""
        CREATE TABLE IF NOT EXISTS sottolivelli (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            mappa_parent_id  INTEGER NOT NULL,
            oggetto_id       TEXT    NOT NULL,
            q_origine        INTEGER NOT NULL,
            r_origine        INTEGER NOT NULL,
            preset           TEXT    NOT NULL DEFAULT 'stanza',
            colonne          INTEGER NOT NULL DEFAULT 40,
            righe            INTEGER NOT NULL DEFAULT 30,
            dati_json        TEXT    NOT NULL DEFAULT '{}',
            FOREIGN KEY (mappa_parent_id) REFERENCES mappe(id)
        )
    """)
    esegui("""
        CREATE TABLE IF NOT EXISTS chunk_mappa (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            mappa_id  INTEGER NOT NULL,
            cx        INTEGER NOT NULL,
            cy        INTEGER NOT NULL,
            dati_json TEXT    NOT NULL DEFAULT '{}',
            UNIQUE(mappa_id, cx, cy),
            FOREIGN KEY (mappa_id) REFERENCES mappe(id)
        )
    """)
