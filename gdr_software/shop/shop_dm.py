"""
shop/shop_dm.py — Shop del DM: asset mappa, mappe prefab, manuali,
                               tileset terreni, oggetti esplorabili
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QWidget, QScrollArea,
    QGridLayout, QMessageBox, QFrame, QTextEdit, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from shop.acquisti import acquista, possiede, lista_posseduti
from lingua.gestore import t

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
     "descrizione": "Dungeon a 3 livelli con trappole e boss finale.",
     "colonne": 15, "righe": 12},
    {"id": "mappa_foresta",      "nome": "Foresta Maledetta",    "prezzo": "1.99€",
     "descrizione": "Foresta densa con percorsi segreti.",
     "colonne": 20, "righe": 15},
    {"id": "mappa_citta",        "nome": "Porto di Meridian",    "prezzo": "3.49€",
     "descrizione": "Città portuale con quartieri distinti.",
     "colonne": 25, "righe": 18},
    {"id": "mappa_castello",     "nome": "Castello Darkhold",    "prezzo": "2.49€",
     "descrizione": "Castello con corte interna e prigioni.",
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
    celle = griglia.celle
    col   = griglia.colonne
    rig   = griglia.righe

    if prefab_id == "mappa_dungeon_base":
        for (q, r), e in celle.items():
            e.terreno = "vuoto"
        for q in range(5, 10):
            for r in range(4, 8):
                if (q, r) in celle: celle[(q, r)].terreno = "montagna"
        for q in range(0, col):
            if (q, 5) in celle: celle[(q, 5)].terreno = "montagna"
            if (q, 6) in celle: celle[(q, 6)].terreno = "montagna"
        for r in range(0, rig):
            if (7, r) in celle: celle[(7, r)].terreno = "montagna"
        for q in range(col):
            for r in [0, rig - 1]:
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"
        for r in range(rig):
            for q in [0, col - 1]:
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"
        import random; random.seed(42)
        for (q, r), e in celle.items():
            if e.terreno == "vuoto" and random.random() < 0.08:
                e.terreno = "foresta"

    elif prefab_id == "mappa_foresta":
        for (q, r), e in celle.items():
            e.terreno = "foresta"
        r_mid = rig // 2
        for q in range(col):
            for dr in [-1, 0, 1]:
                if (q, r_mid + dr) in celle:
                    celle[(q, r_mid + dr)].terreno = "pianura"
        q_mid = col // 2
        for r in range(rig):
            for dq in [0, 1]:
                if (q_mid + dq, r) in celle:
                    celle[(q_mid + dq, r)].terreno = "pianura"
        for q in range(q_mid - 3, q_mid + 4):
            for r in range(r_mid - 3, r_mid + 4):
                if (q, r) in celle: celle[(q, r)].terreno = "pianura"
        for q in range(3, 7):
            for r in range(2, 6):
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"

    elif prefab_id == "mappa_citta":
        for (q, r), e in celle.items():
            e.terreno = "pianura"
        for q in range(col):
            for r in range(rig - 4, rig):
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"
        for q in range(col):
            for r_s in [3, 7, 11]:
                if (q, r_s) in celle: celle[(q, r_s)].terreno = "deserto"
        for r in range(rig):
            for q_s in [4, 9, 14, 19]:
                if (q_s, r) in celle: celle[(q_s, r)].terreno = "deserto"
        for q in range(0, 5):
            for r in range(0, 5):
                if (q, r) in celle: celle[(q, r)].terreno = "montagna"

    elif prefab_id == "mappa_castello":
        for (q, r), e in celle.items():
            e.terreno = "pianura"
        for q in range(col):
            for r in [1, 2, rig - 3, rig - 2]:
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"
        for r in range(rig):
            for q in [1, 2, col - 3, col - 2]:
                if (q, r) in celle: celle[(q, r)].terreno = "acqua"
        for q in range(3, col - 3):
            for r in [3, rig - 4]:
                if (q, r) in celle: celle[(q, r)].terreno = "montagna"
        for r in range(3, rig - 3):
            for q in [3, col - 4]:
                if (q, r) in celle: celle[(q, r)].terreno = "montagna"
        for q in range(4, col - 4):
            for r in range(4, rig - 4):
                if (q, r) in celle: celle[(q, r)].terreno = "deserto"
        q_c, r_c = col // 2, rig // 2
        for dq in range(-2, 3):
            for dr in range(-2, 3):
                if (q_c + dq, r_c + dr) in celle:
                    celle[(q_c + dq, r_c + dr)].terreno = "montagna"


# ── Stile card condiviso ───────────────────────────────────────────────────────
CARD_STYLE = """
    QFrame { background-color: #3a3a4a; border-radius: 8px;
             border: 1px solid #555570; }
"""


class ShopDM(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("shop_titolo"))
        self.setMinimumSize(800, 600)
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("🛒  " + t("shop_dm"))
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        nota = QLabel(
            "Acquista asset grafici, mappe prefab, manuali, "
            "tileset e oggetti esplorabili."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #888888;")
        layout.addWidget(nota)

        tabs = QTabWidget()
        tabs.addTab(self._crea_tab_griglia(CATALOGO_ASSET_MAPPA, "oggetto_mappa"),
                    "🗺️ Asset Mappa")
        tabs.addTab(self._crea_tab_mappe_prefab(),  "📜 Mappe Prefab")
        tabs.addTab(self._crea_tab_griglia(CATALOGO_MANUALI, "manuale"),
                    "📚 Manuali")
        tabs.addTab(self._crea_tab_tileset(),        "🎨 Tileset Mappa")
        tabs.addTab(self._crea_tab_esplorabili(),    "🏠 Oggetti Esplorabili")
        tabs.addTab(self._crea_tab_posseduti(),      t("i_miei_acquisti"))
        layout.addWidget(tabs)

        btn_chiudi = QPushButton(t("chiudi"))
        btn_chiudi.clicked.connect(self.accept)
        layout.addWidget(btn_chiudi, alignment=Qt.AlignmentFlag.AlignRight)

    # ── Tab generico a griglia ────────────────────────────────────────────────

    def _crea_tab_griglia(self, catalogo: list, tipo: str) -> QWidget:
        scroll    = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia   = QGridLayout(contenuto)
        griglia.setSpacing(12)
        for i, item in enumerate(catalogo):
            griglia.addWidget(self._crea_card(item, tipo), i // 2, i % 2)
        scroll.setWidget(contenuto)
        return scroll

    def _crea_card(self, item: dict, tipo: str) -> QWidget:
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
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
        prezzo.setStyleSheet(
            "color: #80ff80;" if prezzo_str == "Gratis" else "color: #ffdd44;")
        prezzo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(prezzo)

        if possiede(item["id"]):
            btn = QPushButton(t("gia_acquistato"))
            btn.setEnabled(False)
            btn.setStyleSheet("color: #80ff80;")
        elif prezzo_str == "Gratis":
            btn = QPushButton("Ottieni gratis")
            btn.clicked.connect(
                lambda checked, it=item, tp=tipo: self._acquista(it, tp))
        else:
            btn = QPushButton(f"{t('acquista')} — {prezzo_str}")
            btn.clicked.connect(
                lambda checked, it=item, tp=tipo: self._acquista(it, tp))
        layout.addWidget(btn)
        return card

    def _acquista(self, item: dict, tipo: str):
        gratuito = item["prezzo"] == "Gratis"
        msg = (f"Ottenere '{item['nome']}' gratuitamente?"
               if gratuito else
               f"Acquistare '{item['nome']}' per {item['prezzo']}?\n(Demo: gratuito)")
        if QMessageBox.question(self, t("conferma_acquisto"), msg) != \
                QMessageBox.StandardButton.Yes:
            return
        ok, msg = acquista(item["id"], tipo)
        if ok:
            QMessageBox.information(self, "OK", f"'{item['nome']}' aggiunto!")
            self._aggiorna()
        else:
            QMessageBox.warning(self, t("errore"), msg)

    # ── Tab mappe prefab ──────────────────────────────────────────────────────

    def _crea_tab_mappe_prefab(self) -> QWidget:
        scroll    = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia   = QGridLayout(contenuto)
        griglia.setSpacing(12)
        for i, item in enumerate(CATALOGO_MAPPE_PREFAB):
            griglia.addWidget(self._crea_card_prefab(item), i // 2, i % 2)
        scroll.setWidget(contenuto)
        return scroll

    def _crea_card_prefab(self, item: dict) -> QWidget:
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
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

        if possiede(item["id"]):
            btn_acq = QPushButton(t("gia_acquistato"))
            btn_acq.setEnabled(False)
            btn_acq.setStyleSheet("color: #80ff80;")
            layout.addWidget(btn_acq)
            btn_car = QPushButton("📥  " + t("carica_in_mondo"))
            btn_car.clicked.connect(
                lambda checked, it=item: self._carica_prefab_in_mondo(it))
            layout.addWidget(btn_car)
        else:
            btn = QPushButton(f"{t('acquista')} — {item['prezzo']}")
            btn.clicked.connect(
                lambda checked, it=item: self._acquista_e_carica_prefab(it))
            layout.addWidget(btn)
        return card

    def _acquista_e_carica_prefab(self, item: dict):
        if QMessageBox.question(
            self, t("conferma_acquisto"),
            f"Acquistare '{item['nome']}' per {item['prezzo']}?\n(Demo: gratuito)"
        ) != QMessageBox.StandardButton.Yes:
            return
        ok, msg = acquista(item["id"], "mappa_prefab")
        if not ok:
            QMessageBox.warning(self, t("errore"), msg)
            return
        self._carica_prefab_in_mondo(item)

    def _carica_prefab_in_mondo(self, item: dict):
        from mondi.mondo import GestoreMondo
        mondi = GestoreMondo.lista()
        if not mondi:
            QMessageBox.warning(self, t("errore"), t("nessun_mondo_shop"))
            return
        nomi_mondi = [m["nome"] for m in mondi]
        scelta, ok = QInputDialog.getItem(
            self, "Scegli il mondo",
            t("scegli_mondo").format(n=item["nome"]),
            nomi_mondi, editable=False)
        if not ok:
            return
        mondo_scelto = mondi[nomi_mondi.index(scelta)]
        mappa_id = GestoreMondo.aggiungi_mappa(
            mondo_scelto["id"], f"{item['nome']} (prefab)", livello=0)

        from mappa.map import Griglia
        from mappa.esporta import salva_griglia_nel_db
        from config import HEX_DIMENSIONE, PANNELLO_LARGHEZZA

        griglia = Griglia(
            item.get("colonne", 15), item.get("righe", 12),
            HEX_DIMENSIONE, PANNELLO_LARGHEZZA + 20, 40)
        _disegna_prefab(griglia, item["id"])
        salva_griglia_nel_db(mappa_id, griglia)

        QMessageBox.information(
            self, t("mappa_caricata"),
            f"'{item['nome']}' aggiunta al mondo '{scelta}'.")
        self._aggiorna()

    # ── Tab tileset ───────────────────────────────────────────────────────────

    def _crea_tab_tileset(self) -> QWidget:
        from config import CATALOGO_TILESET
        from database.modelli import ottieni_tileset_attivo
        from auth.sessione_utente import utente_corrente
        import os

        scroll    = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia   = QGridLayout(contenuto)
        griglia.setSpacing(12)

        utente      = utente_corrente()
        tileset_att = ottieni_tileset_attivo(utente["id"]) if utente else "tileset_base"

        icone_tileset = {
            "tileset_base":     "🗺️",
            "tileset_advanced": "✨",
            "tileset_ice":      "❄️",
            "tileset_fire":     "🔥",
            "tileset_dungeon":  "🪨",
        }

        for i, (tid, info) in enumerate(CATALOGO_TILESET.items()):
            card = QFrame()
            card.setStyleSheet(CARD_STYLE)
            lc = QVBoxLayout(card)
            lc.setContentsMargins(12, 12, 12, 12)
            lc.setSpacing(8)

            lbl_icona = QLabel(icone_tileset.get(tid, "🗺️"))
            lbl_icona.setFont(QFont("Arial", 32))
            lbl_icona.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lc.addWidget(lbl_icona)

            # Anteprima PNG se già disponibile
            percorso_prev = os.path.join(info["cartella"], "tileset.png")
            if os.path.exists(percorso_prev):
                from PyQt6.QtGui import QPixmap
                px = QPixmap(percorso_prev)
                if not px.isNull():
                    px_crop = px.copy(0, 0, 256, 128).scaled(
                        200, 80, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
                    lbl_prev = QLabel()
                    lbl_prev.setPixmap(px_crop)
                    lbl_prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lc.addWidget(lbl_prev)

            nome_lbl = QLabel(info["nome"])
            nome_lbl.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            nome_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lc.addWidget(nome_lbl)

            desc_lbl = QLabel(info["descrizione"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #aaaaaa; font-size: 10px;")
            desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lc.addWidget(desc_lbl)

            prezzo = info.get("prezzo")
            plbl = QLabel("Gratuito" if prezzo is None else prezzo)
            plbl.setStyleSheet(
                "color: #80ff80;" if prezzo is None else "color: #ffdd44;")
            plbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lc.addWidget(plbl)

            if tid == tileset_att:
                btn = QPushButton("✓ Attivo")
                btn.setEnabled(False)
                btn.setStyleSheet("color: #80ff80;")
            elif prezzo is None or possiede(tid):
                btn = QPushButton("▶  Attiva")
                btn.setStyleSheet("background-color: #3a6a3a;")
                btn.clicked.connect(
                    lambda checked, t_id=tid: self._attiva_tileset(t_id))
            else:
                btn = QPushButton(f"{t('acquista')} — {prezzo}")
                btn.clicked.connect(
                    lambda checked, t_id=tid, inf=info:
                        self._acquista_tileset(t_id, inf))
            lc.addWidget(btn)
            griglia.addWidget(card, i // 2, i % 2)

        scroll.setWidget(contenuto)
        return scroll

    def _attiva_tileset(self, tileset_id: str):
        from database.modelli import imposta_tileset_attivo
        from auth.sessione_utente import utente_corrente
        utente = utente_corrente()
        if utente:
            imposta_tileset_attivo(utente["id"], tileset_id)
            QMessageBox.information(
                self, "Tileset attivato",
                "Tileset attivato!\n"
                "Riaprendo l'editor mappa vedrai le nuove texture.")
            self._aggiorna()

    def _acquista_tileset(self, tileset_id: str, info: dict):
        if QMessageBox.question(
            self, t("conferma_acquisto"),
            f"Acquistare '{info['nome']}' per {info['prezzo']}?\n(Demo: gratuito)"
        ) != QMessageBox.StandardButton.Yes:
            return
        ok, msg = acquista(tileset_id, "tileset_mappa")
        if ok:
            self._attiva_tileset(tileset_id)
        else:
            QMessageBox.warning(self, t("errore"), msg)

    # ── Tab oggetti esplorabili ───────────────────────────────────────────────

    def _crea_tab_esplorabili(self) -> QWidget:
        from config import OGGETTI_ESPLORABILI
        from mappa.sottolivello import PRESET_DIMENSIONI

        scroll    = QScrollArea()
        scroll.setWidgetResizable(True)
        contenuto = QWidget()
        griglia   = QGridLayout(contenuto)
        griglia.setSpacing(10)
        griglia.setContentsMargins(12, 12, 12, 12)

        info_lbl = QLabel(
            "🏠  Oggetti Esplorabili\n"
            "Piazza questi oggetti sulla mappa: avranno automaticamente\n"
            "un sottolivello vuoto da disegnare nell'editor."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #aaaacc; font-size: 11px;")
        griglia.addWidget(info_lbl, 0, 0, 1, 2)

        for i, (oid, defn) in enumerate(OGGETTI_ESPLORABILI.items(), start=1):
            card = QFrame()
            card.setStyleSheet(CARD_STYLE)
            lc = QHBoxLayout(card)
            lc.setContentsMargins(10, 8, 10, 8)
            lc.setSpacing(10)

            colore = defn["colore"]
            pallino = QLabel("⬡")
            pallino.setFont(QFont("Arial", 18))
            pallino.setStyleSheet(
                f"color: rgb({colore[0]},{colore[1]},{colore[2]});")
            lc.addWidget(pallino)

            col_info = QVBoxLayout()
            nome_lbl = QLabel(defn["nome"])
            nome_lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            col_info.addWidget(nome_lbl)

            preset = defn.get("preset_sottolivello", "stanza")
            dim    = PRESET_DIMENSIONI.get(preset, (40, 30))
            desc   = QLabel(
                f"Celle: {len(defn['forma'])}   "
                f"Sottolivello: {dim[0]}×{dim[1]} hex   "
                f"Preset: {preset}"
            )
            desc.setStyleSheet("color: #888888; font-size: 10px;")
            col_info.addWidget(desc)
            lc.addLayout(col_info, stretch=1)

            col_btn = QVBoxLayout()
            prezzo_lbl = QLabel(defn.get("prezzo", "?"))
            prezzo_lbl.setStyleSheet("color: #ffdd44; font-weight: bold;")
            prezzo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_btn.addWidget(prezzo_lbl)

            shop_id = defn.get("shop_id", oid)
            if possiede(shop_id):
                btn = QPushButton(t("gia_acquistato"))
                btn.setEnabled(False)
                btn.setStyleSheet("color: #80ff80;")
            else:
                btn = QPushButton(t("acquista"))
                btn.setFixedWidth(90)
                btn.clicked.connect(
                    lambda checked, d=defn, s=shop_id:
                        self._acquista_esplorabile(d, s))
            col_btn.addWidget(btn)
            lc.addLayout(col_btn)
            griglia.addWidget(card, i, 0, 1, 2)

        scroll.setWidget(contenuto)
        return scroll

    def _acquista_esplorabile(self, defn: dict, shop_id: str):
        if QMessageBox.question(
            self, t("conferma_acquisto"),
            f"Acquistare '{defn['nome']}' per {defn.get('prezzo','?')}?\n"
            f"(Demo: gratuito)\n\n"
            f"L'oggetto apparirà nel pannello Oggetti dell'editor mappa."
        ) != QMessageBox.StandardButton.Yes:
            return
        ok, msg = acquista(shop_id, "oggetto_esplorabile")
        if ok:
            QMessageBox.information(
                self, "Acquistato!",
                f"'{defn['nome']}' aggiunto agli oggetti!\n"
                f"Lo trovi nel pannello Oggetti dell'editor mappa.")
            self._aggiorna()
        else:
            QMessageBox.warning(self, t("errore"), msg)

    # ── Tab posseduti ─────────────────────────────────────────────────────────

    def _crea_tab_posseduti(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(t("i_miei_acquisti") + ":"))
        self._testo_posseduti = QTextEdit()
        self._testo_posseduti.setReadOnly(True)
        self._aggiorna_testo_posseduti()
        layout.addWidget(self._testo_posseduti)
        return widget

    def _aggiorna_testo_posseduti(self):
        posseduti = lista_posseduti()
        if not posseduti:
            self._testo_posseduti.setPlainText(t("nessun_acquisto"))
            return
        righe = []
        for tipo, label in [
            ("oggetto_mappa",      "Asset Mappa"),
            ("mappa_prefab",       "Mappe Prefab"),
            ("manuale",            "Manuali"),
            ("tileset_mappa",      "Tileset Mappa"),
            ("oggetto_esplorabile","Oggetti Esplorabili"),
        ]:
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
