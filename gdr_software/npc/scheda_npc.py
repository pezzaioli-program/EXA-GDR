"""
npc/scheda_npc.py — Finestra PyQt per visualizzare e modificare scheda NPC/Nemico
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QPushButton,
    QComboBox, QGroupBox
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from lingua.gestore import t, lingua_corrente


class SchedaNPC(QDialog):

    scheda_aggiornata = pyqtSignal(dict)

    DIFF_IT = ["facile", "medio", "difficile", "boss"]
    DIFF_EN = ["easy",   "medium", "hard",     "boss"]

    def __init__(self, dati: dict, parent=None):
        super().__init__(parent)
        self._dati    = dict(dati)
        is_nemico     = dati.get("tipo") == "nemico"
        self.setWindowTitle(t("scheda_nemico") if is_nemico else t("scheda_npc"))
        self.setMinimumWidth(400)
        self._costruisci_ui(is_nemico)
        self._popola()

    def _costruisci_ui(self, is_nemico: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Identità
        grp_id = QGroupBox(t("nemico_titolo") if is_nemico else t("npc_titolo"))
        form_id = QFormLayout(grp_id)

        self._campo_nome   = QLineEdit()
        self._campo_razza  = QLineEdit()
        self._campo_classe = QLineEdit()
        form_id.addRow(t("nome_npc") + ":", self._campo_nome)
        form_id.addRow(t("razza") + ":",    self._campo_razza)
        form_id.addRow(t("classe") + ":",   self._campo_classe)

        if is_nemico:
            self._combo_diff = QComboBox()
            diff_list = self.DIFF_EN if lingua_corrente() == "en" else self.DIFF_IT
            self._combo_diff.addItems(diff_list)
            form_id.addRow(t("tipo") + ":", self._combo_diff)

        layout.addWidget(grp_id)

        # Combattimento
        grp_combat = QGroupBox("⚔️")
        form_c = QFormLayout(grp_combat)
        self._spin_pf = QSpinBox(); self._spin_pf.setRange(1, 999)
        self._spin_ca = QSpinBox(); self._spin_ca.setRange(1, 30)
        form_c.addRow(t("pf") + ":", self._spin_pf)
        form_c.addRow(t("ca") + ":", self._spin_ca)
        layout.addWidget(grp_combat)

        # Statistiche
        grp_stat = QGroupBox("📊")
        griglia  = QHBoxLayout(grp_stat)
        self._spin_stat = {}
        for chiave in ["for", "des", "cos", "int", "sag", "car"]:
            col = QVBoxLayout()
            col.addWidget(QLabel(t(chiave)))
            spin = QSpinBox(); spin.setRange(1, 30); spin.setFixedWidth(55)
            self._spin_stat[chiave] = spin
            col.addWidget(spin)
            griglia.addLayout(col)
        layout.addWidget(grp_stat)

        # Pulsanti
        riga = QHBoxLayout()
        riga.addStretch()
        btn_ann = QPushButton(t("annulla"))
        btn_ann.clicked.connect(self.reject)
        riga.addWidget(btn_ann)
        btn_salva = QPushButton(t("salva"))
        btn_salva.setDefault(True)
        btn_salva.clicked.connect(self._salva)
        riga.addWidget(btn_salva)
        layout.addLayout(riga)

    def _popola(self):
        d = self._dati
        self._campo_nome.setText(d.get("nome", ""))
        self._campo_razza.setText(d.get("razza", ""))
        self._campo_classe.setText(d.get("classe", ""))
        self._spin_pf.setValue(d.get("pf", 10))
        self._spin_ca.setValue(d.get("ca", 10))
        if hasattr(self, "_combo_diff"):
            diff = d.get("difficolta", "medio")
            idx  = self._combo_diff.findText(diff)
            if idx >= 0:
                self._combo_diff.setCurrentIndex(idx)
        stats = d.get("statistiche", {})
        for k, spin in self._spin_stat.items():
            spin.setValue(stats.get(k, 10))

    def _salva(self):
        self._dati["nome"]   = self._campo_nome.text().strip()
        self._dati["razza"]  = self._campo_razza.text().strip()
        self._dati["classe"] = self._campo_classe.text().strip()
        self._dati["pf"]     = self._spin_pf.value()
        self._dati["pf_max"] = self._spin_pf.value()
        self._dati["ca"]     = self._spin_ca.value()
        if hasattr(self, "_combo_diff"):
            self._dati["difficolta"] = self._combo_diff.currentText()
        for k, spin in self._spin_stat.items():
            self._dati["statistiche"][k] = spin.value()
        self.scheda_aggiornata.emit(self._dati)
        self.accept()
