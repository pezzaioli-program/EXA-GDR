"""
sessione/sessione.py — Ciclo di vita e stato della sessione
============================================================
Questo file gestisce TUTTO ciò che riguarda una sessione di gioco:
apertura, chiusura, stato corrente, partecipanti, mappa attiva.

NON gestisce il combattimento (quello è combattimento.py).
NON gestisce la vista del Player (quella è vista_player.py).
NON gestisce la rete (quella è rete/ — Fase 3).

Concetto chiave: la MACCHINA A STATI
Una sessione può trovarsi in uno di questi stati:
    "attesa"        → sessione aperta, nessun combattimento
    "combattimento" → combattimento in corso, turni sequenziali
    "chiusa"        → sessione terminata

Ogni stato permette azioni diverse. Prima di fare qualcosa,
si chiede alla sessione in che stato si trova.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from database.modelli import (
    apri_sessione, chiudi_sessione,
    aggiungi_partecipante, partecipanti_sessione,
    crea_sessione, salva_personaggio
)
from mappa.esporta import carica_griglia_dal_db, salva_griglia_nel_db
from mappa.map import Griglia


# ─────────────────────────────────────────────────────────────────────────────
#  STATI DELLA SESSIONE
# ─────────────────────────────────────────────────────────────────────────────

class StatoSessione(Enum):
    """
    Enum per gli stati possibili della sessione.

    Perché un Enum e non stringhe ("attesa", "combattimento"...)?
    - Typo impossibili: StatoSessione.ATTESA non può essere scritto male
    - Autocompletamento nell'IDE
    - Confronto sicuro: stato == StatoSessione.ATTESA invece di stato == "attesa"
    - Documentazione implicita: guardando l'Enum sai tutti gli stati possibili
    """
    ATTESA        = "attesa"
    COMBATTIMENTO = "combattimento"
    CHIUSA        = "chiusa"


# ─────────────────────────────────────────────────────────────────────────────
#  STRUTTURA DATI DEL PARTECIPANTE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Partecipante:
    """
    Rappresenta un partecipante attivo alla sessione.

    @dataclass genera automaticamente __init__, __repr__ e __eq__
    basandosi sui campi definiti. Senza @dataclass dovresti scriverli
    a mano — è una scorciatoia molto usata in Python.

    Attributi:
        utente_id       — id dell'utente nel DB
        username        — nome mostrato in gioco
        personaggio_id  — id della scheda personaggio
        nome_personaggio— nome del personaggio
        posizione       — (q, r) sulla mappa, None se non ancora piazzato
        pf_correnti     — punti ferita attuali (aggiornati in tempo reale)
        pf_massimi      — punti ferita massimi (dalla scheda)
        velocita        — esagoni percorribili per turno
        connesso        — True se il client è online (usato in Fase 3)
    """
    utente_id:        int
    username:         str
    personaggio_id:   int
    nome_personaggio: str
    posizione:        Optional[tuple] = None
    pf_correnti:      int = 10
    pf_massimi:       int = 10
    velocita:         int = 6
    connesso:         bool = True

    @property
    def e_vivo(self) -> bool:
        """Un personaggio è vivo se ha almeno 1 PF."""
        return self.pf_correnti > 0

    @property
    def percentuale_pf(self) -> float:
        """Percentuale PF rimasti — usata per colorare la barra salute."""
        if self.pf_massimi == 0:
            return 0.0
        return self.pf_correnti / self.pf_massimi


# ─────────────────────────────────────────────────────────────────────────────
#  CLASSE SESSIONE
# ─────────────────────────────────────────────────────────────────────────────

class Sessione:
    """
    Gestisce il ciclo di vita completo di una sessione di gioco.

    Una sola istanza di Sessione esiste alla volta (quella corrente).
    Il DM la crea, la apre, e la chiude.

    Attributi:
        sessione_id   — id nel database
        mondo_id      — mondo a cui appartiene
        mappa_id      — mappa attiva in questo momento
        griglia       — oggetto Griglia caricato in memoria
        stato         — StatoSessione corrente
        partecipanti  — dizionario {utente_id: Partecipante}
        combattimento — oggetto GestoreCombattimento (None se non in corso)
        log_eventi    — lista di stringhe con la storia della sessione
    """

    def __init__(self, mondo_id: int, mappa_id: int):
        self.mondo_id    = mondo_id
        self.mappa_id    = mappa_id
        self.sessione_id: Optional[int] = None
        self.griglia:     Optional[Griglia] = None
        self.stato        = StatoSessione.CHIUSA
        self.partecipanti: dict[int, Partecipante] = {}
        self.combattimento = None   # GestoreCombattimento, importato al bisogno
        self.log_eventi:  list[str] = []

    # ── Apertura e chiusura ───────────────────────────────────────────────────

    def apri(self) -> bool:
        """
        Apre la sessione: crea il record nel DB, carica la mappa, cambia stato.
        Restituisce True se tutto è andato bene.

        Flusso:
            1. Crea record sessione nel DB
            2. Carica la griglia dalla mappa
            3. Segna la sessione come aperta nel DB
            4. Cambia stato interno a ATTESA
        """
        try:
            # Crea la sessione nel database
            self.sessione_id = crea_sessione(self.mondo_id, self.mappa_id)

            # Carica la griglia esagonale dalla mappa salvata
            self.griglia = carica_griglia_dal_db(self.mappa_id)
            if self.griglia is None:
                self._log("ERRORE: impossibile caricare la mappa.")
                return False

            # Apri nel DB
            apri_sessione(self.sessione_id)
            self.stato = StatoSessione.ATTESA
            self._log("Sessione aperta.")
            return True

        except Exception as e:
            self._log(f"ERRORE apertura sessione: {e}")
            return False

    def chiudi(self):
        """
        Chiude la sessione: salva la mappa, aggiorna il DB, cambia stato.

        Perché salviamo la mappa alla chiusura e non ad ogni modifica?
        Salvare ad ogni click sarebbe troppo frequente e lento.
        Salviamo alla chiusura + ogni N minuti (autosave, da implementare).
        """
        if self.sessione_id is None:
            return

        # Salva lo stato finale della mappa
        if self.griglia:
            salva_griglia_nel_db(self.mappa_id, self.griglia)

        chiudi_sessione(self.sessione_id)
        self.stato = StatoSessione.CHIUSA
        self._log("Sessione chiusa.")

    # ── Partecipanti ─────────────────────────────────────────────────────────

    def aggiungi_giocatore(self, utente_id: int, username: str,
                           personaggio_id: int, nome_personaggio: str,
                           statistiche: dict) -> bool:
        """
        Aggiunge un Player alla sessione.
        Restituisce False se la sessione è chiusa.

        statistiche: dizionario dalla scheda personaggio
                     usato per inizializzare PF e velocità del Partecipante
        """
        if self.stato == StatoSessione.CHIUSA:
            return False

        partecipante = Partecipante(
            utente_id        = utente_id,
            username         = username,
            personaggio_id   = personaggio_id,
            nome_personaggio = nome_personaggio,
            pf_correnti      = statistiche.get("punti_ferita", 10),
            pf_massimi       = statistiche.get("pf_massimi", 10),
            velocita         = statistiche.get("velocita", 6),
        )
        self.partecipanti[utente_id] = partecipante

        # Registra nel database
        aggiungi_partecipante(self.sessione_id, utente_id, personaggio_id)
        self._log(f"{username} ({nome_personaggio}) è entrato nella sessione.")
        return True

    def rimuovi_giocatore(self, utente_id: int):
        """Rimuove un Player dalla sessione (disconnessione o uscita volontaria)."""
        if utente_id in self.partecipanti:
            nome = self.partecipanti[utente_id].username
            del self.partecipanti[utente_id]
            self._log(f"{nome} ha lasciato la sessione.")

    # ── Posizionamento token ──────────────────────────────────────────────────

    def piazza_token(self, utente_id: int, q: int, r: int) -> bool:
        """
        Piazza il token di un Player sulla mappa alla posizione (q, r).
        Restituisce False se la cella non esiste o il Player non è in sessione.

        Il token viene salvato sull'esagono come oggetto mobile con
        il riferimento al personaggio — così la mappa sa chi è dove.
        """
        if utente_id not in self.partecipanti:
            return False
        if (q, r) not in self.griglia.celle:
            return False

        partecipante = self.partecipanti[utente_id]

        # Rimuovi il token dalla posizione precedente
        if partecipante.posizione:
            self._rimuovi_token_da_cella(*partecipante.posizione, utente_id)

        # Piazza il token sulla nuova cella
        esagono = self.griglia.celle[(q, r)]
        esagono.oggetti["mobile"].append({
            "tipo":           "token_player",
            "utente_id":      utente_id,
            "nome":           partecipante.nome_personaggio,
            "colore":         (255, 220, 50),  # giallo per il proprio token
            "colore_altri":   (180, 100, 200), # viola per gli altri player
        })

        partecipante.posizione = (q, r)
        return True

    def muovi_token(self, utente_id: int, q_dest: int, r_dest: int,
                    richiedente_id: int) -> tuple[bool, str]:
        """
        Muove il token di un Player verso (q_dest, r_dest).

        richiedente_id: chi sta chiedendo il movimento.
            - In ATTESA: solo il DM può muovere (richiedente_id == None = DM)
            - In COMBATTIMENTO: solo il Player del turno corrente

        Restituisce (successo, messaggio_errore).
        """
        if utente_id not in self.partecipanti:
            return False, "Personaggio non in sessione."

        if (q_dest, r_dest) not in self.griglia.celle:
            return False, "Destinazione fuori dalla mappa."

        partecipante = self.partecipanti[utente_id]

        # In combattimento: verifica che sia il turno del Player
        if self.stato == StatoSessione.COMBATTIMENTO:
            if self.combattimento is None:
                return False, "Errore interno: combattimento non inizializzato."
            if not self.combattimento.e_il_tuo_turno(utente_id):
                return False, "Non è il tuo turno."
            if not self.combattimento.puoi_muoverti(utente_id, q_dest, r_dest):
                return False, "Movimento fuori dalla portata."

        self.piazza_token(utente_id, q_dest, r_dest)
        self._log(f"{partecipante.nome_personaggio} si è mosso in ({q_dest}, {r_dest}).")
        return True, ""

    def _rimuovi_token_da_cella(self, q: int, r: int, utente_id: int):
        """Rimuove il token di un Player da una specifica cella."""
        if (q, r) not in self.griglia.celle:
            return
        esagono = self.griglia.celle[(q, r)]
        esagono.oggetti["mobile"] = [
            m for m in esagono.oggetti["mobile"]
            if not (m.get("tipo") == "token_player" and m.get("utente_id") == utente_id)
        ]

    # ── Combattimento ─────────────────────────────────────────────────────────

    def avvia_combattimento(self) -> bool:
        """
        Avvia il combattimento:
            1. Crea il GestoreCombattimento
            2. Fa lanciare l'iniziativa a tutti i partecipanti
            3. Cambia stato a COMBATTIMENTO

        Import locale per evitare import circolare:
        combattimento.py importa Sessione → Sessione non può importare
        combattimento.py a livello di modulo.
        """
        if self.stato != StatoSessione.ATTESA:
            return False
        if not self.partecipanti:
            return False

        from sessione.combattimento import GestoreCombattimento
        self.combattimento = GestoreCombattimento(self)
        self.combattimento.lancia_iniziativa()
        self.stato = StatoSessione.COMBATTIMENTO
        self._log("Combattimento iniziato!")
        return True

    def termina_combattimento(self):
        """Termina il combattimento e torna in modalità ATTESA."""
        self.combattimento = None
        self.stato = StatoSessione.ATTESA
        self._log("Combattimento terminato.")

    def aggiorna_pf(self, utente_id: int, nuovi_pf: int):
        """
        Aggiorna i PF di un partecipante.
        Se scendono a 0 gestisce la morte del personaggio.
        """
        if utente_id not in self.partecipanti:
            return

        partecipante = self.partecipanti[utente_id]
        # Clamp: i PF non possono scendere sotto 0 o salire sopra il massimo
        partecipante.pf_correnti = max(0, min(nuovi_pf, partecipante.pf_massimi))

        if partecipante.pf_correnti == 0:
            self._gestisci_morte(utente_id)

    def _gestisci_morte(self, utente_id: int):
        """
        Gestisce la morte di un personaggio.
        Rimuove il token dalla mappa e notifica il Player.
        Il Player potrà creare una nuova scheda (Fase 2 - personaggio/).
        """
        partecipante = self.partecipanti[utente_id]
        if partecipante.posizione:
            self._rimuovi_token_da_cella(*partecipante.posizione, utente_id)
            partecipante.posizione = None

        self._log(f"💀 {partecipante.nome_personaggio} è caduto!")
        # In Fase 3 qui invieremo una notifica WebSocket al Player

    # ── Log eventi ────────────────────────────────────────────────────────────

    def _log(self, messaggio: str):
        """
        Aggiunge un messaggio al log della sessione.
        Il log viene mostrato nella chat della sessione.
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        voce = f"[{timestamp}] {messaggio}"
        self.log_eventi.append(voce)
        print(voce)   # anche su terminale per debug

    # ── Stato e informazioni ──────────────────────────────────────────────────

    def stato_per_player(self, utente_id: int) -> dict:
        """
        Restituisce un dizionario con le informazioni che il Player
        deve vedere: posizioni di tutti, PF propri, stato sessione, log recente.

        Usato da vista_player.py per aggiornare la UI.
        In Fase 3 questo verrà inviato via WebSocket.
        """
        partecipante = self.partecipanti.get(utente_id)
        altri = []
        for uid, p in self.partecipanti.items():
            altri.append({
                "utente_id":      uid,
                "nome":           p.nome_personaggio,
                "posizione":      p.posizione,
                "pf_correnti":    p.pf_correnti,
                "pf_massimi":     p.pf_massimi,
                "e_il_mio":       uid == utente_id,
            })

        turno_corrente = None
        if self.stato == StatoSessione.COMBATTIMENTO and self.combattimento:
            turno_corrente = self.combattimento.chi_agisce_ora()

        return {
            "stato":          self.stato.value,
            "partecipanti":   altri,
            "turno_corrente": turno_corrente,
            "log_recente":    self.log_eventi[-20:],   # ultimi 20 messaggi
        }

    def __repr__(self):
        return (f"Sessione(id={self.sessione_id}, "
                f"stato={self.stato.value}, "
                f"partecipanti={len(self.partecipanti)})")
