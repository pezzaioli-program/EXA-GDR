"""
auth/sessione_utente.py — Utente attualmente loggato
=====================================================
Questo file mantiene lo stato globale dell'utente loggato.
È l'unico stato globale accettabile nel progetto.

Perché uno stato globale qui?
Ogni parte dell'app (mappa, shop, sessione) deve sapere chi è loggato.
Invece di passare i dati utente come parametro attraverso decine di
funzioni e classi, li leggi da un punto centrale.

Perché NON usare una variabile globale diretta?
  SBAGLIATO: utente_corrente = None  (globale nuda)
  GIUSTO: funzioni get/set che controllano i dati

Le funzioni get/set permettono di aggiungere controlli in futuro
(es. logging, validazione) senza cambiare il resto del codice.
"""

# Lo stato interno — privato (prefisso _)
# None = nessuno è loggato
_utente: dict | None = None


def imposta_utente_corrente(dati: dict):
    """
    Salva i dati dell'utente loggato.
    Chiamata da login_window.py dopo un login riuscito.

    dati attesi: {"id": 1, "username": "...", "ruolo": "dm", "abbonamento_attivo": True}
    """
    global _utente
    _utente = dati


def utente_corrente() -> dict | None:
    """
    Restituisce i dati dell'utente loggato, o None se nessuno è loggato.

    Uso tipico:
        from auth.sessione_utente import utente_corrente
        utente = utente_corrente()
        if utente and utente["ruolo"] == "dm":
            # mostra funzionalità DM
    """
    return _utente


def e_loggato() -> bool:
    """Restituisce True se c'è un utente loggato."""
    return _utente is not None


def e_dm() -> bool:
    """Restituisce True se l'utente loggato è un DM."""
    return _utente is not None and _utente.get("ruolo") == "dm"


def e_player() -> bool:
    """Restituisce True se l'utente loggato è un Player."""
    return _utente is not None and _utente.get("ruolo") == "player"


def ha_abbonamento() -> bool:
    """Restituisce True se il DM ha l'abbonamento attivo."""
    return _utente is not None and bool(_utente.get("abbonamento_attivo", False))


def logout():
    """
    Cancella i dati dell'utente loggato.
    Chiamata quando l'utente clicca "Esci" dall'applicazione.
    """
    global _utente
    _utente = None
