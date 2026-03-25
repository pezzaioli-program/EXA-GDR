"""
dashboard/dashboard_player.py — Dashboard del Player
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
from lingua.gestore import t


class DashboardPlayer(QMainWindow):

    logout_richiesto = pyqtSignal()

    def __init__(self):
        super().__init__()
        utente = utente_corrente()
        self.setWindowTitle(f"{APP_TITOLO} — Player: {utente['username']}")
        self.setMinimumSize(FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA)
        self._costruisci_ui(utente)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._aggiorna_sessioni)
        self._timer.start(10_000)

    def _costruisci_ui(self, utente: dict):
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        header = QHBoxLayout()
        titolo = QLabel(t("benvenuto").format(u=utente['username']))
        titolo.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header.addWidget(titolo)
        header.addStretch()

        btn_logout = QPushButton(t("esci"))
        btn_logout.setFixedWidth(80)
        btn_logout.clicked.connect(self.logout_richiesto.emit)
        header.addWidget(btn_logout)
        layout.addLayout(header)

        separatore = QFrame()
        separatore.setFrameShape(QFrame.Shape.HLine)
        separatore.setStyleSheet("color: #555570;")
        layout.addWidget(separatore)

        layout.addWidget(QLabel(t("sessioni_disponibili")))

        self.lista_sessioni = QListWidget()
        self.lista_sessioni.setMinimumHeight(200)
        self.lista_sessioni.setStyleSheet("""
            QListWidget { background-color: #3a3a4a; border: 1px solid #555570; border-radius: 4px; }
            QListWidget::item:selected { background-color: #5a5a90; }
        """)
        layout.addWidget(self.lista_sessioni)

        riga_aggiorna = QHBoxLayout()
        self._label_aggiornamento = QLabel("")
        self._label_aggiornamento.setStyleSheet("color: #888888; font-size: 11px;")
        riga_aggiorna.addWidget(self._label_aggiornamento)
        riga_aggiorna.addStretch()
        btn_aggiorna = QPushButton(t("aggiorna"))
        btn_aggiorna.clicked.connect(self._aggiorna_sessioni)
        riga_aggiorna.addWidget(btn_aggiorna)
        layout.addLayout(riga_aggiorna)

        azioni = QHBoxLayout()

        btn_entra = QPushButton(t("entra_sessione"))
        btn_entra.setMinimumHeight(44)
        btn_entra.setFont(QFont("Arial", 13))
        btn_entra.clicked.connect(self._entra_sessione)
        azioni.addWidget(btn_entra)

        btn_scheda = QPushButton(t("la_mia_scheda"))
        btn_scheda.setMinimumHeight(44)
        btn_scheda.setFont(QFont("Arial", 13))
        btn_scheda.clicked.connect(self._apri_scheda)
        azioni.addWidget(btn_scheda)

        btn_shop = QPushButton(t("shop"))
        btn_shop.setMinimumHeight(44)
        btn_shop.setFont(QFont("Arial", 13))
        btn_shop.clicked.connect(self._apri_shop)
        azioni.addWidget(btn_shop)

        layout.addLayout(azioni)
        self._aggiorna_sessioni()

    def _aggiorna_sessioni(self):
        self.lista_sessioni.clear()
        sessioni = sessioni_aperte()

        if not sessioni:
            item = QListWidgetItem(t("nessuna_sessione"))
            item.setForeground(Qt.GlobalColor.gray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.lista_sessioni.addItem(item)
        else:
            for s in sessioni:
                testo = f"Sessione #{s['id']}  —  {s['data_inizio']}"
                item = QListWidgetItem(f"🟢  {testo}")
                item.setData(Qt.ItemDataRole.UserRole, s["id"])
                self.lista_sessioni.addItem(item)

        from datetime import datetime
        ora = datetime.now().strftime("%H:%M:%S")
        self._label_aggiornamento.setText(f"{t('aggiorna')}: {ora}")

    def _entra_sessione(self):
        item_selezionato = self.lista_sessioni.currentItem()
        if not item_selezionato:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, t("errore"), t("seleziona_mappa"))
            return

        sessione_id = item_selezionato.data(Qt.ItemDataRole.UserRole)
        if sessione_id is None:
            return

        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        host, ok = QInputDialog.getText(self, "Connessione", "IP del DM:", text="localhost")
        if not ok or not host.strip():
            return

        QMessageBox.information(self, "Info",
            f"Connessione alla sessione #{sessione_id} su {host}.\n"
            "Disponibile nella Fase 3.")

    def _apri_scheda(self):
        from personaggio.scheda import FinestraScheda
        from auth.sessione_utente import utente_corrente
        from database.modelli import personaggi_del_player

        utente = utente_corrente()
        personaggi = personaggi_del_player(utente["id"])

        if not personaggi:
            dialog = FinestraScheda(parent=self)
            dialog.exec()
        elif len(personaggi) == 1:
            dialog = FinestraScheda(personaggio_id=personaggi[0]["id"], parent=self)
            dialog.exec()
        else:
            from PyQt6.QtWidgets import QInputDialog
            nomi = [f"{p['nome']} ({p['classe']} lv.{p['livello']})" for p in personaggi]
            nomi.append("+ " + t("crea_account"))
            scelta, ok = QInputDialog.getItem(self, t("la_mia_scheda"), "", nomi, editable=False)
            if not ok:
                return
            idx = nomi.index(scelta)
            if idx < len(personaggi):
                dialog = FinestraScheda(personaggio_id=personaggi[idx]["id"], parent=self)
            else:
                dialog = FinestraScheda(parent=self)
            dialog.exec()

    def _apri_shop(self):
        from shop.shop_player import ShopPlayer
        ShopPlayer(parent=self).exec()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
