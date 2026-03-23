"""
sessione/vista_player.py — Interfaccia del Player durante la sessione
======================================================================
Quello che vede il Player:
  - SINISTRA:  mappa esagonale (pygame embedded in PyQt)
               Il proprio token è GIALLO, gli altri sono VIOLA
               Fog of war attivo (vede solo le celle svelate dal DM)
  - DESTRA:    colonna con tab Scheda / Note
  - BASSO:     sistema dadi + chat log sessione
  - CENTRO IN ALTO: barra iniziativa (solo durante il combattimento)

Tecnologia:
  - PyQt6 per la struttura della finestra e i pannelli laterali
  - pygame embedded per la mappa (tramite QTimer che chiama il loop pygame)
  - Sessione per lo stato del gioco
  - ClientGDR per la comunicazione WebSocket in tempo reale
"""

import pygame
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QTabWidget, QTextEdit,
    QListWidget, QListWidgetItem, QFrame, QSplitter,
    QSpinBox, QComboBox, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from auth.sessione_utente import utente_corrente
from sessione.sessione import Sessione, StatoSessione
from sessione.combattimento import lancia_dado, modificatore_statistica
from rete.client import ClientGDR
from config import (
    FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA,
    COLORE_SFONDO, COLORE_TESTO, APP_TITOLO,
    WS_HOST_DEFAULT, WS_PORTA,
)

# Colori token
COLORE_TOKEN_MIO    = (255, 220,  50)   # giallo — il mio personaggio
COLORE_TOKEN_ALTRI  = (180, 100, 200)   # viola  — altri player


class VistaPlayer(QMainWindow):
    """
    Finestra principale del Player durante una sessione.

    Struttura layout:
    ┌─────────────────────────────────┬──────────────┐
    │                                 │   SCHEDA /   │
    │        MAPPA ESAGONALE          │    NOTE      │
    │          (pygame)               │   (tab)      │
    │                                 │              │
    ├─────────────────────────────────┴──────────────┤
    │  [DADO] [tipo] [lancia]    LOG SESSIONE        │
    └────────────────────────────────────────────────┘
    """

    # Signal emesso se il Player abbandona la sessione
    sessione_abbandonata = pyqtSignal()

    def __init__(self, sessione: Sessione, host: str = WS_HOST_DEFAULT,
                 porta: int = WS_PORTA, parent=None):
        super().__init__(parent)
        self.sessione   = sessione
        self._utente    = utente_corrente()
        self._utente_id = self._utente["id"]

        self._pygame_inizializzato = False
        self._surface: pygame.Surface | None = None

        self.setWindowTitle(
            f"{APP_TITOLO} — {self._utente['username']} | Sessione in corso"
        )
        self.setMinimumSize(FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA)

        self._costruisci_ui()
        self._inizializza_pygame()

        # Client WebSocket
        self._client = ClientGDR(self._utente_id, self._utente["username"])
        self._collega_signal_rete()
        self._client.connetti(host, porta)

        # Indicatore connessione in basso
        self._lbl_connessione = QLabel("🔴 Connessione...")
        self.statusBar().addWidget(self._lbl_connessione)

        self._timer_mappa = QTimer(self)
        self._timer_mappa.timeout.connect(self._aggiorna_mappa)
        self._timer_mappa.start(16)

        self._timer_ui = QTimer(self)
        self._timer_ui.timeout.connect(self._aggiorna_ui)
        self._timer_ui.start(500)

    def _collega_signal_rete(self):
        c = self._client
        c.connesso.connect(lambda: self._lbl_connessione.setText("🟢 Connesso"))
        c.disconnesso.connect(lambda: self._lbl_connessione.setText("🔴 Disconnesso"))
        c.errore_connessione.connect(
            lambda e: self._lbl_connessione.setText(f"🔴 Errore: {e}"))
        c.token_mosso.connect(self._su_token_mosso)
        c.dado_lanciato.connect(self._su_dado_ricevuto)
        c.turno_avanzato.connect(self._su_turno_avanzato)
        c.combattimento_avviato.connect(self._su_combattimento_avviato)
        c.pf_aggiornati.connect(self._su_pf_aggiornati)
        c.personaggio_morto.connect(self._su_morte)
        c.stato_ricevuto.connect(self._su_stato_completo)
        c.giocatore_connesso.connect(
            lambda u: self.sessione._log(f"🟢 {u} si è connesso"))
        c.giocatore_disconnesso.connect(
            lambda uid: self.sessione._log(f"🔴 Giocatore {uid} disconnesso"))

    # ── Handler messaggi rete ─────────────────────────────────────────────────

    def _su_token_mosso(self, utente_id: int, q: int, r: int):
        self.sessione.piazza_token(utente_id, q, r)

    def _su_dado_ricevuto(self, username: str, descrizione: str):
        self.sessione._log(f"🎲 {username}: {descrizione}")

    def _su_turno_avanzato(self, lista_init: list, turno: dict):
        if self.sessione.combattimento:
            self.sessione.combattimento.ordine_turni = []
            self._aggiorna_iniziativa(turno)

    def _su_combattimento_avviato(self, lista_init: list, turno: dict):
        self.sessione.stato = StatoSessione.COMBATTIMENTO
        self.sessione._log("⚔️  Combattimento avviato!")

    def _su_pf_aggiornati(self, utente_id: int, pf: int):
        if utente_id in self.sessione.partecipanti:
            self.sessione.partecipanti[utente_id].pf_correnti = pf

    def _su_morte(self, utente_id: int, nome: str):
        self.sessione._log(f"💀 {nome} è caduto!")

    def _su_stato_completo(self, stato: dict):
        self.sessione._log("📡 Stato sessione ricevuto dal server.")


    def _costruisci_ui(self):
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout_root = QVBoxLayout(centrale)
        layout_root.setSpacing(0)
        layout_root.setContentsMargins(0, 0, 0, 0)

        # ── Barra iniziativa (nascosta fuori dal combattimento) ───────────────
        self._barra_iniziativa = self._crea_barra_iniziativa()
        layout_root.addWidget(self._barra_iniziativa)
        self._barra_iniziativa.setVisible(False)

        # ── Area principale: mappa + colonna destra ───────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout_root.addWidget(splitter, stretch=1)

        # Contenitore mappa pygame
        self._widget_mappa = QWidget()
        self._widget_mappa.setMinimumSize(700, 500)
        self._widget_mappa.setStyleSheet("background-color: #1e1e28;")
        splitter.addWidget(self._widget_mappa)

        # Colonna destra: scheda + note
        colonna_dx = self._crea_colonna_destra()
        colonna_dx.setMaximumWidth(320)
        colonna_dx.setMinimumWidth(220)
        splitter.addWidget(colonna_dx)

        splitter.setSizes([900, 280])

        # ── Barra inferiore: dadi + log ────────────────────────────────────────
        barra_basso = self._crea_barra_inferiore()
        layout_root.addWidget(barra_basso)

    def _crea_barra_iniziativa(self) -> QWidget:
        """
        Barra orizzontale che mostra l'ordine dei turni.
        Visibile solo durante il combattimento.
        """
        widget = QWidget()
        widget.setFixedHeight(48)
        widget.setStyleSheet("background-color: #3a1a1a; border-bottom: 1px solid #aa4444;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)

        lbl = QLabel("⚔️  COMBATTIMENTO:")
        lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #ff8888;")
        layout.addWidget(lbl)

        # Lista scrollabile orizzontale dei turni
        self._lista_iniziativa = QListWidget()
        self._lista_iniziativa.setFlow(QListWidget.Flow.LeftToRight)
        self._lista_iniziativa.setFixedHeight(36)
        self._lista_iniziativa.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._lista_iniziativa.setStyleSheet("""
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 2px 10px; border-radius: 4px;
                                margin: 2px; color: white; }
            QListWidget::item[attivo="true"] { background: #aa4444; }
        """)
        layout.addWidget(self._lista_iniziativa, stretch=1)

        self._btn_fine_turno = QPushButton("Fine turno →")
        self._btn_fine_turno.setFixedHeight(32)
        self._btn_fine_turno.setStyleSheet(
            "background: #aa4444; color: white; border-radius: 4px; padding: 0 12px;")
        self._btn_fine_turno.clicked.connect(self._fine_turno)
        layout.addWidget(self._btn_fine_turno)

        return widget

    def _crea_colonna_destra(self) -> QWidget:
        """
        Colonna destra con due tab: Scheda e Note.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Nome personaggio in cima
        partecipante = self.sessione.partecipanti.get(self._utente_id)
        nome_pg = partecipante.nome_personaggio if partecipante else "—"
        lbl_nome = QLabel(nome_pg)
        lbl_nome.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        lbl_nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_nome)

        # Barra PF
        self._lbl_pf = QLabel("PF: — / —")
        self._lbl_pf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_pf.setStyleSheet("color: #80ff80; font-size: 12px;")
        layout.addWidget(self._lbl_pf)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Tab Scheda / Note
        tabs = QTabWidget()
        tabs.addTab(self._crea_tab_scheda(), "Scheda")
        tabs.addTab(self._crea_tab_note(), "Note")
        layout.addWidget(tabs, stretch=1)

        return widget

    def _crea_tab_scheda(self) -> QWidget:
        """Mostra le statistiche del personaggio."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        layout = QVBoxLayout(contenuto)
        layout.setSpacing(4)

        partecipante = self.sessione.partecipanti.get(self._utente_id)
        if not partecipante:
            layout.addWidget(QLabel("Scheda non disponibile"))
            scroll.setWidget(contenuto)
            return scroll

        from database.modelli import carica_personaggio
        scheda = carica_personaggio(partecipante.personaggio_id)
        if not scheda:
            layout.addWidget(QLabel("Errore caricamento scheda"))
            scroll.setWidget(contenuto)
            return scroll

        stats = scheda["statistiche_json"]

        # Mostra ogni statistica come riga: nome | valore | modificatore
        for nome_stat, valore in stats.items():
            if nome_stat in ("punti_ferita", "pf_massimi", "velocita",
                             "classe_armatura"):
                continue   # mostrate altrove
            riga = QHBoxLayout()
            riga.addWidget(QLabel(nome_stat.capitalize() + ":"))
            riga.addStretch()
            mod = modificatore_statistica(valore)
            segno = "+" if mod >= 0 else ""
            riga.addWidget(QLabel(f"{valore}  ({segno}{mod})"))
            layout.addLayout(riga)

        layout.addWidget(QLabel(f"CA: {stats.get('classe_armatura', 10)}"))
        layout.addWidget(QLabel(f"Velocità: {stats.get('velocita', 6)} hex/turno"))
        layout.addStretch()

        scroll.setWidget(contenuto)
        return scroll

    def _crea_tab_note(self) -> QWidget:
        """Editor di testo per le note personali."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self._area_note = QTextEdit()
        self._area_note.setPlaceholderText(
            "Scrivi qui le tue note personali...\nSolo tu puoi vederle.")

        # Carica note esistenti dal DB
        partecipante = self.sessione.partecipanti.get(self._utente_id)
        if partecipante:
            from database.modelli import carica_personaggio
            scheda = carica_personaggio(partecipante.personaggio_id)
            if scheda:
                self._area_note.setPlainText(scheda.get("note", ""))

        layout.addWidget(self._area_note)

        btn_salva = QPushButton("💾  Salva note")
        btn_salva.clicked.connect(self._salva_note)
        layout.addWidget(btn_salva)

        return widget

    def _crea_barra_inferiore(self) -> QWidget:
        """
        Barra inferiore con sistema dadi a sinistra e log sessione a destra.
        """
        widget = QWidget()
        widget.setFixedHeight(160)
        widget.setStyleSheet(
            "background-color: #252535; border-top: 1px solid #555570;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # ── Sistema dadi ──────────────────────────────────────────────────────
        pannello_dadi = QWidget()
        pannello_dadi.setMaximumWidth(280)
        layout_dadi = QVBoxLayout(pannello_dadi)
        layout_dadi.setSpacing(4)

        lbl_dadi = QLabel("🎲 Lancia dado")
        lbl_dadi.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout_dadi.addWidget(lbl_dadi)

        # Selezione tipo dado
        riga_dado = QHBoxLayout()
        self._combo_dado = QComboBox()
        for facce in [4, 6, 8, 10, 12, 20, 100]:
            self._combo_dado.addItem(f"d{facce}", facce)
        self._combo_dado.setCurrentIndex(5)   # d20 di default
        riga_dado.addWidget(self._combo_dado)

        # Numero di dadi
        self._spin_num_dadi = QSpinBox()
        self._spin_num_dadi.setRange(1, 10)
        self._spin_num_dadi.setValue(1)
        self._spin_num_dadi.setPrefix("×")
        riga_dado.addWidget(self._spin_num_dadi)

        layout_dadi.addLayout(riga_dado)

        # Selezione statistica bonus
        self._combo_stat = QComboBox()
        self._combo_stat.addItem("Nessun bonus", None)
        partecipante = self.sessione.partecipanti.get(self._utente_id)
        if partecipante:
            from database.modelli import carica_personaggio
            scheda = carica_personaggio(partecipante.personaggio_id)
            if scheda:
                for stat in ["forza", "destrezza", "costituzione",
                             "intelligenza", "saggezza", "carisma"]:
                    val = scheda["statistiche_json"].get(stat, 10)
                    mod = modificatore_statistica(val)
                    segno = "+" if mod >= 0 else ""
                    self._combo_stat.addItem(
                        f"{stat.capitalize()} ({segno}{mod})", stat)
        layout_dadi.addWidget(self._combo_stat)

        btn_lancia = QPushButton("🎲  Lancia!")
        btn_lancia.clicked.connect(self._lancia_dado)
        layout_dadi.addWidget(btn_lancia)

        # Risultato ultimo tiro
        self._lbl_risultato_dado = QLabel("")
        self._lbl_risultato_dado.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self._lbl_risultato_dado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_risultato_dado.setStyleSheet("color: #ffdd44;")
        layout_dadi.addWidget(self._lbl_risultato_dado)

        layout.addWidget(pannello_dadi)

        # Separatore verticale
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #555570;")
        layout.addWidget(sep)

        # ── Log sessione ──────────────────────────────────────────────────────
        layout_log = QVBoxLayout()
        lbl_log = QLabel("📜 Log sessione")
        lbl_log.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout_log.addWidget(lbl_log)

        self._area_log = QTextEdit()
        self._area_log.setReadOnly(True)
        self._area_log.setStyleSheet(
            "background-color: #1e1e28; color: #aaaacc; font-size: 11px;")
        layout_log.addWidget(self._area_log)

        layout.addLayout(layout_log, stretch=1)

        return widget

    # ── pygame ────────────────────────────────────────────────────────────────

    def _inizializza_pygame(self):
        """
        Inizializza pygame e crea la surface su cui disegnare la mappa.
        La surface ha le stesse dimensioni del widget_mappa.
        """
        if not pygame.get_init():
            pygame.init()
        larghezza = self._widget_mappa.width()
        altezza   = self._widget_mappa.height()
        # Surface con supporto alpha per l'anteprima oggetti
        self._surface = pygame.Surface((larghezza, altezza))
        self._pygame_inizializzato = True

    def _aggiorna_mappa(self):
        """
        Chiamata ogni 16ms dal timer. Disegna la mappa pygame e
        la trasferisce nel widget PyQt.

        Come funziona il trasferimento pygame → PyQt:
        1. pygame disegna su self._surface
        2. Convertiamo la surface in bytes con pygame.image.tostring()
        3. Creiamo un QImage dai bytes
        4. Convertiamo in QPixmap e lo mostriamo in un QLabel
        """
        if not self._pygame_inizializzato or not self.sessione.griglia:
            return

        w = self._widget_mappa.width()
        h = self._widget_mappa.height()

        # Ridimensiona la surface se la finestra è cambiata
        if self._surface.get_size() != (w, h):
            self._surface = pygame.Surface((w, h))

        # Disegna sfondo
        self._surface.fill(COLORE_SFONDO)

        # Disegna la griglia con fog of war attivo (modalita_master=False)
        # e i token colorati in base all'utente
        self._disegna_griglia_con_token()

        # Trasferisci a PyQt
        self._surface_a_pyqt()

    def _disegna_griglia_con_token(self):
        """
        Disegna la griglia e sovrascrive i colori dei token:
        - token del Player corrente → GIALLO
        - token degli altri Player  → VIOLA
        """
        griglia = self.sessione.griglia

        # Prima aggiorniamo i colori dei token mobile sulla griglia
        for (q, r), esagono in griglia.celle.items():
            for mobile in esagono.oggetti.get("mobile", []):
                if mobile.get("tipo") == "token_player":
                    uid = mobile.get("utente_id")
                    mobile["colore"] = (
                        COLORE_TOKEN_MIO if uid == self._utente_id
                        else COLORE_TOKEN_ALTRI
                    )

        # Disegna la griglia in modalità Player (fog of war attivo)
        hex_corrente = None   # nessun hover in questa vista
        griglia.disegna(self._surface, hex_corrente, modalita_master=False)

    def _surface_a_pyqt(self):
        """
        Copia la surface pygame nel widget PyQt come QPixmap.

        pygame.image.tostring() → bytes grezzi RGB
        QImage(bytes, w, h, formato) → immagine Qt
        QLabel.setPixmap() → mostra l'immagine nel label
        """
        from PyQt6.QtGui import QImage, QPixmap
        from PyQt6.QtWidgets import QLabel

        dati = pygame.image.tostring(self._surface, "RGB")
        w, h = self._surface.get_size()
        qimg = QImage(dati, w, h, w * 3, QImage.Format.Format_RGB888)

        # Usa un QLabel nascosto come "tela" dentro widget_mappa
        if not hasattr(self, "_lbl_canvas"):
            self._lbl_canvas = QLabel(self._widget_mappa)
            self._lbl_canvas.setGeometry(0, 0, w, h)

        self._lbl_canvas.setPixmap(QPixmap.fromImage(qimg))
        self._lbl_canvas.resize(w, h)

    # ── Aggiornamento UI ──────────────────────────────────────────────────────

    def _aggiorna_ui(self):
        """
        Aggiorna la UI ogni 500ms con lo stato corrente della sessione:
        - PF del personaggio
        - Log sessione
        - Barra iniziativa (se in combattimento)
        """
        partecipante = self.sessione.partecipanti.get(self._utente_id)
        if partecipante:
            self._lbl_pf.setText(
                f"❤️  {partecipante.pf_correnti} / {partecipante.pf_massimi} PF")
            # Colore in base alla percentuale PF
            pct = partecipante.percentuale_pf
            if pct > 0.5:
                colore = "#80ff80"   # verde
            elif pct > 0.25:
                colore = "#ffaa44"   # arancione
            else:
                colore = "#ff4444"   # rosso
            self._lbl_pf.setStyleSheet(f"color: {colore}; font-size: 12px;")

        # Log
        stato = self.sessione.stato_per_player(self._utente_id)
        log_testo = "\n".join(stato["log_recente"])
        if self._area_log.toPlainText() != log_testo:
            self._area_log.setPlainText(log_testo)
            # Scrolla in fondo automaticamente
            self._area_log.verticalScrollBar().setValue(
                self._area_log.verticalScrollBar().maximum())

        # Barra iniziativa
        in_combattimento = self.sessione.stato == StatoSessione.COMBATTIMENTO
        self._barra_iniziativa.setVisible(in_combattimento)

        if in_combattimento and self.sessione.combattimento:
            self._aggiorna_iniziativa(stato.get("turno_corrente"))

        # Pulsante fine turno: attivo solo se è il mio turno
        if in_combattimento and self.sessione.combattimento:
            e_mio_turno = self.sessione.combattimento.e_il_tuo_turno(self._utente_id)
            self._btn_fine_turno.setEnabled(e_mio_turno)
            self._btn_fine_turno.setStyleSheet(
                "background: #cc4444; color: white; border-radius: 4px; padding: 0 12px;"
                if e_mio_turno else
                "background: #555555; color: #888888; border-radius: 4px; padding: 0 12px;"
            )

    def _aggiorna_iniziativa(self, turno_corrente: dict | None):
        """Aggiorna la lista dell'ordine d'iniziativa."""
        if not self.sessione.combattimento:
            return
        self._lista_iniziativa.clear()
        for voce in self.sessione.combattimento.lista_iniziativa():
            testo = f"{'▶ ' if voce['e_attivo'] else ''}{voce['nome']} ({voce['iniziativa']})"
            item = QListWidgetItem(testo)
            if voce["e_attivo"]:
                item.setBackground(QColor("#aa4444"))
            self._lista_iniziativa.addItem(item)

    # ── Azioni Player ─────────────────────────────────────────────────────────

    def _lancia_dado(self):
        """
        Lancia il dado selezionato con il bonus della statistica scelta.
        Mostra il risultato, lo aggiunge al log e lo invia via rete.
        """
        facce    = self._combo_dado.currentData()
        num      = self._spin_num_dadi.value()
        stat     = self._combo_stat.currentData()

        tiri     = [lancia_dado(facce) for _ in range(num)]
        somma    = sum(tiri)
        bonus    = 0

        if stat:
            partecipante = self.sessione.partecipanti.get(self._utente_id)
            if partecipante:
                from database.modelli import carica_personaggio
                scheda = carica_personaggio(partecipante.personaggio_id)
                if scheda:
                    valore = scheda["statistiche_json"].get(stat, 10)
                    bonus  = modificatore_statistica(valore)

        totale = somma + bonus
        dettaglio = "+".join(str(t) for t in tiri)
        if bonus != 0:
            segno = "+" if bonus >= 0 else ""
            testo_risultato = f"{dettaglio}{segno}{bonus} = {totale}"
        else:
            testo_risultato = f"{dettaglio} = {totale}" if num > 1 else str(totale)

        self._lbl_risultato_dado.setText(str(totale))

        utente = self._utente["username"]
        stat_str = f" ({stat})" if stat else ""
        descrizione = f"{utente} lancia {num}d{facce}{stat_str}: {testo_risultato}"
        self.sessione._log(f"🎲 {descrizione}")

        # Invia il risultato agli altri via WebSocket
        if self._client.e_connesso:
            self._client.invia_dado(descrizione)

    def _fine_turno(self):
        """Il Player dichiara fine turno — aggiorna localmente e invia via rete."""
        if self.sessione.combattimento:
            self.sessione.combattimento.termina_turno(self._utente_id)
        if self._client.e_connesso:
            self._client.invia_fine_turno()

    def _salva_note(self):
        """Salva le note nel database."""
        partecipante = self.sessione.partecipanti.get(self._utente_id)
        if not partecipante:
            return
        from database.modelli import carica_personaggio, salva_personaggio
        scheda = carica_personaggio(partecipante.personaggio_id)
        if scheda:
            salva_personaggio(
                partecipante.personaggio_id,
                scheda["statistiche_json"],
                scheda["inventario_json"],
                self._area_note.toPlainText()
            )
            self.sessione._log("📝 Note salvate.")

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        """Ferma i timer, disconnette il client e salva prima di chiudere."""
        self._timer_mappa.stop()
        self._timer_ui.stop()
        self._client.disconnetti()
        self._salva_note()
        super().closeEvent(event)
