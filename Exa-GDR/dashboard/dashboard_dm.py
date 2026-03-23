"""
dashboard/dashboard_dm.py — Dashboard del Dungeon Master
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auth.sessione_utente import utente_corrente, ha_abbonamento
from config import APP_TITOLO, FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA


class DashboardDM(QMainWindow):

    logout_richiesto = pyqtSignal()

    def __init__(self):
        super().__init__()
        utente = utente_corrente()
        self.setWindowTitle(f"{APP_TITOLO} — DM: {utente['username']}")
        self.setMinimumSize(FINESTRA_LARGHEZZA, FINESTRA_ALTEZZA)
        self._costruisci_ui(utente)

    def _costruisci_ui(self, utente: dict):
        centrale = QWidget()
        self.setCentralWidget(centrale)
        layout = QVBoxLayout(centrale)
        layout.setSpacing(16)
        layout.setContentsMargins(40, 30, 40, 30)

        # Header
        header = QHBoxLayout()
        titolo = QLabel(f"Benvenuto, {utente['username']}")
        titolo.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        header.addWidget(titolo)
        header.addStretch()

        abbonamento = ha_abbonamento()
        stato_abb = QLabel("✓ Abbonamento attivo" if abbonamento else "✗ Abbonamento non attivo")
        stato_abb.setStyleSheet("color: #80ff80;" if abbonamento else "color: #ff8080;")
        header.addWidget(stato_abb)

        btn_shop = QPushButton("🛒  Shop DM")
        btn_shop.clicked.connect(self._apri_shop)
        header.addWidget(btn_shop)

        btn_logout = QPushButton("Esci")
        btn_logout.setFixedWidth(80)
        btn_logout.clicked.connect(self.logout_richiesto.emit)
        header.addWidget(btn_logout)
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #555570;")
        layout.addWidget(sep)

        # Lista mondi sempre visibile
        lbl = QLabel("🌍  I miei Mondi")
        lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        layout.addWidget(lbl)

        self._lista_mondi = QListWidget()
        self._lista_mondi.setMinimumHeight(220)
        self._lista_mondi.itemDoubleClicked.connect(self._apri_mondo_da_lista)
        self._lista_mondi.setStyleSheet("""
            QListWidget { background-color: #3a3a4a; border: 1px solid #555570; border-radius: 4px; }
            QListWidget::item { padding: 10px; font-size: 13px; }
            QListWidget::item:selected { background-color: #5a5a90; }
        """)
        layout.addWidget(self._lista_mondi, stretch=1)

        riga_btn = QHBoxLayout()
        riga_btn.setSpacing(10)

        btn_nuovo = QPushButton("➕  Nuovo mondo")
        btn_nuovo.setMinimumHeight(40)
        btn_nuovo.clicked.connect(self._nuovo_mondo)
        riga_btn.addWidget(btn_nuovo)

        btn_modifica = QPushButton("✏️  Modifica selezionato")
        btn_modifica.setMinimumHeight(40)
        btn_modifica.clicked.connect(self._modifica_mondo_selezionato)
        riga_btn.addWidget(btn_modifica)

        riga_btn.addStretch()
        layout.addLayout(riga_btn)

        self._aggiorna_lista_mondi()

    def _aggiorna_lista_mondi(self):
        from mondi.mondo import GestoreMondo
        self._lista_mondi.clear()
        mondi = GestoreMondo.lista()
        if not mondi:
            item = QListWidgetItem("Nessun mondo ancora — clicca '➕ Nuovo mondo' per iniziare")
            item.setForeground(Qt.GlobalColor.gray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._lista_mondi.addItem(item)
        else:
            for mondo in mondi:
                desc = mondo['descrizione'][:50] if mondo['descrizione'] else ""
                testo = f"🌍  {mondo['nome']}"
                if desc:
                    testo += f"  —  {desc}..."
                item = QListWidgetItem(testo)
                item.setData(Qt.ItemDataRole.UserRole, mondo["id"])
                self._lista_mondi.addItem(item)

    def _nuovo_mondo(self):
        from mondi.mondo_editor import EditorMondo
        dialog = EditorMondo(parent=self)
        dialog.mondo_salvato.connect(lambda _: self._aggiorna_lista_mondi())
        dialog.exec()

    def _modifica_mondo_selezionato(self):
        item = self._lista_mondi.currentItem()
        mondo_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not mondo_id:
            QMessageBox.information(self, "Nessuna selezione",
                                    "Seleziona un mondo dalla lista.")
            return
        self._apri_mondo(mondo_id)

    def _apri_mondo_da_lista(self, item: QListWidgetItem):
        mondo_id = item.data(Qt.ItemDataRole.UserRole)
        if mondo_id:
            self._apri_mondo(mondo_id)

    def _apri_mondo(self, mondo_id: int):
        from mondi.mondo_editor import EditorMondo
        dialog = EditorMondo(mondo_id=mondo_id, parent=self)
        dialog.mondo_salvato.connect(lambda _: self._aggiorna_lista_mondi())
        dialog.exec()

    def _apri_shop(self):
        from shop.shop_dm import ShopDM
        ShopDM(parent=self).exec()
