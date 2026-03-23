"""
database/db.py — Connessione e operazioni SQLite
=================================================
Questo file ha UNA responsabilità: parlare con il database.
Tutto il resto del progetto usa le funzioni di questo file
per leggere e scrivere dati — non accede mai direttamente al DB.

Perché questo livello di separazione?
Se un giorno vuoi passare da SQLite a PostgreSQL, modifichi
solo questo file. Il resto del codice non sa (e non deve sapere)
che tipo di database c'è sotto.
"""

import sqlite3
import os
from config import DB_PATH


# ─────────────────────────────────────────────────────────────────────────────
#  CONNESSIONE
# ─────────────────────────────────────────────────────────────────────────────

def ottieni_connessione() -> sqlite3.Connection:
    """
    Apre e restituisce una connessione al database SQLite.

    Perché non teniamo una connessione aperta sempre?
    SQLite non gestisce bene connessioni condivise tra thread diversi.
    Aprire una connessione per ogni operazione (e chiuderla subito dopo)
    è il pattern più sicuro per un'app desktop.

    detect_types=sqlite3.PARSE_DECLTYPES permette a SQLite di convertire
    automaticamente le date da stringa a oggetto Python datetime.

    check_same_thread=False: necessario perché PyQt e il loop WebSocket
    girano su thread diversi ma possono accedere al DB.
    """
    # Assicuriamoci che la cartella database/ esista prima di creare il file
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,
    )

    # row_factory: fa sì che ogni riga restituita sia un dizionario
    # invece che una tupla. Senza questo:  riga[0], riga[1]...
    # Con questo:  riga["username"], riga["ruolo"] — molto più leggibile.
    conn.row_factory = sqlite3.Row

    # Attiva i foreign key — SQLite li ignora di default.
    # Con questa riga, se provi a inserire una sessione con un mondo_id
    # che non esiste, SQLite ti blocca invece di lasciartelo fare silenziosamente.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ─────────────────────────────────────────────────────────────────────────────
#  FUNZIONI DI UTILITÀ
# ─────────────────────────────────────────────────────────────────────────────

def esegui(query: str, parametri: tuple = ()) -> sqlite3.Cursor:
    """
    Esegue una query che MODIFICA dati (INSERT, UPDATE, DELETE).
    Apre la connessione, esegue, fa il commit e chiude.

    Il "commit" è fondamentale: senza di esso le modifiche rimangono
    in sospeso nella memoria e non vengono scritte sul disco.
    Pensa al commit come al tasto "Salva" — senza di esso perdi tutto
    se il programma crasha.

    Restituisce il cursore, utile per leggere lastrowid
    (l'id della riga appena inserita).
    """
    with ottieni_connessione() as conn:
        cursore = conn.execute(query, parametri)
        conn.commit()
        return cursore


def leggi_uno(query: str, parametri: tuple = ()):
    """
    Esegue una query SELECT e restituisce UNA SOLA riga.
    Restituisce None se non trova nulla.

    Quando usarla: quando cerchi un elemento specifico per id o username.
    Esempio: "dammi l'utente con id = 5"
    """
    with ottieni_connessione() as conn:
        cursore = conn.execute(query, parametri)
        riga = cursore.fetchone()
        # fetchone() restituisce la prima riga, o None se non ce ne sono
        return dict(riga) if riga else None


def leggi_tutti(query: str, parametri: tuple = ()) -> list:
    """
    Esegue una query SELECT e restituisce TUTTE le righe come lista di dizionari.
    Restituisce lista vuota [] se non trova nulla.

    Quando usarla: quando vuoi una lista di elementi.
    Esempio: "dammi tutte le sessioni di questo mondo"
    """
    with ottieni_connessione() as conn:
        cursore = conn.execute(query, parametri)
        righe = cursore.fetchall()
        return [dict(r) for r in righe]


# ─────────────────────────────────────────────────────────────────────────────
#  INIZIALIZZAZIONE — crea le tabelle se non esistono
# ─────────────────────────────────────────────────────────────────────────────

def inizializza_db():
    """
    Crea tutte le tabelle del database se non esistono già.
    Viene chiamata una volta sola all'avvio del programma (da main.py).

    "IF NOT EXISTS" è fondamentale: senza di esso, al secondo avvio
    SQLite cercherebbe di creare tabelle già esistenti e andrebbe in errore.
    Con IF NOT EXISTS: "crea solo se non c'è già" — idempotente.

    Idempotente significa: puoi chiamarlo 100 volte, il risultato è sempre
    lo stesso. È una proprietà desiderabile per le operazioni di setup.
    """
    with ottieni_connessione() as conn:

        # ── UTENTI ────────────────────────────────────────────────────────────
        # Ogni persona che usa il software è un utente.
        # ruolo: "player" o "dm"
        # abbonamento_attivo: 0 = no, 1 = sì (SQLite non ha booleani nativi)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                username            TEXT    NOT NULL UNIQUE,
                password_hash       TEXT    NOT NULL,
                ruolo               TEXT    NOT NULL CHECK(ruolo IN ('player', 'dm')),
                abbonamento_attivo  INTEGER NOT NULL DEFAULT 0,
                data_creazione      TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # AUTOINCREMENT: SQLite assegna automaticamente id 1, 2, 3...
        # UNIQUE: due utenti non possono avere lo stesso username
        # CHECK: SQLite rifiuta qualsiasi valore che non sia 'player' o 'dm'
        # DEFAULT: se non specifichi la data, usa quella corrente

        # ── MONDI ─────────────────────────────────────────────────────────────
        # Un mondo appartiene a un DM e contiene mappe e sessioni.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mondi (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                dm_id           INTEGER NOT NULL,
                nome            TEXT    NOT NULL,
                lore            TEXT    DEFAULT '',
                descrizione     TEXT    DEFAULT '',
                data_creazione  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (dm_id) REFERENCES utenti(id)
            )
        """)
        # FOREIGN KEY: dm_id deve corrispondere a un id esistente in utenti.
        # Se provi a inserire un mondo con dm_id=999 e l'utente 999 non esiste,
        # SQLite ti blocca. Questo mantiene la coerenza dei dati.

        # ── MAPPE ─────────────────────────────────────────────────────────────
        # Ogni mondo può avere più mappe (diverse aree geografiche).
        # dati_json: la griglia esagonale serializzata come JSON
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mappe (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mondo_id        INTEGER NOT NULL,
                nome            TEXT    NOT NULL,
                livello         INTEGER NOT NULL DEFAULT 0,
                dati_json       TEXT    NOT NULL DEFAULT '{}',
                data_modifica   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (mondo_id) REFERENCES mondi(id)
            )
        """)
        # livello: 0 = piano terra, 1 = primo piano, -1 = sotterraneo

        # ── SESSIONI ──────────────────────────────────────────────────────────
        # Una sessione è un'istanza di gioco in tempo reale.
        # stato: "aperta" quando il DM la avvia, "chiusa" quando finisce
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessioni (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mondo_id        INTEGER NOT NULL,
                mappa_id        INTEGER,
                stato           TEXT    NOT NULL DEFAULT 'chiusa'
                                        CHECK(stato IN ('aperta', 'chiusa')),
                data_inizio     TEXT    NOT NULL DEFAULT (datetime('now')),
                data_fine       TEXT,
                FOREIGN KEY (mondo_id) REFERENCES mondi(id),
                FOREIGN KEY (mappa_id) REFERENCES mappe(id)
            )
        """)

        # ── PERSONAGGI ────────────────────────────────────────────────────────
        # La scheda personaggio di ogni Player.
        # statistiche_json e inventario_json: dizionari Python serializzati
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personaggi (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                utente_id           INTEGER NOT NULL,
                nome                TEXT    NOT NULL,
                classe              TEXT    NOT NULL DEFAULT '',
                livello             INTEGER NOT NULL DEFAULT 1,
                statistiche_json    TEXT    NOT NULL DEFAULT '{}',
                inventario_json     TEXT    NOT NULL DEFAULT '[]',
                note                TEXT    NOT NULL DEFAULT '',
                data_creazione      TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (utente_id) REFERENCES utenti(id)
            )
        """)

        # ── PARTECIPANTI ──────────────────────────────────────────────────────
        # Tabella di collegamento: chi partecipa a quale sessione con quale personaggio.
        # È una tabella "ponte" tra sessioni e personaggi.
        # Esempio: Frodo (personaggio_id=2) partecipa alla sessione 1.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partecipanti (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                sessione_id     INTEGER NOT NULL,
                utente_id       INTEGER NOT NULL,
                personaggio_id  INTEGER NOT NULL,
                FOREIGN KEY (sessione_id)    REFERENCES sessioni(id),
                FOREIGN KEY (utente_id)      REFERENCES utenti(id),
                FOREIGN KEY (personaggio_id) REFERENCES personaggi(id)
            )
        """)

        # ── NPC ───────────────────────────────────────────────────────────────
        # Personaggi non giocanti controllati dal DM.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS npc (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                mondo_id        INTEGER NOT NULL,
                nome            TEXT    NOT NULL,
                tipo            TEXT    NOT NULL DEFAULT 'npc'
                                        CHECK(tipo IN ('npc', 'mob')),
                statistiche_json TEXT   NOT NULL DEFAULT '{}',
                png_path        TEXT,
                FOREIGN KEY (mondo_id) REFERENCES mondi(id)
            )
        """)
        # tipo: "npc" = alleato/neutro, "mob" = nemico

        # ── ACQUISTI ──────────────────────────────────────────────────────────
        # Storico degli acquisti nello shop.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS acquisti (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                utente_id       INTEGER NOT NULL,
                asset_id        TEXT    NOT NULL,
                tipo_asset      TEXT    NOT NULL,
                data_acquisto   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (utente_id) REFERENCES utenti(id)
            )
        """)
        # asset_id: identificatore dell'asset acquistato (es. "castello_gold")
        # tipo_asset: "skin_personaggio", "skin_dado", "oggetto_mappa", "mappa_prefab"

        # ── SKIN DADI ─────────────────────────────────────────────────────────
        # Skin attive per ogni tipo di dado, per utente.
        # La colonna skin_json contiene un dizionario {facce: skin_id | null}
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skin_dadi (
                utente_id   INTEGER PRIMARY KEY,
                skin_json   TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (utente_id) REFERENCES utenti(id)
            )
        """)

        # ── CHUNK MAPPA ───────────────────────────────────────────────────────
        conn.execute("""
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

        # ── SOTTOLIVELLI ──────────────────────────────────────────────────────
        conn.execute("""
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

        # ── IMPOSTAZIONI ──────────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS impostazioni (
                chiave  TEXT PRIMARY KEY,
                valore  TEXT NOT NULL
            )
        """)

        conn.commit()
        print(f"[DB] Database inizializzato: {DB_PATH}")
