"""
dashboard/dashboard_player.py — Dashboard del Player
=====================================================
Schermata principale del Player dopo il login.
Versione FASE 1: minimale ma funzionante.

Per ora mostra:
  - Benvenuto con username
  - Lista sessioni aperte (con aggiornamento manuale)
  - Pulsante logout
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from auth.sessione_utente import utente_corrente
from database.modelli import sessioni_aperte
from config import APP_TITOLO, FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA


class DashboardPlayer(QMainWindow):
    """
    Dashboard principale del Player.

    Mostra le sessioni attualmente aperte e permette di entrare.
    Un QTimer aggiorna la lista ogni 10 secondi automaticamente —
    così il Player vede quando il DM apre una sessione senza dover
    ricaricare manualmente.
    """

    logout_richiesto = pyqtSignal()

    def __init__(self):
        super().__init__()
        utente = utente_corrente()

        self.setWindowTitle(f"{APP_TITOLO} — Player: {utente['username']}")
        self.setMinimumSize(FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA)

        self._costruisci_ui(utente)

        # QTimer: chiama _aggiorna_sessioni ogni 10000ms (10 secondi)
        # Perché QTimer e non un thread? Perché QTimer è sicuro con PyQt —
        # i thread e i widget PyQt non vanno d'accordo senza precauzioni.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._aggiorna_sessioni)
        self._timer.start(10_000)

    def _costruisci_ui(self, utente: dict):
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()

        titolo = QLabel(f"Benvenuto, {utente['username']}")
        titolo.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header.addWidget(titolo)

        header.addStretch()

        btn_logout = QPushButton("Esci")
        btn_logout.setFixedWidth(80)
        btn_logout.clicked.connect(self.logout_richiesto.emit)
        header.addWidget(btn_logout)

        layout.addLayout(header)

        separatore = QFrame()
        separatore.setFrameShape(QFrame.Shape.HLine)
        separatore.setStyleSheet("color: #555570;")
        layout.addWidget(separatore)

        # ── Sessioni disponibili ──────────────────────────────────────────────
        layout.addWidget(QLabel("Sessioni disponibili:"))

        self.lista_sessioni = QListWidget()
        self.lista_sessioni.setMinimumHeight(200)
        self.lista_sessioni.setStyleSheet("""
            QListWidget {
                background-color: #3a3a4a;
                border: 1px solid #555570;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #5a5a90;
            }
        """)
        layout.addWidget(self.lista_sessioni)

        # Pulsante aggiorna manuale + etichetta ultimo aggiornamento
        riga_aggiorna = QHBoxLayout()
        self._label_aggiornamento = QLabel("Aggiornamento automatico ogni 10 secondi")
        self._label_aggiornamento.setStyleSheet("color: #888888; font-size: 11px;")
        riga_aggiorna.addWidget(self._label_aggiornamento)
        riga_aggiorna.addStretch()
        btn_aggiorna = QPushButton("↻  Aggiorna ora")
        btn_aggiorna.clicked.connect(self._aggiorna_sessioni)
        riga_aggiorna.addWidget(btn_aggiorna)
        layout.addLayout(riga_aggiorna)

        # ── Azioni ────────────────────────────────────────────────────────────
        azioni = QHBoxLayout()

        btn_entra = QPushButton("▶  Entra nella sessione")
        btn_entra.setMinimumHeight(44)
        btn_entra.setFont(QFont("Arial", 13))
        btn_entra.clicked.connect(self._entra_sessione)
        azioni.addWidget(btn_entra)

        btn_scheda = QPushButton("📋  La mia scheda")
        btn_scheda.setMinimumHeight(44)
        btn_scheda.setFont(QFont("Arial", 13))
        btn_scheda.clicked.connect(self._apri_scheda)
        azioni.addWidget(btn_scheda)

        btn_shop = QPushButton("🛒  Shop")
        btn_shop.setMinimumHeight(44)
        btn_shop.setFont(QFont("Arial", 13))
        btn_shop.clicked.connect(self._apri_shop)
        azioni.addWidget(btn_shop)

        layout.addLayout(azioni)

        # Carica la lista all'avvio
        self._aggiorna_sessioni()

    def _aggiorna_sessioni(self):
        """
        Richiede le sessioni aperte al database e aggiorna la lista.

        Perché leggiamo dal database e non da un server?
        Siamo ancora in Fase 1 — senza rete. In Fase 3, quando avremo
        i WebSocket, questa funzione ascolterà gli aggiornamenti in
        tempo reale invece di interrogare il DB periodicamente.
        """
        self.lista_sessioni.clear()
        sessioni = sessioni_aperte()

        if not sessioni:
            item = QListWidgetItem("Nessuna sessione aperta al momento")
            item.setForeground(Qt.GlobalColor.gray)
            # Disabilita la selezione per questo item
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.lista_sessioni.addItem(item)
        else:
            for s in sessioni:
                testo = f"Sessione #{s['id']}  —  avviata il {s['data_inizio']}"
                item = QListWidgetItem(f"🟢  {testo}")
                # Salviamo l'id della sessione nel dato interno dell'item
                # così quando l'utente clicca "Entra" sappiamo a quale sessione riferirci
                item.setData(Qt.ItemDataRole.UserRole, s["id"])
                self.lista_sessioni.addItem(item)

        from datetime import datetime
        ora = datetime.now().strftime("%H:%M:%S")
        self._label_aggiornamento.setText(f"Ultimo aggiornamento: {ora}")

    def _entra_sessione(self):
        """
        Gestisce il click su 'Entra nella sessione'.
        """
        item_selezionato = self.lista_sessioni.currentItem()
        if not item_selezionato:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona una sessione dalla lista.")
            return

        sessione_id = item_selezionato.data(Qt.ItemDataRole.UserRole)
        if sessione_id is None:
            return

        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        host, ok = QInputDialog.getText(
            self, "Connessione",
            "Inserisci l'IP del DM:",
            text="localhost"
        )
        if not ok or not host.strip():
            return

        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Funzionalità in arrivo",
            f"Connessione alla sessione #{sessione_id} su {host}.\n"
            "Questa funzionalità sarà disponibile nella Fase 3 (rete e multiplayer)."
        )

    def _apri_scheda(self):
        """Apre la scheda personaggio del Player."""
        from personaggio.scheda import FinestraScheda
        from auth.sessione_utente import utente_corrente
        from database.modelli import personaggi_del_player

        utente = utente_corrente()
        personaggi = personaggi_del_player(utente["id"])

        if not personaggi:
            # Nessun personaggio — apre direttamente la creazione
            dialog = FinestraScheda(parent=self)
            dialog.exec()
        elif len(personaggi) == 1:
            dialog = FinestraScheda(personaggio_id=personaggi[0]["id"], parent=self)
            dialog.exec()
        else:
            # Più personaggi — chiede quale aprire
            from PyQt6.QtWidgets import QInputDialog
            nomi = [f"{p['nome']} ({p['classe']} lv.{p['livello']})"
                    for p in personaggi]
            nomi.append("+ Crea nuovo personaggio")
            scelta, ok = QInputDialog.getItem(
                self, "Scegli personaggio", "Personaggio:", nomi, editable=False)
            if not ok:
                return
            idx = nomi.index(scelta)
            if idx < len(personaggi):
                dialog = FinestraScheda(personaggio_id=personaggi[idx]["id"], parent=self)
            else:
                dialog = FinestraScheda(parent=self)
            dialog.exec()

    def _apri_shop(self):
        """Apre lo shop del Player."""
        from shop.shop_player import ShopPlayer
        ShopPlayer(parent=self).exec()


    def closeEvent(self, event):
        """
        Chiamata da PyQt quando la finestra viene chiusa (X in alto a destra).
        Fermiamo il timer prima di chiudere — buona pratica per evitare
        che il timer continui a girare su un widget già distrutto.
        """
        self._timer.stop()
        super().closeEvent(event)
