"""
shop/shop_player.py — Shop del Player: skin personaggio e dadi
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QWidget, QScrollArea,
    QGridLayout, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from shop.acquisti import acquista, possiede, lista_posseduti

# Catalogo skin disponibili nello shop
CATALOGO_SKIN_DADI = [
    {"id": "skin_fuoco",    "nome": "Dado del Fuoco",    "prezzo": "2.99€",
     "descrizione": "Dadi con effetti fiammeggianti",   "anteprima": None},
    {"id": "skin_ghiaccio", "nome": "Dado del Ghiaccio", "prezzo": "2.99€",
     "descrizione": "Dadi con cristalli di ghiaccio",   "anteprima": None},
    {"id": "skin_arcana",   "nome": "Dado Arcano",       "prezzo": "3.99€",
     "descrizione": "Dadi con rune luminescenti",       "anteprima": None},
    {"id": "skin_ossa",     "nome": "Dado d'Ossa",       "prezzo": "1.99€",
     "descrizione": "Dadi in stile scheletrico",        "anteprima": None},
    {"id": "skin_oro",      "nome": "Dado d'Oro",        "prezzo": "4.99€",
     "descrizione": "Dadi dorati premium",              "anteprima": None},
]

CATALOGO_SKIN_PERSONAGGIO = [
    {"id": "skin_guerriero_rosso",  "nome": "Guerriero Cremisi",  "prezzo": "1.99€",
     "descrizione": "Token guerriero con armatura rossa",         "anteprima": None},
    {"id": "skin_mago_blu",         "nome": "Mago Celeste",       "prezzo": "1.99€",
     "descrizione": "Token mago con mantello blu",                "anteprima": None},
    {"id": "skin_ladro_ombra",      "nome": "Ladro dell'Ombra",   "prezzo": "2.49€",
     "descrizione": "Token ladro semi-trasparente",               "anteprima": None},
    {"id": "skin_paladino_luce",    "nome": "Paladino della Luce","prezzo": "2.49€",
     "descrizione": "Token paladino con aureola dorata",          "anteprima": None},
]


class ShopPlayer(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shop — Skin e Contenuti")
        self.setMinimumSize(700, 520)
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🛒  Shop")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        nota = QLabel("Acquista skin per personalizzare i tuoi dadi e il tuo personaggio.")
        nota.setStyleSheet("color: #888888;")
        layout.addWidget(nota)

        tabs = QTabWidget()
        tabs.addTab(self._crea_tab_catalogo(CATALOGO_SKIN_DADI, "skin_dado"),
                    "🎲 Skin Dadi")
        tabs.addTab(self._crea_tab_catalogo(CATALOGO_SKIN_PERSONAGGIO, "skin_personaggio"),
                    "👤 Skin Personaggio")
        tabs.addTab(self._crea_tab_posseduti(), "📦 I miei acquisti")
        layout.addWidget(tabs)

        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(self.accept)
        layout.addWidget(btn_chiudi, alignment=Qt.AlignmentFlag.AlignRight)

    def _crea_tab_catalogo(self, catalogo: list, tipo: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia = QGridLayout(contenuto)
        griglia.setSpacing(12)

        for i, item in enumerate(catalogo):
            card = self._crea_card(item, tipo)
            griglia.addWidget(card, i // 2, i % 2)

        scroll.setWidget(contenuto)
        return scroll

    def _crea_card(self, item: dict, tipo: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #3a3a4a; border-radius: 8px;
                     border: 1px solid #555570; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Anteprima (placeholder colorato)
        anteprima = QLabel()
        anteprima.setFixedSize(80, 80)
        anteprima.setAlignment(Qt.AlignmentFlag.AlignCenter)
        anteprima.setStyleSheet("background-color: #555570; border-radius: 40px;")
        anteprima.setText("🎲" if "dado" in tipo else "👤")
        anteprima.setFont(QFont("Arial", 24))
        layout.addWidget(anteprima, alignment=Qt.AlignmentFlag.AlignCenter)

        nome = QLabel(item["nome"])
        nome.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(nome)

        desc = QLabel(item["descrizione"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        prezzo = QLabel(item["prezzo"])
        prezzo.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        prezzo.setStyleSheet("color: #ffdd44;")
        prezzo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prezzo)

        gia_acquistato = possiede(item["id"])
        if gia_acquistato:
            btn = QPushButton("✓ Già acquistato")
            btn.setEnabled(False)
            btn.setStyleSheet("color: #80ff80;")
        else:
            btn = QPushButton(f"Acquista — {item['prezzo']}")
            btn.clicked.connect(
                lambda checked, it=item, t=tipo: self._acquista(it, t))

        layout.addWidget(btn)
        return card

    def _acquista(self, item: dict, tipo: str):
        risposta = QMessageBox.question(
            self, "Conferma acquisto",
            f"Acquistare '{item['nome']}' per {item['prezzo']}?\n\n"
            f"(In questa versione demo l'acquisto è gratuito)"
        )
        if risposta == QMessageBox.StandardButton.Yes:
            ok, msg = acquista(item["id"], tipo)
            if ok:
                QMessageBox.information(self, "Acquistato!",
                    f"'{item['nome']}' aggiunto ai tuoi acquisti!\n"
                    f"Puoi equipaggiarlo dalla sezione Dadi.")
                self._aggiorna()
            else:
                QMessageBox.warning(self, "Errore", msg)

    def _crea_tab_posseduti(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("I tuoi acquisti:"))

        self._lista_posseduti = QLabel()
        self._lista_posseduti.setWordWrap(True)
        self._aggiorna_lista_posseduti()
        layout.addWidget(self._lista_posseduti)
        layout.addStretch()
        return widget

    def _aggiorna_lista_posseduti(self):
        posseduti = lista_posseduti()
        if not posseduti:
            self._lista_posseduti.setText("Nessun acquisto ancora.")
        else:
            righe = [f"• {a['asset_id']} ({a['tipo_asset']})  —  {a['data_acquisto']}"
                     for a in posseduti]
            self._lista_posseduti.setText("\n".join(righe))

    def _aggiorna(self):
        self.close()
        nuovo = ShopPlayer(self.parent())
        nuovo.exec()
