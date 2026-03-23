"""
sessione/combattimento.py — Sistema di combattimento
=====================================================
Gestisce i turni sequenziali, l'iniziativa, il movimento in combattimento
e la risoluzione degli attacchi.

Dipende da Sessione (per accedere ai partecipanti e alla mappa)
ma non la importa direttamente — riceve l'istanza come parametro.
Questo evita l'import circolare: sessione.py importerebbe combattimento.py
che importerebbe sessione.py → loop infinito.

Soluzione: combattimento.py riceve l'oggetto Sessione come argomento
nel costruttore e lo usa direttamente. Nessun import di sessione.py.
"""

import random
import math
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
#  DADO — funzione base
# ─────────────────────────────────────────────────────────────────────────────

def lancia_dado(facce: int) -> int:
    """
    Lancia un dado con il numero di facce specificato.
    Restituisce un numero tra 1 e facce (inclusi).

    random.randint(a, b) restituisce un intero N tale che a <= N <= b.
    Nota: a differenza di range(), randint include ENTRAMBI gli estremi.
    """
    return random.randint(1, facce)


def modificatore_statistica(valore: int) -> int:
    """
    Calcola il modificatore da una statistica D&D.
    Formula standard: (statistica - 10) // 2

    Esempi:
        Forza 10 → modificatore  0
        Forza 14 → modificatore +2
        Forza 18 → modificatore +4
        Forza  8 → modificatore -1

    // è la divisione intera (floor division):
        7 // 2 = 3  (non 3.5)
       -1 // 2 = -1 (non -0.5, arrotonda verso il basso)
    """
    return (valore - 10) // 2


# ─────────────────────────────────────────────────────────────────────────────
#  STRUTTURA DATI PER IL TURNO
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VoceTurno:
    """
    Rappresenta un partecipante nell'ordine dell'iniziativa.

    Attributi:
        utente_id       — None se è un NPC/mob controllato dal DM
        nome            — nome mostrato nella lista iniziativa
        iniziativa      — valore del tiro d20 + modificatore destrezza
        e_player        — True se è un Player, False se è NPC/mob
        esagoni_rimasti — esagoni ancora percorribili in questo turno
        ha_attaccato    — True se ha già usato l'azione di attacco
    """
    utente_id:       Optional[int]
    nome:            str
    iniziativa:      int
    e_player:        bool
    esagoni_rimasti: int = 0
    ha_attaccato:    bool = False


# ─────────────────────────────────────────────────────────────────────────────
#  GESTORE COMBATTIMENTO
# ─────────────────────────────────────────────────────────────────────────────

class GestoreCombattimento:
    """
    Gestisce un combattimento sequenziale a turni.

    Attributi:
        sessione        — riferimento alla Sessione corrente
        ordine_turni    — lista di VoceTurno ordinata per iniziativa
        indice_turno    — chi agisce ora (indice in ordine_turni)
        round_corrente  — numero del round (parte da 1)
        risultati       — lista di stringhe con la storia del combattimento
    """

    def __init__(self, sessione):
        # Riceviamo la sessione come parametro, non la importiamo
        self.sessione       = sessione
        self.ordine_turni:  list[VoceTurno] = []
        self.indice_turno:  int = 0
        self.round_corrente: int = 0
        self.risultati:     list[str] = []

    # ── Iniziativa ────────────────────────────────────────────────────────────

    def lancia_iniziativa(self):
        """
        Fa lanciare l'iniziativa a tutti i partecipanti.

        Formula: d20 + modificatore_destrezza
        Chi ha l'iniziativa più alta agisce per primo.
        In caso di parità, ordine casuale (random.random() come chiave secondaria).

        Perché sorted() e non sort()?
        Entrambi funzionano, ma sorted() crea una nuova lista invece di
        modificare quella esistente — più sicuro se l'originale serve altrove.
        """
        voci = []

        for uid, partecipante in self.sessione.partecipanti.items():
            # Legge la destrezza dalla scheda personaggio nel DB
            from database.modelli import carica_personaggio
            scheda = carica_personaggio(partecipante.personaggio_id)
            destrezza = scheda["statistiche_json"].get("destrezza", 10) if scheda else 10

            tiro = lancia_dado(20)
            mod  = modificatore_statistica(destrezza)
            iniziativa = tiro + mod

            voce = VoceTurno(
                utente_id       = uid,
                nome            = partecipante.nome_personaggio,
                iniziativa      = iniziativa,
                e_player        = True,
                esagoni_rimasti = partecipante.velocita,
            )
            voci.append(voce)

            self.sessione._log(
                f"🎲 {partecipante.nome_personaggio}: iniziativa {tiro}+{mod} = {iniziativa}"
            )

        # Ordina per iniziativa decrescente.
        # -v.iniziativa: il segno negativo inverte l'ordine (il più alto prima).
        # random.random(): in caso di parità, ordine casuale.
        self.ordine_turni = sorted(
            voci,
            key=lambda v: (-v.iniziativa, random.random())
        )

        self.round_corrente = 1
        self.indice_turno   = 0
        self._annuncia_ordine()
        self._prepara_turno_corrente()

    def _annuncia_ordine(self):
        """Logga l'ordine di iniziativa per tutti."""
        self.sessione._log("── Ordine iniziativa ──")
        for i, voce in enumerate(self.ordine_turni):
            self.sessione._log(f"  {i+1}. {voce.nome} ({voce.iniziativa})")

    def _prepara_turno_corrente(self):
        """
        Prepara il turno del combattente corrente:
        ripristina esagoni di movimento e flag attacco.
        """
        if not self.ordine_turni:
            return
        voce = self.ordine_turni[self.indice_turno]

        # Ripristina le azioni del turno
        if voce.utente_id and voce.utente_id in self.sessione.partecipanti:
            voce.esagoni_rimasti = self.sessione.partecipanti[voce.utente_id].velocita
        voce.ha_attaccato = False

        self.sessione._log(
            f"⚔️  Round {self.round_corrente} — Turno di {voce.nome}"
        )

    # ── Stato turno ──────────────────────────────────────────────────────────

    def chi_agisce_ora(self) -> Optional[dict]:
        """
        Restituisce informazioni su chi sta agendo ora.
        Usato da vista_player.py per evidenziare il turno corrente.
        """
        if not self.ordine_turni:
            return None
        voce = self.ordine_turni[self.indice_turno]
        return {
            "utente_id": voce.utente_id,
            "nome":      voce.nome,
            "e_player":  voce.e_player,
            "round":     self.round_corrente,
        }

    def e_il_tuo_turno(self, utente_id: int) -> bool:
        """Restituisce True se è il turno del Player con questo utente_id."""
        if not self.ordine_turni:
            return False
        voce = self.ordine_turni[self.indice_turno]
        return voce.utente_id == utente_id

    # ── Movimento in combattimento ────────────────────────────────────────────

    def puoi_muoverti(self, utente_id: int, q_dest: int, r_dest: int) -> bool:
        """
        Verifica se il Player può muoversi verso (q_dest, r_dest).

        Controlla:
        1. È il turno del Player
        2. Ha ancora esagoni disponibili
        3. La destinazione è raggiungibile (distanza ≤ esagoni rimasti)

        La distanza in esagoni usa la formula della distanza assiale:
            d = max(|dq|, |dr|, |dq+dr|)  in coordinate cubiche
        Che si semplifica in coordinate assiali come:
            d = (|dq| + |dr| + |dq+dr|) / 2
        """
        if not self.e_il_tuo_turno(utente_id):
            return False

        voce = self.ordine_turni[self.indice_turno]
        if voce.esagoni_rimasti <= 0:
            return False

        partecipante = self.sessione.partecipanti.get(utente_id)
        if not partecipante or not partecipante.posizione:
            return False

        q_att, r_att = partecipante.posizione
        distanza = self._distanza_hex(q_att, r_att, q_dest, r_dest)

        return distanza <= voce.esagoni_rimasti

    def consuma_movimento(self, utente_id: int, q_dest: int, r_dest: int):
        """
        Scala gli esagoni rimasti dopo un movimento.
        Chiamata da Sessione.muovi_token() dopo aver spostato il token.
        """
        partecipante = self.sessione.partecipanti.get(utente_id)
        if not partecipante or not partecipante.posizione:
            return

        voce = self.ordine_turni[self.indice_turno]
        q_att, r_att = partecipante.posizione
        distanza = self._distanza_hex(q_att, r_att, q_dest, r_dest)
        voce.esagoni_rimasti = max(0, voce.esagoni_rimasti - distanza)

    @staticmethod
    def _distanza_hex(q1: int, r1: int, q2: int, r2: int) -> int:
        """
        Calcola la distanza in esagoni tra due celle.

        Formula in coordinate assiali:
            dq = q2 - q1
            dr = r2 - r1
            distanza = (|dq| + |dr| + |dq + dr|) / 2

        Perché questa formula? In coordinate cubiche (q, r, s) con s = -q-r,
        la distanza è max(|dq|, |dr|, |ds|). Convertendo in assiali si
        ottiene la formula sopra — è la stessa cosa, scritta diversamente.
        """
        dq = q2 - q1
        dr = r2 - r1
        return (abs(dq) + abs(dr) + abs(dq + dr)) // 2

    # ── Attacco ───────────────────────────────────────────────────────────────

    def esegui_attacco(self, attaccante_id: int,
                       bersaglio_id: int) -> tuple[bool, dict]:
        """
        Risolve un attacco automaticamente: dado + statistica.

        Formula attacco (D&D semplificato):
            tiro_attacco = d20 + modificatore_forza
            Se tiro_attacco >= CA del bersaglio → colpisce
            danno = d6 + modificatore_forza

        Restituisce (successo_operazione, dettagli_risultato).

        dettagli_risultato contiene tutto per il log e la UI:
        {
            "attaccante": nome,
            "bersaglio":  nome,
            "tiro":       15,
            "modificatore": +3,
            "totale":     18,
            "ca_bersaglio": 14,
            "colpisce":   True,
            "danno":      7,
            "pf_rimasti": 8,
        }
        """
        if not self.e_il_tuo_turno(attaccante_id):
            return False, {"errore": "Non è il tuo turno."}

        voce = self.ordine_turni[self.indice_turno]
        if voce.ha_attaccato:
            return False, {"errore": "Hai già attaccato questo turno."}

        att = self.sessione.partecipanti.get(attaccante_id)
        ber = self.sessione.partecipanti.get(bersaglio_id)
        if not att or not ber:
            return False, {"errore": "Partecipante non trovato."}

        # Carica le statistiche dal DB
        from database.modelli import carica_personaggio
        scheda_att = carica_personaggio(att.personaggio_id)
        scheda_ber = carica_personaggio(ber.personaggio_id)

        stats_att = scheda_att["statistiche_json"] if scheda_att else {}
        stats_ber = scheda_ber["statistiche_json"] if scheda_ber else {}

        forza_att = stats_att.get("forza", 10)
        ca_ber    = stats_ber.get("classe_armatura", 10)

        # Tiro attacco
        tiro_d20  = lancia_dado(20)
        mod_forza = modificatore_statistica(forza_att)
        totale    = tiro_d20 + mod_forza
        colpisce  = totale >= ca_ber

        risultato = {
            "attaccante":   att.nome_personaggio,
            "bersaglio":    ber.nome_personaggio,
            "tiro":         tiro_d20,
            "modificatore": mod_forza,
            "totale":       totale,
            "ca_bersaglio": ca_ber,
            "colpisce":     colpisce,
            "danno":        0,
            "pf_rimasti":   ber.pf_correnti,
        }

        if colpisce:
            danno = lancia_dado(6) + max(0, mod_forza)
            nuovi_pf = ber.pf_correnti - danno
            self.sessione.aggiorna_pf(bersaglio_id, nuovi_pf)
            risultato["danno"]     = danno
            risultato["pf_rimasti"] = max(0, nuovi_pf)

            self.sessione._log(
                f"⚔️  {att.nome_personaggio} colpisce {ber.nome_personaggio} "
                f"({tiro_d20}+{mod_forza}={totale} vs CA {ca_ber}) "
                f"per {danno} danni! PF rimasti: {max(0, nuovi_pf)}"
            )
        else:
            self.sessione._log(
                f"💨 {att.nome_personaggio} manca {ber.nome_personaggio} "
                f"({tiro_d20}+{mod_forza}={totale} vs CA {ca_ber})"
            )

        voce.ha_attaccato = True
        return True, risultato

    # ── Avanzamento turno ─────────────────────────────────────────────────────

    def termina_turno(self, utente_id: int) -> bool:
        """
        Il Player (o il DM per un NPC) dichiara fine turno.
        Avanza al combattente successivo.
        Restituisce False se non è il turno di utente_id.
        """
        if not self.e_il_tuo_turno(utente_id):
            return False

        # Avanza all'indice successivo
        self.indice_turno += 1

        # Se abbiamo finito il giro → nuovo round
        if self.indice_turno >= len(self.ordine_turni):
            self.indice_turno = 0
            self.round_corrente += 1
            self.sessione._log(f"── Inizio Round {self.round_corrente} ──")

            # Rimuovi i combattenti morti dall'ordine
            self.ordine_turni = [
                v for v in self.ordine_turni
                if v.utente_id is None or
                self.sessione.partecipanti.get(v.utente_id, None) and
                self.sessione.partecipanti[v.utente_id].e_vivo
            ]

            if not self.ordine_turni:
                self.sessione._log("Nessun combattente rimasto.")
                self.sessione.termina_combattimento()
                return True

        self._prepara_turno_corrente()
        return True

    def lista_iniziativa(self) -> list[dict]:
        """
        Restituisce la lista dell'iniziativa per la UI.
        Usata da vista_player.py per mostrare chi agisce e in che ordine.
        """
        return [
            {
                "nome":       v.nome,
                "iniziativa": v.iniziativa,
                "e_attivo":   i == self.indice_turno,
                "e_player":   v.e_player,
            }
            for i, v in enumerate(self.ordine_turni)
        ]
