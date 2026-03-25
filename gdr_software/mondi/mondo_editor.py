"""
mondi/mondo_editor.py — Editor mondi per il DM
"""

import subprocess
import sys
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QWidget, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from mondi.mondo import GestoreMondo
from lingua.gestore import t


class EditorMondo(QDialog):

    mondo_salvato = pyqtSignal(int)

    def __init__(self, mondo_id: int = None, parent=None):
        super().__init__(parent)
        self.mondo_id = mondo_id
        self._dati = {}

        if mondo_id:
            self._dati = GestoreMondo.carica(mondo_id) or {}

        self.setWindowTitle(t("modifica_mondo") if mondo_id else t("crea_mondo"))
        self.setMinimumSize(700, 540)
        self._costruisci_ui()
        self._popola()

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._tab_info(),  t("informazioni"))
        tabs.addTab(self._tab_mappe(), t("mappe"))
        layout.addWidget(tabs)

        riga_btn = QHBoxLayout()
        riga_btn.addStretch()
        btn_annulla = QPushButton(t("annulla"))
        btn_annulla.clicked.connect(self.reject)
        riga_btn.addWidget(btn_annulla)
        btn_salva = QPushButton(t("salva"))
        btn_salva.setDefault(True)
        btn_salva.clicked.connect(self._salva)
        riga_btn.addWidget(btn_salva)
        layout.addLayout(riga_btn)

    def _tab_info(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._campo_nome = QLineEdit()
        self._campo_nome.setPlaceholderText(t("nome"))
        layout.addRow(t("nome") + "*:", self._campo_nome)

        layout.addRow(QLabel(t("lore")))
        self._area_lore = QTextEdit()
        self._area_lore.setMinimumHeight(120)
        layout.addRow(self._area_lore)

        layout.addRow(QLabel(t("descrizione")))
        self._area_desc = QTextEdit()
        self._area_desc.setMaximumHeight(80)
        layout.addRow(self._area_desc)

        return w

    def _tab_mappe(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        nota = QLabel(t("seleziona_mappa"))
        nota.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(nota)

        self._lista_mappe = QListWidget()
        self._lista_mappe.setStyleSheet("""
            QListWidget { background-color: #3a3a4a; border: 1px solid #555570;
                          border-radius: 4px; }
            QListWidget::item { padding: 8px; font-size: 12px; }
            QListWidget::item:selected { background-color: #5a5a90; }
        """)
        layout.addWidget(self._lista_mappe, stretch=1)

        riga_btn = QHBoxLayout()
        riga_btn.setSpacing(8)

        btn_nuova = QPushButton(t("nuova_mappa"))
        btn_nuova.setMinimumHeight(38)
        btn_nuova.clicked.connect(self._aggiungi_mappa)
        riga_btn.addWidget(btn_nuova)

        btn_apri = QPushButton(t("apri_editor"))
        btn_apri.setMinimumHeight(38)
        btn_apri.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        btn_apri.setStyleSheet("background-color: #5a5a90;")
        btn_apri.clicked.connect(self._apri_editor_selezionato)
        riga_btn.addWidget(btn_apri)

        riga_btn.addStretch()
        layout.addLayout(riga_btn)

        if self.mondo_id:
            self._aggiorna_lista_mappe()

        return w

    def _aggiorna_lista_mappe(self):
        self._lista_mappe.clear()
        mappe = GestoreMondo.mappe(self.mondo_id)
        if not mappe:
            item = QListWidgetItem(t("nessuna_mappa"))
            item.setForeground(Qt.GlobalColor.gray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self._lista_mappe.addItem(item)
        else:
            for mappa in mappe:
                from mappa.livelli import GestoreMultilivello
                nome_livello = GestoreMultilivello(None).nome_livello(mappa['livello']) \
                    if hasattr(GestoreMultilivello, 'nome_livello') else f"livello {mappa['livello']}"
                testo = f"🗺️  {mappa['nome']}  ({nome_livello})  —  {mappa['data_modifica']}"
                item = QListWidgetItem(testo)
                item.setData(Qt.ItemDataRole.UserRole, mappa["id"])
                self._lista_mappe.addItem(item)

    def _aggiungi_mappa(self):
        if not self.mondo_id:
            QMessageBox.warning(self, t("errore"), t("salva_prima"))
            return
        nome, ok = QInputDialog.getText(self, t("nuova_mappa"), t("nome_mappa"))
        if ok and nome.strip():
            GestoreMondo.aggiungi_mappa(self.mondo_id, nome.strip())
            self._aggiorna_lista_mappe()

    def _apri_editor_selezionato(self):
        item = self._lista_mappe.currentItem()
        mappa_id = item.data(Qt.ItemDataRole.UserRole) if item else None

        if not mappa_id:
            QMessageBox.information(self, t("errore"), t("seleziona_mappa"))
            return

        cartella_radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        map_py = os.path.join(cartella_radice, "mappa", "map.py")

        subprocess.Popen(
            [sys.executable, map_py, str(mappa_id)],
            cwd=cartella_radice
        )

    def _popola(self):
        self._campo_nome.setText(self._dati.get("nome", ""))
        self._area_lore.setPlainText(self._dati.get("lore", ""))
        self._area_desc.setPlainText(self._dati.get("descrizione", ""))

    def _salva(self):
        nome = self._campo_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, t("errore"), t("campo_obbligatorio"))
            return

        lore = self._area_lore.toPlainText()
        desc = self._area_desc.toPlainText()

        if self.mondo_id is None:
            self.mondo_id = GestoreMondo.crea(nome, lore, desc)
        else:
            GestoreMondo.aggiorna(self.mondo_id, nome, lore, desc)

        self.mondo_salvato.emit(self.mondo_id)
        QMessageBox.information(self, t("salva"), t("mondo_salvato").format(n=nome))
        self.accept()
