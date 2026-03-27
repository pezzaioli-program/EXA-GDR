"""
database/modelli.py — Funzioni di accesso ai dati (CRUD)
=========================================================
CRUD = Create, Read, Update, Delete — le 4 operazioni fondamentali su un DB.

Questo file contiene UNA funzione per ogni operazione su ogni tabella.
Non contiene logica di business (quella sta nei moduli specifici come auth/,
sessione/, ecc.) — sa solo come leggere e scrivere dati.

Perché separare modelli.py da db.py?
  db.py     → SA COME parlare con SQLite (connessione, query generiche)
  modelli.py → SA COSA c'è nel database (una funzione per ogni tabella)

Esempio: se vuoi sapere come funziona il login, guardi auth/registro.py.
Se vuoi sapere come si salva un utente nel DB, guardi modelli.py.
Le due cose sono separate.
"""

import json
from database.db import esegui, leggi_uno, leggi_tutti


# ─────────────────────────────────────────────────────────────────────────────
#  UTENTI
# ─────────────────────────────────────────────────────────────────────────────

def crea_utente(username: str, password_hash: str, ruolo: str) -> int:
    """
    Inserisce un nuovo utente nel database.
    Restituisce l'id del nuovo utente.

    password_hash: la password NON deve mai arrivare qui in chiaro.
    L'hashing viene fatto prima, in auth/registro.py.
    Questo file non sa nulla di bcrypt — sa solo salvare dati.
    """
    cursore = esegui(
        "INSERT INTO utenti (username, password_hash, ruolo) VALUES (?, ?, ?)",
        (username, password_hash, ruolo)
    )
    return cursore.lastrowid   # lastrowid = id assegnato automaticamente da SQLite


def trova_utente_per_username(username: str) -> dict | None:
    """
    Cerca un utente per username.
    Restituisce un dizionario con i dati, o None se non esiste.

    Usato dal login: "esiste questo username? se sì, dammi l'hash della password".
    """
    return leggi_uno(
        "SELECT * FROM utenti WHERE username = ?",
        (username,)
    )


def trova_utente_per_id(utente_id: int) -> dict | None:
    """Cerca un utente per id. Usato per caricare il profilo dopo il login."""
    return leggi_uno(
        "SELECT * FROM utenti WHERE id = ?",
        (utente_id,)
    )


def aggiorna_abbonamento(utente_id: int, attivo: bool):
    """Attiva o disattiva l'abbonamento di un DM."""
    esegui(
        "UPDATE utenti SET abbonamento_attivo = ? WHERE id = ?",
        (1 if attivo else 0, utente_id)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  MONDI
# ─────────────────────────────────────────────────────────────────────────────

def crea_mondo(dm_id: int, nome: str, lore: str = "", descrizione: str = "") -> int:
    """Crea un nuovo mondo. Restituisce l'id del mondo creato."""
    cursore = esegui(
        "INSERT INTO mondi (dm_id, nome, lore, descrizione) VALUES (?, ?, ?, ?)",
        (dm_id, nome, lore, descrizione)
    )
    return cursore.lastrowid


def mondi_del_dm(dm_id: int) -> list:
    """Restituisce tutti i mondi creati da un DM specifico."""
    return leggi_tutti(
        "SELECT * FROM mondi WHERE dm_id = ? ORDER BY data_creazione DESC",
        (dm_id,)
    )


def trova_mondo(mondo_id: int) -> dict | None:
    """Restituisce i dati di un mondo specifico."""
    return leggi_uno("SELECT * FROM mondi WHERE id = ?", (mondo_id,))


def aggiorna_mondo(mondo_id: int, nome: str, lore: str, descrizione: str):
    """Aggiorna le informazioni di un mondo."""
    esegui(
        "UPDATE mondi SET nome = ?, lore = ?, descrizione = ? WHERE id = ?",
        (nome, lore, descrizione, mondo_id)
    )


def elimina_mondo(mondo_id: int):
    """
    Elimina un mondo.

    ATTENZIONE: in un'implementazione completa dovresti eliminare anche
    tutte le mappe e le sessioni collegate prima di eliminare il mondo,
    altrimenti violi i foreign key. Per ora questa funzione è un placeholder.
    """
    esegui("DELETE FROM mondi WHERE id = ?", (mondo_id,))


# ─────────────────────────────────────────────────────────────────────────────
#  MAPPE
# ─────────────────────────────────────────────────────────────────────────────

def crea_mappa(mondo_id: int, nome: str, livello: int = 0) -> int:
    """
    Crea una nuova mappa vuota per un mondo.
    La griglia è inizialmente un dizionario vuoto serializzato come JSON.
    """
    cursore = esegui(
        "INSERT INTO mappe (mondo_id, nome, livello, dati_json) VALUES (?, ?, ?, ?)",
        (mondo_id, nome, livello, "{}")
    )
    return cursore.lastrowid


def salva_mappa(mappa_id: int, dati: dict):
    """
    Salva la griglia esagonale nel database.

    dati: il dizionario Python della griglia (prodotto da mappa/esporta.py)
    json.dumps() lo converte in stringa JSON per salvarlo nel campo TEXT del DB.

    Perché JSON e non un formato binario?
    JSON è leggibile da un essere umano — puoi aprire il database con
    un tool come "DB Browser for SQLite" e vedere i dati della mappa.
    Utile per debuggare.
    """
    esegui(
        """UPDATE mappe
           SET dati_json = ?, data_modifica = datetime('now')
           WHERE id = ?""",
        (json.dumps(dati, ensure_ascii=False), mappa_id)
    )


def carica_mappa(mappa_id: int) -> dict | None:
    """
    Carica una mappa dal database.
    Restituisce un dizionario con tutti i dati, inclusa la griglia.

    json.loads() riconverte la stringa JSON in dizionario Python.
    """
    riga = leggi_uno("SELECT * FROM mappe WHERE id = ?", (mappa_id,))
    if riga is None:
        return None
    # Converte dati_json da stringa a dizionario
    riga["dati_json"] = json.loads(riga["dati_json"])
    return riga


def mappe_del_mondo(mondo_id: int) -> list:
    """Restituisce tutte le mappe di un mondo, ordinate per livello."""
    return leggi_tutti(
        "SELECT id, nome, livello, data_modifica FROM mappe WHERE mondo_id = ? ORDER BY livello",
        (mondo_id,)
    )


def duplica_mappa(mappa_id: int, nuovo_nome: str) -> int:
    """
    Crea una copia identica di una mappa con un nuovo nome.
    Utile per duplicare mappe prefab acquistate (il DM modifica la copia,
    non l'originale — come richiesto dal PDR §16).
    """
    originale = carica_mappa(mappa_id)
    if originale is None:
        raise ValueError(f"Mappa {mappa_id} non trovata")

    nuovo_id = crea_mappa(originale["mondo_id"], nuovo_nome, originale["livello"])
    salva_mappa(nuovo_id, originale["dati_json"])
    return nuovo_id


# ─────────────────────────────────────────────────────────────────────────────
#  SESSIONI
# ─────────────────────────────────────────────────────────────────────────────

def crea_sessione(mondo_id: int, mappa_id: int = None) -> int:
    """Crea una nuova sessione (inizialmente chiusa)."""
    cursore = esegui(
        "INSERT INTO sessioni (mondo_id, mappa_id) VALUES (?, ?)",
        (mondo_id, mappa_id)
    )
    return cursore.lastrowid


def apri_sessione(sessione_id: int):
    """Segna la sessione come aperta — il DM ha avviato il gioco."""
    esegui(
        "UPDATE sessioni SET stato = 'aperta', data_inizio = datetime('now') WHERE id = ?",
        (sessione_id,)
    )


def chiudi_sessione(sessione_id: int):
    """Segna la sessione come chiusa e registra l'orario di fine."""
    esegui(
        "UPDATE sessioni SET stato = 'chiusa', data_fine = datetime('now') WHERE id = ?",
        (sessione_id,)
    )


def sessioni_del_mondo(mondo_id: int) -> list:
    """Restituisce tutte le sessioni di un mondo, dalla più recente."""
    return leggi_tutti(
        "SELECT * FROM sessioni WHERE mondo_id = ? ORDER BY data_inizio DESC",
        (mondo_id,)
    )


def sessioni_aperte() -> list:
    """
    Restituisce tutte le sessioni attualmente aperte.
    Usato dalla dashboard del Player per mostrare le sessioni disponibili.
    """
    return leggi_tutti("SELECT * FROM sessioni WHERE stato = 'aperta'")


# ─────────────────────────────────────────────────────────────────────────────
#  PERSONAGGI
# ─────────────────────────────────────────────────────────────────────────────

def crea_personaggio(utente_id: int, nome: str, classe: str,
                     statistiche: dict = None) -> int:
    """
    Crea una nuova scheda personaggio.
    Le statistiche default vengono impostate se non specificate.
    """
    stats_default = {
        "forza": 10, "destrezza": 10, "costituzione": 10,
        "intelligenza": 10, "saggezza": 10, "carisma": 10,
        "punti_ferita": 10, "pf_massimi": 10,
        "velocita": 6,
    }
    stats = statistiche or stats_default

    cursore = esegui(
        """INSERT INTO personaggi (utente_id, nome, classe, statistiche_json)
           VALUES (?, ?, ?, ?)""",
        (utente_id, nome, classe, json.dumps(stats))
    )
    return cursore.lastrowid


def carica_personaggio(personaggio_id: int) -> dict | None:
    """Carica una scheda personaggio con le statistiche deserializzate."""
    riga = leggi_uno("SELECT * FROM personaggi WHERE id = ?", (personaggio_id,))
    if riga is None:
        return None
    riga["statistiche_json"]  = json.loads(riga["statistiche_json"])
    riga["inventario_json"]   = json.loads(riga["inventario_json"])
    return riga


def personaggi_del_player(utente_id: int) -> list:
    """Restituisce tutti i personaggi di un Player."""
    return leggi_tutti(
        "SELECT id, nome, classe, livello FROM personaggi WHERE utente_id = ?",
        (utente_id,)
    )


def salva_personaggio(personaggio_id: int, statistiche: dict,
                      inventario: list, note: str):
    """Aggiorna la scheda personaggio nel database."""
    esegui(
        """UPDATE personaggi
           SET statistiche_json = ?, inventario_json = ?, note = ?
           WHERE id = ?""",
        (json.dumps(statistiche), json.dumps(inventario), note, personaggio_id)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PARTECIPANTI
# ─────────────────────────────────────────────────────────────────────────────

def aggiungi_partecipante(sessione_id: int, utente_id: int, personaggio_id: int):
    """Registra un Player come partecipante a una sessione."""
    esegui(
        """INSERT OR IGNORE INTO partecipanti (sessione_id, utente_id, personaggio_id)
           VALUES (?, ?, ?)""",
        (sessione_id, utente_id, personaggio_id)
    )
    # INSERT OR IGNORE: se il Player è già registrato, non fa nulla
    # (evita duplicati senza andare in errore)


def partecipanti_sessione(sessione_id: int) -> list:
    """
    Restituisce i partecipanti di una sessione con username e nome personaggio.
    Usa una JOIN per combinare dati da tre tabelle in una sola query.

    JOIN: unisce due tabelle usando un campo in comune.
    "partecipanti JOIN utenti ON partecipanti.utente_id = utenti.id"
    significa: "per ogni partecipante, prendi anche i dati dell'utente corrispondente"
    """
    return leggi_tutti(
        """SELECT p.utente_id, u.username, per.nome AS nome_personaggio
           FROM partecipanti p
           JOIN utenti      u   ON p.utente_id      = u.id
           JOIN personaggi  per ON p.personaggio_id = per.id
           WHERE p.sessione_id = ?""",
        (sessione_id,)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ACQUISTI
# ─────────────────────────────────────────────────────────────────────────────

def registra_acquisto(utente_id: int, asset_id: str, tipo_asset: str):
    """Registra un acquisto nello shop."""
    esegui(
        "INSERT INTO acquisti (utente_id, asset_id, tipo_asset) VALUES (?, ?, ?)",
        (utente_id, asset_id, tipo_asset)
    )


def ha_acquistato(utente_id: int, asset_id: str) -> bool:
    """
    Controlla se un utente ha già acquistato un asset.
    Restituisce True o False.

    Usato ovunque nel codice per sbloccare contenuti acquistati.
    """
    riga = leggi_uno(
        "SELECT id FROM acquisti WHERE utente_id = ? AND asset_id = ?",
        (utente_id, asset_id)
    )
    return riga is not None   # se ha trovato una riga = ha acquistato


def acquisti_utente(utente_id: int) -> list:
    """Restituisce tutti gli acquisti di un utente."""
    return leggi_tutti(
        "SELECT asset_id, tipo_asset, data_acquisto FROM acquisti WHERE utente_id = ?",
        (utente_id,)
    )

"""
AGGIUNTE A database/modelli.py
================================
Incolla queste funzioni alla FINE del file modelli.py
"""

# ─────────────────────────────────────────────────────────────────────────────
#  TILESET
# ─────────────────────────────────────────────────────────────────────────────

def ottieni_tileset_attivo(utente_id: int) -> str:
    """
    Restituisce l'id del tileset attualmente attivo per l'utente.
    Se l'utente non ha mai scelto, usa 'tileset_base' (gratuito).
    """
    riga = leggi_uno(
        "SELECT tileset_id FROM tileset_attivi WHERE utente_id = ?",
        (utente_id,)
    )
    return riga["tileset_id"] if riga else "tileset_base"


def imposta_tileset_attivo(utente_id: int, tileset_id: str):
    """
    Salva il tileset scelto dall'utente nel database.
    Usa INSERT OR REPLACE: se esiste già un record lo aggiorna,
    altrimenti lo inserisce.
    """
    esegui(
        """INSERT OR REPLACE INTO tileset_attivi (utente_id, tileset_id)
           VALUES (?, ?)""",
        (utente_id, tileset_id)
    )


# ─────────────────────────────────────────────────────────────────────────────
#  OGGETTI ESPLORABILI — sottolivelli acquistati
# ─────────────────────────────────────────────────────────────────────────────

def crea_sottolivello_esplorabile(mappa_id: int,
                                  oggetto_id: str,
                                  q_origine: int,
                                  r_origine: int,
                                  preset: str) -> int:
    """
    Crea un sottolivello vuoto per un oggetto esplorabile appena piazzato.
    Restituisce l'id del nuovo sottolivello.

    Questa funzione viene chiamata automaticamente quando il DM piazza
    un oggetto esplorabile sulla mappa (es. casa_esplorabile).
    Il sottolivello è vuoto — il DM lo disegna aprendo l'editor.
    """
    from config import PRESET_DIMENSIONI_SOTTOLIVELLO

    colonne, righe = PRESET_DIMENSIONI_SOTTOLIVELLO.get(preset, (40, 30))

    cursore = esegui(
        """INSERT INTO sottolivelli
           (mappa_parent_id, oggetto_id, q_origine, r_origine,
            preset, colonne, righe, dati_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, '{}')""",
        (mappa_id, oggetto_id, q_origine, r_origine,
         preset, colonne, righe)
    )
    return cursore.lastrowid

