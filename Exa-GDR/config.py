"""
config.py — Costanti globali del progetto GDR
==============================================
REGOLA FONDAMENTALE: questo file non importa NULLA degli altri moduli
del progetto. Tutti gli altri moduli possono importare da qui, ma config.py
sta alla base della piramide delle dipendenze.

Perché centralizzare qui: ogni valore che compare in più di un file
deve vivere in un posto solo. Modificare una costante = toccare una riga.
"""

import os

# ─────────────────────────────────────────────────────────────────────────────
#  PERCORSI — dove vivono i file del progetto
# ─────────────────────────────────────────────────────────────────────────────

# Cartella radice del progetto (quella che contiene config.py)
# os.path.dirname(__file__) restituisce la cartella del file corrente.
# Usare __file__ invece di un percorso assoluto ("C:/utenti/...") significa
# che il progetto funziona su qualsiasi computer, indipendentemente da dove
# è installato.
CARTELLA_ROOT = os.path.dirname(os.path.abspath(__file__))

# Percorso del database SQLite
# os.path.join costruisce percorsi in modo corretto su Windows (\) e Mac/Linux (/)
DB_PATH = os.path.join(CARTELLA_ROOT, "database", "gdr.db")

# Cartelle degli asset grafici
CARTELLA_ASSET       = os.path.join(CARTELLA_ROOT, "asset")
CARTELLA_TERRENI     = os.path.join(CARTELLA_ASSET, "terreni")
CARTELLA_OGGETTI     = os.path.join(CARTELLA_ASSET, "oggetti")
CARTELLA_PERSONAGGI  = os.path.join(CARTELLA_ASSET, "personaggi")
CARTELLA_NPC         = os.path.join(CARTELLA_ASSET, "npc")
CARTELLA_UI          = os.path.join(CARTELLA_ASSET, "ui")
CARTELLA_ACQUISTATI  = os.path.join(CARTELLA_ASSET, "acquistati")


# ─────────────────────────────────────────────────────────────────────────────
#  RETE — configurazione WebSocket
# ─────────────────────────────────────────────────────────────────────────────

# Il DM avvia il server su questa porta. I Player si connettono all'IP
# del DM su questa stessa porta.
# 8765 è una porta alta (>1024) che non richiede privilegi di amministratore.
WS_PORTA = 8765

# IP di default quando si testa in locale (DM e Player sullo stesso PC)
WS_HOST_DEFAULT = "localhost"

# Timeout in secondi per la connessione WebSocket.
# Se il server non risponde entro questo tempo, il client mostra "offline".
WS_TIMEOUT = 5

# Intervallo in secondi tra i ping di controllo connessione
WS_PING_INTERVALLO = 10


# ─────────────────────────────────────────────────────────────────────────────
#  FINESTRA PRINCIPALE — dimensioni e titolo
# ─────────────────────────────────────────────────────────────────────────────

APP_TITOLO          = "GDR Map Creator & Session Manager"
APP_VERSIONE        = "0.1.0"

FINESTRA_LARGHEZZA  = 1400
FINESTRA_ALTEZZA    = 900

# Dimensioni minime sotto cui la finestra non può essere ridimensionata
FINESTRA_MIN_LARGHEZZA = 1024
FINESTRA_MIN_ALTEZZA   = 700


# ─────────────────────────────────────────────────────────────────────────────
#  MAPPA ESAGONALE — geometria e griglia
# ─────────────────────────────────────────────────────────────────────────────

# Distanza dal centro di un esagono a un vertice, in pixel.
# Aumentare questo valore = esagoni più grandi.
HEX_DIMENSIONE = 40

# Dimensioni della griglia di default per una nuova mappa
GRIGLIA_COLONNE_DEFAULT = 20
GRIGLIA_RIGHE_DEFAULT   = 15

# Larghezza del pannello laterale sinistro nell'editor mappa
PANNELLO_LARGHEZZA = 160

# Zoom: fattore minimo e massimo (futura funzionalità)
ZOOM_MIN = 0.5
ZOOM_MAX = 3.0
ZOOM_DEFAULT = 1.0


# ─────────────────────────────────────────────────────────────────────────────
#  TERRENI — nome → colore RGB
# ─────────────────────────────────────────────────────────────────────────────
# Il colore viene usato come placeholder finché non c'è il PNG corrispondente.
# La chiave deve corrispondere esattamente al nome del file PNG nella cartella
# asset/terreni/ (es. "pianura" → asset/terreni/pianura.png).

TERRENI = {
    "pianura":  (144, 200, 120),   # verde chiaro
    "foresta":  ( 34, 100,  34),   # verde scuro
    "montagna": (140, 120, 100),   # marrone grigio
    "acqua":    ( 64, 150, 210),   # blu
    "deserto":  (220, 200, 130),   # sabbia
    "vuoto":    ( 50,  50,  50),   # grigio scuro (non assegnato)
}


# ─────────────────────────────────────────────────────────────────────────────
#  OGGETTI — catalogo completo degli oggetti piazzabili
# ─────────────────────────────────────────────────────────────────────────────
# Struttura di ogni voce:
#   id       → chiave univoca, deve corrispondere al nome del PNG in asset/oggetti/
#   nome     → etichetta mostrata nel pannello
#   layer    → "struttura" | "viabilita" | "mobile"
#   forma    → lista di offset (dq, dr) rispetto alla cella origine
#   colore   → placeholder RGB usato finché non c'è il PNG
#   icona    → 2 lettere mostrate sulla cella (finché non c'è il PNG)
#   png      → None ora, percorso stringa quando l'asset è disponibile
#
# LAYER — regole di sovrapposizione:
#   struttura → max 1 per cella, non sovrapponibile ad altre strutture
#   viabilita → max 1 per cella, si sovrappone a struttura e mobile
#   mobile    → lista, più oggetti possono coesistere

OGGETTI = {
    # ── Strutture piccole (1 cella) ──────────────────────────────────────────
    "casa": {
        "id": "casa", "nome": "Casa", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (210, 180, 140), "icona": "Ca", "png": None,
    },
    "albero": {
        "id": "albero", "nome": "Albero", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (50, 140, 50), "icona": "Ab", "png": None,
    },
    "statua": {
        "id": "statua", "nome": "Statua", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (180, 180, 190), "icona": "St", "png": None,
    },
    "strada": {
        "id": "strada", "nome": "Strada", "layer": "viabilita",
        "forma": [(0, 0)],
        "colore": (180, 160, 120), "icona": "Rd", "png": None,
    },
    # ── Strutture medie (3 celle) ─────────────────────────────────────────────
    "villaggio": {
        "id": "villaggio", "nome": "Villaggio", "layer": "struttura",
        "forma": [(0, 0), (1, 0), (0, 1)],
        "colore": (200, 150, 100), "icona": "Vi", "png": None,
    },
    "campo": {
        "id": "campo", "nome": "Campo coltivato", "layer": "struttura",
        "forma": [(0, 0), (1, 0), (0, 1)],
        "colore": (210, 200, 80), "icona": "Co", "png": None,
    },
    "foresta_densa": {
        "id": "foresta_densa", "nome": "Foresta densa", "layer": "struttura",
        "forma": [(0, 0), (1, 0), (0, 1)],
        "colore": (20, 80, 20), "icona": "Fd", "png": None,
    },
    "ponte": {
        "id": "ponte", "nome": "Ponte", "layer": "viabilita",
        "forma": [(0, 0), (1, 0), (2, 0)],
        "colore": (160, 140, 100), "icona": "Po", "png": None,
    },
    # ── Strutture grandi (4 celle) ────────────────────────────────────────────
    "castello": {
        "id": "castello", "nome": "Castello", "layer": "struttura",
        "forma": [(0, 0), (1, 0), (0, 1), (-1, 1)],
        "colore": (120, 110, 100), "icona": "Cs", "png": None,
    },
    "fattoria": {
        "id": "fattoria", "nome": "Fattoria", "layer": "struttura",
        "forma": [(0, 0), (1, 0), (0, 1), (-1, 1)],
        "colore": (180, 150, 80), "icona": "Fa", "png": None,
    },
    # ── Mobili (1 cella, layer mobile) ───────────────────────────────────────
    "carretto": {
        "id": "carretto", "nome": "Carretto", "layer": "mobile",
        "forma": [(0, 0)],
        "colore": (200, 160, 80), "icona": "Cr", "png": None,
    },
    # ── Con sottolivello ──────────────────────────────────────────────────────
    "locanda": {
        "id": "locanda", "nome": "Locanda", "layer": "struttura",
        "forma": [(0, 0), (1, 0)],
        "colore": (180, 120, 60), "icona": "Lo", "png": None,
        "ha_sottolivello": True,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  PAVIMENTI — usati nei sottolivelli invece dei terreni
# ─────────────────────────────────────────────────────────────────────────────

PAVIMENTI = {
    "pietra":              (100, 100, 110),
    "marmo":               (200, 195, 210),
    "legno":               (140,  95,  55),
    "terra_battuta":       (110,  85,  55),
    "mattoni":             (160,  80,  60),
    "piastrelle_bianche":  (220, 220, 225),
    "piastrelle_nere":     ( 40,  40,  45),
    "piastrelle_rosse":    (180,  70,  60),
    "vuoto_interno":       ( 30,  30,  35),
}

# ─────────────────────────────────────────────────────────────────────────────
#  OGGETTI INTERNI — usati solo nei sottolivelli
# ─────────────────────────────────────────────────────────────────────────────

OGGETTI_INTERNI = {
    # ── Strutture interne ─────────────────────────────────────────────────────
    "muro": {
        "id": "muro", "nome": "Muro", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (70, 70, 80), "icona": "Mu", "png": None,
        "solo_interno": True,
    },
    "porta_chiusa": {
        "id": "porta_chiusa", "nome": "Porta (chiusa)", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (140, 90, 40), "icona": "Pc", "png": None,
        "solo_interno": True,
    },
    "porta_aperta": {
        "id": "porta_aperta", "nome": "Porta (aperta)", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (180, 130, 70), "icona": "Pa", "png": None,
        "solo_interno": True,
    },
    "scale_su": {
        "id": "scale_su", "nome": "Scale (su)", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (160, 140, 100), "icona": "↑", "png": None,
        "solo_interno": True,
    },
    "scale_giu": {
        "id": "scale_giu", "nome": "Scale (giù)", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (120, 100, 70), "icona": "↓", "png": None,
        "solo_interno": True,
    },
    "altare": {
        "id": "altare", "nome": "Altare", "layer": "struttura",
        "forma": [(0, 0), (1, 0)],
        "colore": (180, 160, 200), "icona": "Al", "png": None,
        "solo_interno": True,
    },
    "statua_interna": {
        "id": "statua_interna", "nome": "Statua", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (160, 160, 170), "icona": "St", "png": None,
        "solo_interno": True,
    },
    # ── Arredo ───────────────────────────────────────────────────────────────
    "tavolo": {
        "id": "tavolo", "nome": "Tavolo", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (160, 110, 60), "icona": "Tv", "png": None,
        "solo_interno": True,
    },
    "sedia": {
        "id": "sedia", "nome": "Sedia", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (140, 95, 50), "icona": "Sd", "png": None,
        "solo_interno": True,
    },
    "letto": {
        "id": "letto", "nome": "Letto", "layer": "struttura",
        "forma": [(0, 0), (1, 0)],
        "colore": (200, 180, 160), "icona": "Lt", "png": None,
        "solo_interno": True,
    },
    "armadio": {
        "id": "armadio", "nome": "Armadio", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (120, 85, 45), "icona": "Ar", "png": None,
        "solo_interno": True,
    },
    "cassa": {
        "id": "cassa", "nome": "Cassa", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (160, 120, 60), "icona": "Cs", "png": None,
        "solo_interno": True,
    },
    "barile": {
        "id": "barile", "nome": "Barile", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (130, 90, 50), "icona": "Ba", "png": None,
        "solo_interno": True,
    },
    # ── Illuminazione ─────────────────────────────────────────────────────────
    "torcia": {
        "id": "torcia", "nome": "Torcia", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (255, 180, 50), "icona": "🔥", "png": None,
        "solo_interno": True,
    },
    "lampada": {
        "id": "lampada", "nome": "Lampada", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (240, 220, 140), "icona": "La", "png": None,
        "solo_interno": True,
    },
    # ── Trappole e pericoli ───────────────────────────────────────────────────
    "trappola_interna": {
        "id": "trappola_interna", "nome": "Trappola", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (200, 60, 60), "icona": "⚠", "png": None,
        "solo_interno": True,
    },
    "mimic": {
        "id": "mimic", "nome": "Mimic", "layer": "struttura",
        "forma": [(0, 0)],
        "colore": (160, 80, 160), "icona": "Mi", "png": None,
        "solo_interno": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  COLORI INTERFACCIA — usati da map.py, PyQt e altri moduli
# ─────────────────────────────────────────────────────────────────────────────
# Formato: tuple RGB (rosso, verde, blu) con valori 0-255.
# I nomi descrivono lo SCOPO, non il colore — così se cambi tema grafico
# basta modificare qui senza cercare in tutti i file.

# Mappa
COLORE_SFONDO           = ( 30,  30,  30)   # sfondo finestra principale
COLORE_BORDO_HEX        = ( 20,  20,  20)   # bordo degli esagoni
COLORE_SELEZIONE_HEX    = (255, 220,  50)   # esagono evidenziato (giallo)
COLORE_ANTEPRIMA_OK     = ( 80, 200,  80)   # anteprima oggetto: piazzabile
COLORE_ANTEPRIMA_NO     = (200,  80,  80)   # anteprima oggetto: bloccato
COLORE_FOG_OF_WAR       = ( 15,  15,  15)   # celle nascoste ai player

# Pannello laterale
COLORE_PANNELLO         = ( 45,  45,  55)   # sfondo pannello
COLORE_VOCE_ATTIVA      = ( 80,  80, 120)   # voce selezionata nel pannello
COLORE_TESTO            = (255, 255, 255)   # testo generico

# Interfaccia PyQt (usati nei file .py, non in stylesheet CSS)
COLORE_SFONDO_UI        = ( 40,  40,  50)
COLORE_ACCENTO          = ( 90,  90, 160)   # bottoni, highlight


# ─────────────────────────────────────────────────────────────────────────────
#  COMBATTIMENTO — regole base
# ─────────────────────────────────────────────────────────────────────────────

# Statistica usata per calcolare il numero di esagoni percorribili per turno.
# Il valore effettivo viene letto dalla scheda personaggio.
STAT_VELOCITA_DEFAULT = 6        # esagoni per turno se non specificato

# Punti ferita a 0 = morte (o incoscienza, dipende dal manuale)
PF_MORTE = 0


# ─────────────────────────────────────────────────────────────────────────────
#  AUTENTICAZIONE — parametri sicurezza
# ─────────────────────────────────────────────────────────────────────────────

# Numero di "round" dell'algoritmo bcrypt per l'hashing delle password.
# Più alto = più sicuro ma più lento. 12 è il valore raccomandato nel 2024.
# NON scendere sotto 10.
BCRYPT_ROUNDS = 12

# Lunghezza minima della password in caratteri
PASSWORD_MIN_LEN = 8


# ─────────────────────────────────────────────────────────────────────────────
#  SALVATAGGIO AUTOMATICO
# ─────────────────────────────────────────────────────────────────────────────

# Intervallo in secondi tra un salvataggio automatico e il successivo
# (per le note del personaggio e lo stato della sessione)
AUTOSAVE_INTERVALLO = 30
