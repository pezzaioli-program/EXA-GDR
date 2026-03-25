"""
auth/registro.py — Logica di autenticazione
============================================
Questo file sa COME verificare le credenziali.
NON sa come mostrarle graficamente (quello è login_window.py).
NON sa come salvarle nel DB (quello è database/modelli.py).

Sa solo: "questa password è corretta?" e "questo utente può registrarsi?"
"""

import bcrypt
from config import BCRYPT_ROUNDS, PASSWORD_MIN_LEN
from database.modelli import (
    crea_utente,
    trova_utente_per_username,
    trova_utente_per_id,
)


# ─────────────────────────────────────────────────────────────────────────────
#  HASHING
# ─────────────────────────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    """
    Converte una password in chiaro nel suo hash bcrypt.
    Il prefisso _ indica che è una funzione privata — usata solo in questo file.

    bcrypt.hashpw vuole bytes, non stringhe — per questo encode("utf-8").
    decode("utf-8") alla fine riconverte l'hash in stringa per salvarlo nel DB.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode("utf-8")


def _verifica_password(password: str, hash_salvato: str) -> bool:
    """
    Confronta una password in chiaro con l'hash salvato nel DB.
    Restituisce True se corrispondono, False altrimenti.

    bcrypt.checkpw fa tutto il lavoro: estrae il salt dall'hash,
    rielabora la password e confronta — senza che tu debba fare nulla.
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hash_salvato.encode("utf-8")
    )


# ─────────────────────────────────────────────────────────────────────────────
#  VALIDAZIONE
# ─────────────────────────────────────────────────────────────────────────────

def _valida_registrazione(username: str, password: str, ruolo: str) -> str | None:
    """
    Controlla che i dati di registrazione siano validi.
    Restituisce un messaggio di errore (stringa) se qualcosa non va,
    oppure None se tutto è ok.

    Perché restituire una stringa di errore invece di sollevare un'eccezione?
    Perché l'errore non è "eccezionale" — è normale che un utente sbagli
    il form. Le eccezioni sono per errori imprevisti (DB non raggiungibile,
    file mancante...). Gli errori di validazione sono errori "attesi".
    """
    if not username or not username.strip():
        return "Il nome utente non può essere vuoto."

    if len(username) < 3:
        return "Il nome utente deve avere almeno 3 caratteri."

    if len(username) > 30:
        return "Il nome utente non può superare i 30 caratteri."

    if not password:
        return "La password non può essere vuota."

    if len(password) < PASSWORD_MIN_LEN:
        return f"La password deve avere almeno {PASSWORD_MIN_LEN} caratteri."

    if ruolo not in ("player", "dm"):
        return "Ruolo non valido."

    # Controlla se lo username è già preso
    if trova_utente_per_username(username) is not None:
        return f"Il nome utente '{username}' è già in uso."

    return None   # nessun errore = tutto ok


# ─────────────────────────────────────────────────────────────────────────────
#  REGISTRAZIONE
# ─────────────────────────────────────────────────────────────────────────────

def registra_utente(username: str, password: str, ruolo: str) -> tuple[bool, str]:
    """
    Registra un nuovo utente nel sistema.

    Restituisce una tupla (successo, messaggio):
      (True,  "")           → registrazione riuscita
      (False, "Il nome...") → errore con spiegazione

    Perché una tupla (bool, str) invece di True/False?
    Perché il chiamante (login_window.py) ha bisogno di sapere
    PERCHÉ è fallito per mostrarlo all'utente. Solo True/False
    non basta.

    Flusso:
      1. Valida i dati
      2. Hashea la password
      3. Salva nel DB
    """
    errore = _valida_registrazione(username.strip(), password, ruolo)
    if errore:
        return (False, errore)

    password_hash = _hash_password(password)
    crea_utente(username.strip(), password_hash, ruolo)
    return (True, "")


# ─────────────────────────────────────────────────────────────────────────────
#  LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def login(username: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Verifica le credenziali di login.

    Restituisce una tripla (successo, messaggio, dati_utente):
      (True,  "",          {"id": 1, "username": "...", "ruolo": "dm"})
      (False, "Credenz...", None)

    Perché il messaggio di errore è vago ("Credenziali non valide")
    e non specifico ("Username non trovato" o "Password errata")?
    Sicurezza: se dici "username non trovato", un attaccante sa che
    quell'username non esiste e può concentrarsi su altri. Con un
    messaggio generico non dà informazioni utili.

    Flusso:
      1. Cerca l'utente per username
      2. Se non esiste → errore generico
      3. Verifica la password contro l'hash
      4. Se non corrisponde → stesso errore generico
      5. Se tutto ok → restituisce i dati utente
    """
    utente = trova_utente_per_username(username.strip())

    if utente is None:
        return (False, "Credenziali non valide.", None)

    if not _verifica_password(password, utente["password_hash"]):
        return (False, "Credenziali non valide.", None)

    # Restituiamo solo i campi necessari — mai restituire password_hash
    dati = {
        "id":                 utente["id"],
        "username":           utente["username"],
        "ruolo":              utente["ruolo"],
        "abbonamento_attivo": bool(utente["abbonamento_attivo"]),
    }
    return (True, "", dati)


# ─────────────────────────────────────────────────────────────────────────────
#  VERIFICA ABBONAMENTO DM
# ─────────────────────────────────────────────────────────────────────────────

def verifica_abbonamento_dm(utente_id: int) -> bool:
    """
    Controlla se un DM ha l'abbonamento attivo.
    Restituisce True se può accedere alle funzionalità DM, False altrimenti.

    Chiamata da login_window.py dopo il login riuscito di un DM.
    """
    utente = trova_utente_per_id(utente_id)
    if utente is None:
        return False
    return bool(utente["abbonamento_attivo"])
