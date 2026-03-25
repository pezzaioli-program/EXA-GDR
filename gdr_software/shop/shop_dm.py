"""
shop/shop_dm.py — Shop del DM: asset mappa, mappe prefab, manuali
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QWidget, QScrollArea,
    QGridLayout, QMessageBox, QFrame, QTextEdit,
    QListWidget, QListWidgetItem, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from shop.acquisti import acquista, possiede, lista_posseduti

CATALOGO_ASSET_MAPPA = [
    {"id": "asset_drago",       "nome": "Token Drago",        "prezzo": "0.99€",
     "descrizione": "Token PNG ad alta risoluzione di un drago rosso"},
    {"id": "asset_torre",       "nome": "Torre del Mago",     "prezzo": "1.49€",
     "descrizione": "Struttura torre con effetto magico"},
    {"id": "asset_dungeon_set", "nome": "Set Dungeon Base",   "prezzo": "4.99€",
     "descrizione": "20 asset per dungeon: porte, trappole, tesori"},
    {"id": "asset_foresta_set", "nome": "Set Foresta Oscura", "prezzo": "3.99€",
     "descrizione": "15 asset per foresta: alberi dettagliati, funghi, rovine"},
    {"id": "asset_citta_set",   "nome": "Set Città Medievale","prezzo": "5.99€",
     "descrizione": "30 asset urbani: case, mercato, stalla, taverna"},
]

CATALOGO_MAPPE_PREFAB = [
    {"id": "mappa_dungeon_base", "nome": "Dungeon del Re Lich",  "prezzo": "2.99€",
     "descrizione": "Dungeon a 3 livelli con trappole e boss finale. 15×12 esagoni.",
     "colonne": 15, "righe": 12},
    {"id": "mappa_foresta",      "nome": "Foresta Maledetta",    "prezzo": "1.99€",
     "descrizione": "Foresta densa con percorsi segreti. 20×15 esagoni.",
     "colonne": 20, "righe": 15},
    {"id": "mappa_citta",        "nome": "Porto di Meridian",    "prezzo": "3.49€",
     "descrizione": "Città portuale con quartieri distinti. 25×18 esagoni.",
     "colonne": 25, "righe": 18},
    {"id": "mappa_castello",     "nome": "Castello Darkhold",    "prezzo": "2.49€",
     "descrizione": "Castello con corte interna e prigioni. 18×14 esagoni.",
     "colonne": 18, "righe": 14},
]

CATALOGO_MANUALI = [
    {"id": "manuale_base",     "nome": "Manuale Base GDR",  "prezzo": "Gratis",
     "descrizione": "Regole base del sistema GDR incluso nel software."},
    {"id": "manuale_avanzato", "nome": "Manuale Avanzato",  "prezzo": "7.99€",
     "descrizione": "Regole avanzate: magia complessa, multiclasse, oggetti leggendari."},
    {"id": "manuale_homebrew", "nome": "Guida Homebrew",    "prezzo": "4.99€",
     "descrizione": "Crea le tue classi, razze e incantesimi personalizzati."},
]


def _disegna_prefab(griglia, prefab_id: str):
    """
    Disegna una mappa prefab pre-costruita sulla griglia.
    Ogni prefab ha un layout predefinito realistico.
    """
    from mappa.map import Esagono
    celle = griglia.celle
    col   = griglia.colonne
    rig   = griglia.righe

    if prefab_id == "mappa_dungeon_base":
        # Dungeon del Re Lich — corridoi di pietra con stanze
        for (q, r), e in celle.items():
            e.terreno = "vuoto"
        # Stanza centrale
        for q in range(5, 10):
            for r in range(4, 8):
                if (q, r) in celle:
                    celle[(q,r)].terreno = "pietra_scura" if hasattr(e, "terreno") else "montagna"
        # Corridoi
        for q in range(0, col):
            if (q, 5) in celle: celle[(q,5)].terreno = "montagna"
            if (q, 6) in celle: celle[(q,6)].terreno = "montagna"
        for r in range(0, rig):
            if (7, r) in celle: celle[(7,r)].terreno = "montagna"
        # Bordi come acqua (fossato)
        for q in range(col):
            for r in [0, rig-1]:
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"
        for r in range(rig):
            for q in [0, col-1]:
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"
        # Alcune celle foresta = trappole visive
        import random
        random.seed(42)
        for (q,r), e in celle.items():
            if e.terreno == "vuoto" and random.random() < 0.08:
                e.terreno = "foresta"

    elif prefab_id == "mappa_foresta":
        # Foresta Maledetta — alberi fitti con sentieri
        for (q,r), e in celle.items():
            e.terreno = "foresta"
        # Sentiero principale orizzontale
        r_mid = rig // 2
        for q in range(col):
            for dr in [-1, 0, 1]:
                if (q, r_mid+dr) in celle:
                    celle[(q, r_mid+dr)].terreno = "pianura"
        # Sentiero verticale
        q_mid = col // 2
        for r in range(rig):
            for dq in [0, 1]:
                if (q_mid+dq, r) in celle:
                    celle[(q_mid+dq, r)].terreno = "pianura"
        # Radura centrale
        for q in range(q_mid-3, q_mid+4):
            for r in range(r_mid-3, r_mid+4):
                if (q,r) in celle: celle[(q,r)].terreno = "pianura"
        # Lago
        for q in range(3, 7):
            for r in range(2, 6):
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"

    elif prefab_id == "mappa_citta":
        # Porto di Meridian — città con strade e porto
        for (q,r), e in celle.items():
            e.terreno = "pianura"
        # Porto (acqua su un lato)
        for q in range(col):
            for r in range(rig-4, rig):
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"
        # Strade principali
        for q in range(col):
            for r_s in [3, 7, 11]:
                if (q, r_s) in celle: celle[(q,r_s)].terreno = "deserto"
        for r in range(rig):
            for q_s in [4, 9, 14, 19]:
                if (q_s, r) in celle: celle[(q_s,r)].terreno = "deserto"
        # Zona montagna (collina)
        for q in range(0, 5):
            for r in range(0, 5):
                if (q,r) in celle: celle[(q,r)].terreno = "montagna"

    elif prefab_id == "mappa_castello":
        # Castello Darkhold — castello con fossato e cortile
        for (q,r), e in celle.items():
            e.terreno = "pianura"
        # Fossato esterno
        for q in range(col):
            for r in [1, 2, rig-3, rig-2]:
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"
        for r in range(rig):
            for q in [1, 2, col-3, col-2]:
                if (q,r) in celle: celle[(q,r)].terreno = "acqua"
        # Mura (montagna)
        for q in range(3, col-3):
            for r in [3, rig-4]:
                if (q,r) in celle: celle[(q,r)].terreno = "montagna"
        for r in range(3, rig-3):
            for q in [3, col-4]:
                if (q,r) in celle: celle[(q,r)].terreno = "montagna"
        # Cortile interno
        for q in range(4, col-4):
            for r in range(4, rig-4):
                if (q,r) in celle: celle[(q,r)].terreno = "deserto"
        # Torre centrale
        q_c, r_c = col//2, rig//2
        for dq in range(-2, 3):
            for dr in range(-2, 3):
                if (q_c+dq, r_c+dr) in celle:
                    celle[(q_c+dq, r_c+dr)].terreno = "montagna"


class ShopDM(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Shop DM — Asset, Mappe e Manuali")
        self.setMinimumSize(760, 580)
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🛒  Shop DM")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        nota = QLabel(
            "Acquista asset grafici, mappe prefab e manuali.\n"
            "Le mappe prefab vengono caricate direttamente in un tuo mondo."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #888888;")
        layout.addWidget(nota)

        tabs = QTabWidget()
        tabs.addTab(self._crea_tab_griglia(CATALOGO_ASSET_MAPPA, "oggetto_mappa"),
                    "🗺️ Asset Mappa")
        tabs.addTab(self._crea_tab_mappe_prefab(), "📜 Mappe Prefab")
        tabs.addTab(self._crea_tab_griglia(CATALOGO_MANUALI, "manuale"),
                    "📚 Manuali")
        tabs.addTab(self._crea_tab_posseduti(), "📦 I miei acquisti")
        layout.addWidget(tabs)

        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(self.accept)
        layout.addWidget(btn_chiudi, alignment=Qt.AlignmentFlag.AlignRight)

    # ── Tab generico a griglia ────────────────────────────────────────────────

    def _crea_tab_griglia(self, catalogo: list, tipo: str) -> QWidget:
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

        icona_map = {"oggetto_mappa": "🗺️", "mappa_prefab": "📜", "manuale": "📚"}
        icona = QLabel(icona_map.get(tipo, "📦"))
        icona.setFont(QFont("Arial", 28))
        icona.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icona)

        nome = QLabel(item["nome"])
        nome.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(nome)

        desc = QLabel(item["descrizione"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addWidget(desc)

        prezzo_str = item["prezzo"]
        prezzo = QLabel(prezzo_str)
        prezzo.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        prezzo.setStyleSheet("color: #80ff80;" if prezzo_str == "Gratis" else "color: #ffdd44;")
        prezzo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prezzo)

        if possiede(item["id"]):
            btn = QPushButton("✓ Già acquistato")
            btn.setEnabled(False)
            btn.setStyleSheet("color: #80ff80;")
        elif prezzo_str == "Gratis":
            btn = QPushButton("Ottieni gratis")
            btn.clicked.connect(lambda checked, it=item, t=tipo: self._acquista(it, t))
        else:
            btn = QPushButton(f"Acquista — {prezzo_str}")
            btn.clicked.connect(lambda checked, it=item, t=tipo: self._acquista(it, t))

        layout.addWidget(btn)
        return card

    def _acquista(self, item: dict, tipo: str):
        gratuito = item["prezzo"] == "Gratis"
        msg_conferma = (
            f"Ottenere '{item['nome']}' gratuitamente?"
            if gratuito else
            f"Acquistare '{item['nome']}' per {item['prezzo']}?\n(Demo: acquisto gratuito)"
        )
        risposta = QMessageBox.question(self, "Conferma", msg_conferma)
        if risposta != QMessageBox.StandardButton.Yes:
            return

        ok, msg = acquista(item["id"], tipo)
        if ok:
            QMessageBox.information(self, "Fatto!", f"'{item['nome']}' aggiunto ai tuoi acquisti!")
            self._aggiorna()
        else:
            QMessageBox.warning(self, "Errore", msg)

    # ── Tab mappe prefab (con caricamento nel mondo) ──────────────────────────

    def _crea_tab_mappe_prefab(self) -> QWidget:
        """
        Tab speciale per le mappe prefab: dopo l'acquisto chiede
        in quale mondo caricarla e la crea direttamente nel database.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia = QGridLayout(contenuto)
        griglia.setSpacing(12)

        for i, item in enumerate(CATALOGO_MAPPE_PREFAB):
            card = self._crea_card_prefab(item)
            griglia.addWidget(card, i // 2, i % 2)

        scroll.setWidget(contenuto)
        return scroll

    def _crea_card_prefab(self, item: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #3a3a4a; border-radius: 8px;
                     border: 1px solid #555570; }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)

        icona = QLabel("📜")
        icona.setFont(QFont("Arial", 28))
        icona.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icona)

        nome = QLabel(item["nome"])
        nome.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        nome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(nome)

        desc = QLabel(item["descrizione"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        layout.addWidget(desc)

        prezzo = QLabel(item["prezzo"])
        prezzo.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        prezzo.setStyleSheet("color: #ffdd44;")
        prezzo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prezzo)

        gia = possiede(item["id"])

        if gia:
            # Già acquistata: mostra solo il pulsante "Carica in un mondo"
            btn_acquista = QPushButton("✓ Già acquistata")
            btn_acquista.setEnabled(False)
            btn_acquista.setStyleSheet("color: #80ff80;")
            layout.addWidget(btn_acquista)

            btn_carica = QPushButton("📥  Carica in un mondo")
            btn_carica.clicked.connect(
                lambda checked, it=item: self._carica_prefab_in_mondo(it))
            layout.addWidget(btn_carica)
        else:
            btn = QPushButton(f"Acquista — {item['prezzo']}")
            btn.clicked.connect(
                lambda checked, it=item: self._acquista_e_carica_prefab(it))
            layout.addWidget(btn)

        return card

    def _acquista_e_carica_prefab(self, item: dict):
        """Acquista la mappa prefab e poi chiede dove caricarla."""
        risposta = QMessageBox.question(
            self, "Conferma acquisto",
            f"Acquistare '{item['nome']}' per {item['prezzo']}?\n"
            f"(Demo: acquisto gratuito)\n\n"
            f"Dopo l'acquisto potrai caricarla in uno dei tuoi mondi."
        )
        if risposta != QMessageBox.StandardButton.Yes:
            return

        ok, msg = acquista(item["id"], "mappa_prefab")
        if not ok:
            QMessageBox.warning(self, "Errore", msg)
            return

        self._carica_prefab_in_mondo(item)

    def _carica_prefab_in_mondo(self, item: dict):
        """
        Chiede in quale mondo caricare la mappa prefab e la crea nel DB.
        La mappa viene creata come duplicato — il DM può modificarla
        senza alterare l'originale (PDR §16).
        """
        from mondi.mondo import GestoreMondo
        from auth.sessione_utente import utente_corrente

        utente = utente_corrente()
        mondi = GestoreMondo.lista()

        if not mondi:
            QMessageBox.warning(
                self, "Nessun mondo",
                "Non hai ancora nessun mondo.\n"
                "Crea prima un mondo dalla dashboard, poi carica la mappa."
            )
            return

        # Mostra la lista dei mondi per scegliere
        nomi_mondi = [m["nome"] for m in mondi]
        scelta, ok = QInputDialog.getItem(
            self,
            "Scegli il mondo",
            f"In quale mondo vuoi caricare '{item['nome']}'?",
            nomi_mondi,
            editable=False
        )
        if not ok:
            return

        mondo_scelto = mondi[nomi_mondi.index(scelta)]

        # Crea la mappa nel mondo scelto con le dimensioni della prefab
        mappa_id = GestoreMondo.aggiungi_mappa(
            mondo_scelto["id"],
            f"{item['nome']} (prefab)",
            livello=0
        )

        from mappa.map import Griglia
        from mappa.esporta import salva_griglia_nel_db
        from config import HEX_DIMENSIONE, PANNELLO_LARGHEZZA, TERRENI

        colonne = item.get("colonne", 15)
        righe   = item.get("righe", 12)
        griglia = Griglia(
            colonne=colonne, righe=righe,
            dimensione=HEX_DIMENSIONE,
            offset_x=PANNELLO_LARGHEZZA + 20, offset_y=40,
        )

        # Genera una mappa pre-disegnata in base al tipo
        _disegna_prefab(griglia, item["id"])
        salva_griglia_nel_db(mappa_id, griglia)

        QMessageBox.information(
            self,
            "Mappa caricata!",
            f"'{item['nome']}' è stata aggiunta al mondo '{scelta}'.\n\n"
            f"Aprila da: Dashboard → I miei Mondi → {scelta} → "
            f"Modifica selezionato → Mappe → {item['nome']} (prefab) → Apri Editor"
        )
        self._aggiorna()

    # ── Tab posseduti ─────────────────────────────────────────────────────────

    def _crea_tab_posseduti(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("I tuoi acquisti:"))
        self._testo_posseduti = QTextEdit()
        self._testo_posseduti.setReadOnly(True)
        self._aggiorna_testo_posseduti()
        layout.addWidget(self._testo_posseduti)
        return widget

    def _aggiorna_testo_posseduti(self):
        posseduti = lista_posseduti()
        if not posseduti:
            self._testo_posseduti.setPlainText("Nessun acquisto ancora.")
            return
        righe = []
        for tipo, label in [("oggetto_mappa", "Asset Mappa"),
                             ("mappa_prefab",  "Mappe Prefab"),
                             ("manuale",        "Manuali")]:
            gruppo = [a for a in posseduti if a["tipo_asset"] == tipo]
            if gruppo:
                righe.append(f"── {label} ──")
                for a in gruppo:
                    righe.append(f"  • {a['asset_id']}  ({a['data_acquisto']})")
                righe.append("")
        self._testo_posseduti.setPlainText("\n".join(righe))

    def _aggiorna(self):
        self.close()
        ShopDM(self.parent()).exec()
