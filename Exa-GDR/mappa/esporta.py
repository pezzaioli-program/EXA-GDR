"""
mappa/esporta.py — Serializzazione della griglia esagonale
===========================================================
Questo file sa come convertire una Griglia Python in JSON (per salvarla)
e come ricostruire una Griglia da JSON (per caricarla).

Responsabilità UNICA: traduzione Griglia ↔ JSON.
Non sa nulla di database (quello è database/modelli.py).
Non sa nulla di come si disegna (quello è map.py).

Perché un file separato e non metodi dentro Griglia?
Perché la serializzazione è una responsabilità esterna alla Griglia.
La Griglia sa disegnarsi e gestire gli esagoni — non deve sapere
anche come salvarsi su disco. Se domani vuoi aggiungere un formato
di esportazione diverso (es. XML, binario compresso), aggiungi
funzioni qui senza toccare map.py.
"""

import json
from config import OGGETTI
from mappa.map import Griglia, Esagono


# ─────────────────────────────────────────────────────────────────────────────
#  SERIALIZZAZIONE — Griglia → dizionario Python → JSON
# ─────────────────────────────────────────────────────────────────────────────

def griglia_a_dizionario(griglia: Griglia) -> dict:
    """
    Converte una Griglia in un dizionario Python puro.
    Questo dizionario può poi essere convertito in JSON con json.dumps().

    Struttura del risultato:
    {
        "meta": {
            "colonne": 15,
            "righe": 12,
            "dimensione": 40,
            "offset_x": 180,
            "offset_y": 40
        },
        "celle": {
            "0,0": { "terreno": "pianura", "visibile": true, ... },
            "1,0": { ... },
            ...
        }
    }

    Perché "meta" separato dalle celle?
    Perché quando ricarichiamo la griglia, dobbiamo sapere PRIMA
    le dimensioni per costruire l'oggetto Griglia — solo dopo
    possiamo popolare le celle. Tenere i metadati separati rende
    più chiaro l'ordine delle operazioni.

    Perché le chiavi delle celle sono "q,r" (stringa) e non (q,r) (tupla)?
    JSON non supporta tuple come chiavi dei dizionari — accetta solo stringhe.
    Convertiamo (3, 2) in "3,2" per salvare, e "3,2" in (3, 2) per ricaricare.
    """
    celle_serializzate = {}

    for (q, r), esagono in griglia.celle.items():
        chiave = f"{q},{r}"   # (3, 2) → "3,2"
        celle_serializzate[chiave] = _esagono_a_dizionario(esagono)

    return {
        "meta": {
            "colonne":   griglia.colonne,
            "righe":     griglia.righe,
            "dimensione": griglia.dimensione,
            "offset_x":  griglia.offset_x,
            "offset_y":  griglia.offset_y,
        },
        "celle": celle_serializzate,
    }


def _esagono_a_dizionario(esagono: Esagono) -> dict:
    """
    Converte un singolo Esagono in dizionario.
    Funzione privata (prefisso _) — usata solo da griglia_a_dizionario.

    Il punto critico è self.oggetti: contiene istanze con riferimenti
    agli oggetti di OGGETTI. Salviamo SOLO l'id, non tutta la definizione.
    """
    return {
        "terreno":  esagono.terreno,
        "visibile": esagono.visibile,
        "evento":   esagono.evento,
        "oggetti":  _oggetti_a_dizionario(esagono.oggetti),
    }
    # Nota: non salviamo q e r perché sono già nella chiave del dizionario celle.
    # Salvarli di nuovo sarebbe ridondante.


def _oggetti_a_dizionario(oggetti: dict) -> dict:
    """
    Converte il dizionario self.oggetti di un Esagono in formato serializzabile.

    Struttura input (oggetti in memoria):
        {
            "struttura": {
                "def": OGGETTI["castello"],   ← riferimento Python, NON serializzabile
                "origine": (3, 2),            ← tupla, NON serializzabile in JSON
                "rotazione": 1
            },
            "viabilita": None,
            "mobile": []
        }

    Struttura output (serializzata):
        {
            "struttura": {
                "id_oggetto": "castello",   ← solo l'id, stringa serializzabile
                "origine": [3, 2],          ← lista invece di tupla
                "rotazione": 1
            },
            "viabilita": None,
            "mobile": []
        }
    """
    def serializza_istanza(istanza: dict) -> dict:
        """Converte una singola istanza oggetto in formato JSON-compatibile."""
        return {
            "id_oggetto": istanza["def"]["id"],          # solo l'id
            "origine":    list(istanza["origine"]),      # tupla → lista
            "rotazione":  istanza["rotazione"],
        }

    struttura = None
    if oggetti.get("struttura"):
        struttura = serializza_istanza(oggetti["struttura"])

    viabilita = None
    if oggetti.get("viabilita"):
        viabilita = serializza_istanza(oggetti["viabilita"])

    mobile = [serializza_istanza(m) for m in oggetti.get("mobile", [])]

    return {
        "struttura": struttura,
        "viabilita": viabilita,
        "mobile":    mobile,
    }


def griglia_a_json(griglia: Griglia) -> str:
    """
    Converte una Griglia direttamente in stringa JSON.
    Questa è la funzione che viene chiamata da database/modelli.py.

    ensure_ascii=False: permette caratteri italiani (è, à...) senza escape.
    indent=None: nessuna indentazione → JSON compatto, meno spazio nel DB.
                 Usa indent=2 se vuoi leggere il JSON a occhio nudo (debug).
    """
    dizionario = griglia_a_dizionario(griglia)
    return json.dumps(dizionario, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
#  DESERIALIZZAZIONE — JSON → dizionario Python → Griglia
# ─────────────────────────────────────────────────────────────────────────────

def json_a_griglia(json_str: str) -> Griglia:
    """
    Ricostruisce una Griglia da una stringa JSON.
    È il processo inverso di griglia_a_json().

    Flusso:
        1. json.loads() → dizionario Python
        2. Legge i metadati → crea oggetto Griglia vuoto
        3. Per ogni cella nel JSON → ricostruisce l'Esagono
        4. Reinserisce gli Esagoni nella Griglia
    """
    dati = json.loads(json_str)
    return dizionario_a_griglia(dati)


def dizionario_a_griglia(dati: dict) -> Griglia:
    """
    Ricostruisce una Griglia da un dizionario Python.
    Separata da json_a_griglia per permettere test più facili
    (puoi testare con dizionari senza passare da JSON).
    """
    meta = dati["meta"]

    # Crea la Griglia con i parametri originali
    # _costruisci() viene chiamato da __init__ e popola celle con Esagoni vuoti.
    # Subito dopo, sovrascriviamo ogni cella con i dati salvati.
    griglia = Griglia(
        colonne=meta["colonne"],
        righe=meta["righe"],
        dimensione=meta["dimensione"],
        offset_x=meta["offset_x"],
        offset_y=meta["offset_y"],
    )

    # Ripopola ogni cella con i dati salvati
    for chiave, dati_cella in dati["celle"].items():
        # Riconverti "3,2" → (3, 2)
        q, r = map(int, chiave.split(","))

        if (q, r) not in griglia.celle:
            # Cella fuori dai limiti della griglia (non dovrebbe succedere,
            # ma meglio gestirlo che crashare silenziosamente)
            continue

        esagono = griglia.celle[(q, r)]
        _popola_esagono(esagono, dati_cella)

    return griglia


def _popola_esagono(esagono: Esagono, dati: dict):
    """
    Ripristina i dati di un Esagono dal dizionario salvato.
    Modifica l'esagono in-place (direttamente sull'oggetto).
    """
    esagono.terreno  = dati.get("terreno", "vuoto")
    esagono.visibile = dati.get("visibile", True)
    esagono.evento   = dati.get("evento", None)
    esagono.oggetti  = _dizionario_a_oggetti(dati.get("oggetti", {}))


def _dizionario_a_oggetti(dati_oggetti: dict) -> dict:
    """
    Ricostruisce il dizionario self.oggetti di un Esagono.
    È il processo inverso di _oggetti_a_dizionario().

    Il punto chiave: da "id_oggetto": "castello" ricostruiamo
    il riferimento completo a OGGETTI["castello"].
    Se l'id non esiste più in OGGETTI (es. oggetto rimosso in un aggiornamento),
    logghiamo un avviso e saltiamo — non crashiamo.
    """
    def deserializza_istanza(dati_ist: dict) -> dict | None:
        """Ricostruisce una singola istanza da dizionario salvato."""
        id_oggetto = dati_ist.get("id_oggetto")

        if id_oggetto not in OGGETTI:
            print(f"[WARN] Oggetto '{id_oggetto}' non trovato in OGGETTI — saltato.")
            return None

        return {
            "def":       OGGETTI[id_oggetto],          # riferimento alla definizione
            "origine":   tuple(dati_ist["origine"]),   # lista → tupla
            "rotazione": dati_ist["rotazione"],
        }

    # Struttura
    struttura = None
    if dati_oggetti.get("struttura"):
        struttura = deserializza_istanza(dati_oggetti["struttura"])

    # Viabilità
    viabilita = None
    if dati_oggetti.get("viabilita"):
        viabilita = deserializza_istanza(dati_oggetti["viabilita"])

    # Mobile — lista, filtriamo i None (oggetti non trovati)
    mobile = []
    for m in dati_oggetti.get("mobile", []):
        istanza = deserializza_istanza(m)
        if istanza:
            mobile.append(istanza)

    return {
        "struttura": struttura,
        "viabilita": viabilita,
        "mobile":    mobile,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  FUNZIONI DI ALTO LIVELLO — collegano esporta.py al database
# ─────────────────────────────────────────────────────────────────────────────

def salva_griglia_nel_db(mappa_id: int, griglia: Griglia):
    """
    Serializza la Griglia e la salva nel database.

    Questa funzione è il "ponte" tra map.py e database/modelli.py:
    - map.py non sa nulla del database
    - modelli.py non sa nulla della Griglia
    - esporta.py conosce entrambi e li connette
    """
    from database.modelli import salva_mappa
    json_str = griglia_a_json(griglia)
    # salva_mappa si aspetta un dizionario, non una stringa JSON.
    # Passiamo già il dizionario per evitare una doppia conversione.
    from database.modelli import esegui
    from database.db import esegui as db_esegui
    db_esegui(
        "UPDATE mappe SET dati_json = ?, data_modifica = datetime('now') WHERE id = ?",
        (json_str, mappa_id)
    )
    print(f"[MAPPA] Salvata mappa id={mappa_id}")


def carica_griglia_dal_db(mappa_id: int) -> Griglia | None:
    """
    Carica una Griglia dal database e la deserializza.
    Restituisce None se la mappa non esiste.
    """
    from database.modelli import carica_mappa
    dati = carica_mappa(mappa_id)

    if dati is None:
        print(f"[MAPPA] Mappa id={mappa_id} non trovata nel database.")
        return None

    # dati["dati_json"] è già un dizionario (carica_mappa fa json.loads internamente)
    griglia = dizionario_a_griglia(dati["dati_json"])
    print(f"[MAPPA] Caricata mappa id={mappa_id} ({griglia})")
    return griglia
