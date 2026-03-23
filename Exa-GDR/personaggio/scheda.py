"""
personaggio/scheda.py — Scheda personaggio completa
====================================================
Finestra PyQt con 6 tab che coprono tutti gli aspetti del personaggio.
Il Player compila tutto a mano, i dati vengono salvati nel DB come JSON.

Tab disponibili:
    1. Identità      — nome, classe, razza, livello, background
    2. Statistiche   — le 6 stat base con modificatori calcolati
    3. Combattimento — PF, CA, velocità, bonus competenza
    4. Incantesimi   — slot per livello + lista incantesimi
    5. Inventario    — lista oggetti con quantità e descrizione
    6. Abilità       — abilità e competenze

Perché un tab per sezione e non tutto in una pagina?
Una scheda D&D cartacea ha due facciate piene di informazioni.
Su schermo, mettere tutto visibile contemporaneamente sarebbe
illeggibile. I tab riproducono la logica delle sezioni della
scheda cartacea — ogni tab è una "area" della scheda.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QLabel, QLineEdit, QSpinBox,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QMessageBox, QComboBox, QCheckBox, QScrollArea,
    QGroupBox, QGridLayout, QSplitter, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import json
from sessione.combattimento import modificatore_statistica
from database.modelli import carica_personaggio, salva_personaggio, crea_personaggio
from auth.sessione_utente import utente_corrente

# Lista base incantesimi — il Player può sceglierne o aggiungerne di custom
INCANTESIMI_BASE = [
    {"nome": "Dardo incantato",   "livello": 1, "descrizione": "3 dardi magici automatici",
     "danno": "1d4+1 ×3", "gittata": "36m", "area": "—", "componenti": ["V", "S"]},
    {"nome": "Scudo",             "livello": 1, "descrizione": "+5 CA fino al prossimo turno",
     "danno": "—", "gittata": "Sé stesso", "area": "—", "componenti": ["V", "S"]},
    {"nome": "Mani brucianti",    "livello": 1, "descrizione": "Cono di fuoco 3m",
     "danno": "3d6", "gittata": "Sé stesso", "area": "cono 3m", "componenti": ["V", "S"]},
    {"nome": "Nebbia",            "livello": 1, "descrizione": "Sfera di nebbia 6m",
     "danno": "—", "gittata": "27m", "area": "sfera 6m", "componenti": ["V", "S", "M"]},
    {"nome": "Invisibilità",      "livello": 2, "descrizione": "Bersaglio invisibile 1h",
     "danno": "—", "gittata": "Tocco", "area": "—", "componenti": ["V", "S", "M"]},
    {"nome": "Palla di fuoco",    "livello": 3, "descrizione": "Esplosione sferica di fuoco",
     "danno": "8d6", "gittata": "45m", "area": "sfera 6m", "componenti": ["V", "S", "M"]},
    {"nome": "Saetta di fulmine", "livello": 3, "descrizione": "Linea di fulmine 30m",
     "danno": "8d6", "gittata": "Sé stesso", "area": "linea 30m", "componenti": ["V", "S", "M"]},
    {"nome": "Volare",            "livello": 3, "descrizione": "Volo 18m per 10 minuti",
     "danno": "—", "gittata": "Tocco", "area": "—", "componenti": ["V", "S", "M"]},
    {"nome": "Porta dimensionale","livello": 4, "descrizione": "Teletrasporto a 500m",
     "danno": "—", "gittata": "500m", "area": "—", "componenti": ["V"]},
    {"nome": "Cono di freddo",    "livello": 5, "descrizione": "Cono di freddo glaciale",
     "danno": "8d8", "gittata": "Sé stesso", "area": "cono 18m", "componenti": ["V", "S", "M"]},
]

STATISTICHE_NOMI = ["forza", "destrezza", "costituzione",
                    "intelligenza", "saggezza", "carisma"]

CLASSI = ["Barbaro", "Bardo", "Chierico", "Druido", "Guerriero",
          "Ladro", "Mago", "Monaco", "Paladino", "Ranger",
          "Stregone", "Warlock", "Personalizzata"]

RAZZE = ["Umano", "Elfo", "Nano", "Halfling", "Mezzorco",
         "Tiefling", "Draconico", "Gnomo", "Personalizzata"]

ABILITA_LISTA = [
    "Acrobazia", "Addestrare animali", "Arcana", "Atletica",
    "Furtività", "Inganno", "Intuizione", "Intimidazione",
    "Intrattenimento", "Investigazione", "Medicina", "Natura",
    "Percezione", "Persuasione", "Religione", "Storia",
    "Sopravvivenza", "Rapidità di mano"
]


# ─────────────────────────────────────────────────────────────────────────────
#  FINESTRA SCHEDA
# ─────────────────────────────────────────────────────────────────────────────

class FinestraScheda(QDialog):
    """
    Finestra completa della scheda personaggio.

    Può essere usata in due modalità:
        - Creazione: personaggio_id=None → crea nuovo personaggio
        - Modifica:  personaggio_id=X    → carica e modifica esistente

    Signal scheda_salvata: emesso dopo il salvataggio con i dati aggiornati.
    """

    scheda_salvata = pyqtSignal(dict)

    def __init__(self, personaggio_id: int = None, parent=None):
        super().__init__(parent)
        self.personaggio_id = personaggio_id
        self._dati: dict = self._dati_default()

        # Se stiamo modificando un personaggio esistente, carichiamo i dati
        if personaggio_id:
            self._carica_dati(personaggio_id)

        titolo = "Modifica personaggio" if personaggio_id else "Crea personaggio"
        self.setWindowTitle(titolo)
        self.setMinimumSize(820, 640)
        self.resize(900, 700)

        self._costruisci_ui()
        self._popola_campi()

    # ── Dati ─────────────────────────────────────────────────────────────────

    def _dati_default(self) -> dict:
        """
        Struttura dati di una scheda vuota.
        Usata come punto di partenza per un nuovo personaggio.
        """
        return {
            "nome":             "",
            "classe":           "Guerriero",
            "razza":            "Umano",
            "livello":          1,
            "background":       "",
            "statistiche": {s: 10 for s in STATISTICHE_NOMI},
            "punti_ferita":     10,
            "pf_massimi":       10,
            "classe_armatura":  10,
            "velocita":         6,
            "bonus_competenza": 2,
            "slot_incantesimi": {str(i): [0, 0] for i in range(1, 10)},
            "incantesimi":      [],
            "abilita":          [],
            "competenze":       [],
            "inventario":       [],
        }

    def _carica_dati(self, personaggio_id: int):
        """Carica i dati dal database."""
        scheda = carica_personaggio(personaggio_id)
        if scheda:
            self._dati.update(scheda["statistiche_json"])
            # Assicuriamoci che tutti i campi esistano (per schede vecchie)
            for chiave, valore in self._dati_default().items():
                if chiave not in self._dati:
                    self._dati[chiave] = valore

    # ── Costruzione UI ────────────────────────────────────────────────────────

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Tab principale
        self._tabs = QTabWidget()
        self._tabs.addTab(self._tab_identita(),     "👤 Identità")
        self._tabs.addTab(self._tab_statistiche(),  "📊 Statistiche")
        self._tabs.addTab(self._tab_combattimento(),"⚔️ Combattimento")
        self._tabs.addTab(self._tab_incantesimi(),  "✨ Incantesimi")
        self._tabs.addTab(self._tab_inventario(),   "🎒 Inventario")
        self._tabs.addTab(self._tab_abilita(),      "🎯 Abilità")
        layout.addWidget(self._tabs, stretch=1)

        # Pulsanti in fondo
        riga_btn = QHBoxLayout()
        riga_btn.addStretch()
        btn_annulla = QPushButton("Annulla")
        btn_annulla.clicked.connect(self.reject)
        riga_btn.addWidget(btn_annulla)
        btn_salva = QPushButton("💾  Salva scheda")
        btn_salva.setDefault(True)
        btn_salva.clicked.connect(self._salva)
        riga_btn.addWidget(btn_salva)
        layout.addLayout(riga_btn)

    # ── Tab 1: Identità ───────────────────────────────────────────────────────

    def _tab_identita(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._campo_nome = QLineEdit()
        self._campo_nome.setPlaceholderText("Nome del personaggio")
        layout.addRow("Nome:", self._campo_nome)

        self._combo_classe = QComboBox()
        self._combo_classe.addItems(CLASSI)
        self._combo_classe.setEditable(True)
        layout.addRow("Classe:", self._combo_classe)

        self._combo_razza = QComboBox()
        self._combo_razza.addItems(RAZZE)
        self._combo_razza.setEditable(True)
        layout.addRow("Razza:", self._combo_razza)

        self._spin_livello = QSpinBox()
        self._spin_livello.setRange(1, 20)
        layout.addRow("Livello:", self._spin_livello)

        layout.addRow(QLabel("Background / storia del personaggio:"))
        self._area_background = QTextEdit()
        self._area_background.setMinimumHeight(160)
        self._area_background.setPlaceholderText(
            "Descrivi il background, la storia e la personalità del tuo personaggio...")
        layout.addRow(self._area_background)

        scroll.setWidget(w)
        return scroll

    # ── Tab 2: Statistiche ────────────────────────────────────────────────────

    def _tab_statistiche(self) -> QWidget:
        """
        Mostra le 6 statistiche base con il modificatore calcolato in tempo reale.
        Quando cambia il valore di una stat, il modificatore si aggiorna subito.
        """
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel(
            "Modificatore = (statistica - 10) ÷ 2  (arrotondato per difetto)"),
        )

        griglia = QGridLayout()
        griglia.setSpacing(8)

        # Intestazioni
        for col, testo in enumerate(["Statistica", "Valore", "Modificatore"]):
            lbl = QLabel(testo)
            lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            griglia.addWidget(lbl, 0, col)

        self._spin_stat:  dict[str, QSpinBox] = {}
        self._lbl_mod:    dict[str, QLabel]   = {}

        for riga, stat in enumerate(STATISTICHE_NOMI, start=1):
            # Nome
            griglia.addWidget(QLabel(stat.capitalize() + ":"), riga, 0)

            # SpinBox valore
            spin = QSpinBox()
            spin.setRange(1, 30)
            spin.setValue(10)
            spin.setFixedWidth(70)
            self._spin_stat[stat] = spin
            griglia.addWidget(spin, riga, 1)

            # Label modificatore — aggiornato quando cambia il valore
            lbl_mod = QLabel("+0")
            lbl_mod.setFixedWidth(50)
            lbl_mod.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._lbl_mod[stat] = lbl_mod
            griglia.addWidget(lbl_mod, riga, 2)

            # Collega il cambio valore all'aggiornamento del modificatore
            # Lambda con default stat=stat per catturare il valore corrente
            # di stat nell'iterazione — senza il default, tutte le lambda
            # userebbero l'ultimo valore di stat del ciclo (bug classico).
            spin.valueChanged.connect(
                lambda val, s=stat: self._aggiorna_modificatore(s, val))

        layout.addLayout(griglia)
        layout.addStretch()
        return w

    def _aggiorna_modificatore(self, stat: str, valore: int):
        """Ricalcola e mostra il modificatore quando cambia il valore."""
        mod   = modificatore_statistica(valore)
        segno = "+" if mod >= 0 else ""
        lbl   = self._lbl_mod[stat]
        lbl.setText(f"{segno}{mod}")
        # Verde se positivo, rosso se negativo, grigio se zero
        if mod > 0:
            lbl.setStyleSheet("color: #80ff80;")
        elif mod < 0:
            lbl.setStyleSheet("color: #ff8080;")
        else:
            lbl.setStyleSheet("color: #aaaaaa;")

    # ── Tab 3: Combattimento ──────────────────────────────────────────────────

    def _tab_combattimento(self) -> QWidget:
        w = QWidget()
        layout = QFormLayout(w)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._spin_pf_max = QSpinBox()
        self._spin_pf_max.setRange(1, 999)
        layout.addRow("PF massimi:", self._spin_pf_max)

        self._spin_pf_attuali = QSpinBox()
        self._spin_pf_attuali.setRange(0, 999)
        layout.addRow("PF attuali:", self._spin_pf_attuali)

        self._spin_ca = QSpinBox()
        self._spin_ca.setRange(1, 30)
        layout.addRow("Classe armatura (CA):", self._spin_ca)

        self._spin_velocita = QSpinBox()
        self._spin_velocita.setRange(1, 20)
        self._spin_velocita.setSuffix(" hex/turno")
        layout.addRow("Velocità:", self._spin_velocita)

        self._spin_bonus_comp = QSpinBox()
        self._spin_bonus_comp.setRange(1, 6)
        layout.addRow("Bonus competenza:", self._spin_bonus_comp)

        # Nota esplicativa
        nota = QLabel(
            "ℹ️  La velocità indica quanti esagoni puoi percorrere per turno "
            "in combattimento.\nIl bonus competenza si aggiunge ai tiri per "
            "abilità in cui sei competente."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addRow(nota)

        return w

    # ── Tab 4: Incantesimi ────────────────────────────────────────────────────

    def _tab_incantesimi(self) -> QWidget:
        """
        Due sezioni:
        - Sinistra: slot per livello (quanti ne hai, quanti ne hai usati)
        - Destra:   lista degli incantesimi conosciuti
        """
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Slot incantesimi ──────────────────────────────────────────────────
        w_slot = QWidget()
        layout_slot = QVBoxLayout(w_slot)
        layout_slot.setContentsMargins(8, 8, 8, 8)
        layout_slot.addWidget(QLabel("Slot incantesimi per livello:"))

        griglia_slot = QGridLayout()
        griglia_slot.setSpacing(6)
        for col, testo in enumerate(["Livello", "Totali", "Usati"]):
            lbl = QLabel(testo)
            lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            griglia_slot.addWidget(lbl, 0, col)

        self._spin_slot_totali: dict[int, QSpinBox] = {}
        self._spin_slot_usati:  dict[int, QSpinBox] = {}

        for i, livello in enumerate(range(1, 10), start=1):
            griglia_slot.addWidget(QLabel(f"  {livello}°:"), i, 0)

            spin_tot = QSpinBox()
            spin_tot.setRange(0, 10)
            spin_tot.setFixedWidth(55)
            self._spin_slot_totali[livello] = spin_tot
            griglia_slot.addWidget(spin_tot, i, 1)

            spin_us = QSpinBox()
            spin_us.setRange(0, 10)
            spin_us.setFixedWidth(55)
            self._spin_slot_usati[livello] = spin_us
            griglia_slot.addWidget(spin_us, i, 2)

        layout_slot.addLayout(griglia_slot)
        layout_slot.addStretch()
        splitter.addWidget(w_slot)

        # ── Lista incantesimi ─────────────────────────────────────────────────
        w_lista = QWidget()
        layout_lista = QVBoxLayout(w_lista)
        layout_lista.setContentsMargins(8, 8, 8, 8)
        layout_lista.addWidget(QLabel("Incantesimi conosciuti:"))

        self._lista_incantesimi = QListWidget()
        self._lista_incantesimi.itemDoubleClicked.connect(
            self._mostra_dettaglio_incantesimo)
        layout_lista.addWidget(self._lista_incantesimi, stretch=1)

        riga_btn = QHBoxLayout()
        btn_aggiungi_base = QPushButton("+ Da lista base")
        btn_aggiungi_base.clicked.connect(self._aggiungi_incantesimo_base)
        riga_btn.addWidget(btn_aggiungi_base)

        btn_aggiungi_custom = QPushButton("+ Custom")
        btn_aggiungi_custom.clicked.connect(self._aggiungi_incantesimo_custom)
        riga_btn.addWidget(btn_aggiungi_custom)

        btn_rimuovi = QPushButton("Rimuovi")
        btn_rimuovi.clicked.connect(self._rimuovi_incantesimo)
        riga_btn.addWidget(btn_rimuovi)
        layout_lista.addLayout(riga_btn)

        splitter.addWidget(w_lista)
        splitter.setSizes([220, 400])
        return splitter

    # ── Tab 5: Inventario ─────────────────────────────────────────────────────

    def _tab_inventario(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        self._lista_inventario = QListWidget()
        self._lista_inventario.itemDoubleClicked.connect(
            self._modifica_oggetto)
        layout.addWidget(self._lista_inventario, stretch=1)

        riga_btn = QHBoxLayout()
        btn_aggiungi = QPushButton("+ Aggiungi oggetto")
        btn_aggiungi.clicked.connect(self._aggiungi_oggetto)
        riga_btn.addWidget(btn_aggiungi)

        btn_rimuovi = QPushButton("Rimuovi")
        btn_rimuovi.clicked.connect(self._rimuovi_oggetto)
        riga_btn.addWidget(btn_rimuovi)
        layout.addLayout(riga_btn)

        return w

    # ── Tab 6: Abilità ────────────────────────────────────────────────────────

    def _tab_abilita(self) -> QWidget:
        """
        Checklist delle abilità standard + campo libero per le competenze.
        Le checkbox spuntate vengono salvate come lista in self._dati["abilita"].
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        layout.addWidget(QLabel(
            "Seleziona le abilità in cui sei competente:"))

        self._check_abilita: dict[str, QCheckBox] = {}
        griglia = QGridLayout()
        griglia.setSpacing(4)
        for i, nome in enumerate(ABILITA_LISTA):
            chk = QCheckBox(nome)
            self._check_abilita[nome] = chk
            griglia.addWidget(chk, i // 2, i % 2)
        layout.addLayout(griglia)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addWidget(QLabel("Competenze con armi e armature:"))
        self._area_competenze = QTextEdit()
        self._area_competenze.setMaximumHeight(80)
        self._area_competenze.setPlaceholderText(
            "Es: Spade, Armature leggere, Scudi...")
        layout.addWidget(self._area_competenze)
        layout.addStretch()

        scroll.setWidget(w)
        return scroll

    # ── Popolamento campi dai dati ────────────────────────────────────────────

    def _popola_campi(self):
        """Riempie tutti i widget con i dati di self._dati."""
        d = self._dati

        # Identità
        self._campo_nome.setText(d.get("nome", ""))
        idx = self._combo_classe.findText(d.get("classe", ""))
        if idx >= 0:
            self._combo_classe.setCurrentIndex(idx)
        else:
            self._combo_classe.setCurrentText(d.get("classe", ""))
        idx = self._combo_razza.findText(d.get("razza", ""))
        if idx >= 0:
            self._combo_razza.setCurrentIndex(idx)
        else:
            self._combo_razza.setCurrentText(d.get("razza", ""))
        self._spin_livello.setValue(d.get("livello", 1))
        self._area_background.setPlainText(d.get("background", ""))

        # Statistiche
        for stat in STATISTICHE_NOMI:
            valore = d.get("statistiche", {}).get(stat, 10)
            self._spin_stat[stat].setValue(valore)
            self._aggiorna_modificatore(stat, valore)

        # Combattimento
        self._spin_pf_max.setValue(d.get("pf_massimi", 10))
        self._spin_pf_attuali.setValue(d.get("punti_ferita", 10))
        self._spin_ca.setValue(d.get("classe_armatura", 10))
        self._spin_velocita.setValue(d.get("velocita", 6))
        self._spin_bonus_comp.setValue(d.get("bonus_competenza", 2))

        # Slot incantesimi
        slot = d.get("slot_incantesimi", {})
        for livello in range(1, 10):
            dati_slot = slot.get(str(livello), [0, 0])
            self._spin_slot_totali[livello].setValue(dati_slot[0])
            self._spin_slot_usati[livello].setValue(dati_slot[1])

        # Incantesimi
        self._lista_incantesimi.clear()
        for inc in d.get("incantesimi", []):
            self._aggiungi_voce_incantesimo(inc)

        # Inventario
        self._lista_inventario.clear()
        for ogg in d.get("inventario", []):
            self._lista_inventario.addItem(
                f"{ogg['nome']}  ×{ogg.get('quantita', 1)}"
                + (f"  — {ogg['descrizione']}" if ogg.get('descrizione') else "")
            )

        # Abilità
        for nome, chk in self._check_abilita.items():
            chk.setChecked(nome in d.get("abilita", []))
        self._area_competenze.setPlainText(
            ", ".join(d.get("competenze", [])))

    def _aggiungi_voce_incantesimo(self, inc: dict):
        """Aggiunge una riga alla lista incantesimi."""
        comp_str = "/".join(inc.get("componenti", []))
        testo = (f"[{inc['livello']}°] {inc['nome']}  "
                 f"— {inc['danno']}  {inc['gittata']}  [{comp_str}]"
                 + ("  ★custom" if inc.get("custom") else ""))
        item = QListWidgetItem(testo)
        item.setData(Qt.ItemDataRole.UserRole, inc)
        if inc.get("custom"):
            item.setForeground(QColor("#ffcc66"))
        self._lista_incantesimi.addItem(item)

    # ── Azioni incantesimi ────────────────────────────────────────────────────

    def _aggiungi_incantesimo_base(self):
        """Mostra una finestra per scegliere dalla lista base."""
        dialog = _SceltaIncantesimoBase(INCANTESIMI_BASE, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            inc = dialog.incantesimo_scelto
            if inc and inc not in self._dati["incantesimi"]:
                self._dati["incantesimi"].append(inc)
                self._aggiungi_voce_incantesimo(inc)

    def _aggiungi_incantesimo_custom(self):
        """Apre un form per creare un incantesimo personalizzato."""
        dialog = _FormIncantesimoCustom(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            inc = dialog.incantesimo
            inc["custom"] = True
            self._dati["incantesimi"].append(inc)
            self._aggiungi_voce_incantesimo(inc)

    def _rimuovi_incantesimo(self):
        item = self._lista_incantesimi.currentItem()
        if item:
            inc = item.data(Qt.ItemDataRole.UserRole)
            self._dati["incantesimi"] = [
                i for i in self._dati["incantesimi"] if i != inc]
            self._lista_incantesimi.takeItem(
                self._lista_incantesimi.row(item))

    def _mostra_dettaglio_incantesimo(self, item: QListWidgetItem):
        """Doppio click → mostra i dettagli dell'incantesimo."""
        inc = item.data(Qt.ItemDataRole.UserRole)
        if not inc:
            return
        comp_str = ", ".join(inc.get("componenti", []))
        testo = (
            f"Nome:        {inc['nome']}\n"
            f"Livello:     {inc['livello']}°\n"
            f"Danno:       {inc.get('danno','—')}\n"
            f"Gittata:     {inc.get('gittata','—')}\n"
            f"Area:        {inc.get('area','—')}\n"
            f"Componenti:  {comp_str}\n\n"
            f"Descrizione: {inc.get('descrizione','')}"
        )
        QMessageBox.information(self, inc["nome"], testo)

    # ── Azioni inventario ─────────────────────────────────────────────────────

    def _aggiungi_oggetto(self):
        dialog = _FormOggetto(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ogg = dialog.oggetto
            self._dati["inventario"].append(ogg)
            self._lista_inventario.addItem(
                f"{ogg['nome']}  ×{ogg['quantita']}"
                + (f"  — {ogg['descrizione']}" if ogg.get("descrizione") else ""))

    def _modifica_oggetto(self, item: QListWidgetItem):
        """Doppio click → modifica oggetto."""
        row = self._lista_inventario.row(item)
        ogg = self._dati["inventario"][row]
        dialog = _FormOggetto(self, ogg)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._dati["inventario"][row] = dialog.oggetto
            ogg_upd = dialog.oggetto
            item.setText(
                f"{ogg_upd['nome']}  ×{ogg_upd['quantita']}"
                + (f"  — {ogg_upd['descrizione']}"
                   if ogg_upd.get("descrizione") else ""))

    def _rimuovi_oggetto(self):
        row = self._lista_inventario.currentRow()
        if row >= 0:
            self._lista_inventario.takeItem(row)
            del self._dati["inventario"][row]

    # ── Salvataggio ───────────────────────────────────────────────────────────

    def _raccogli_dati(self):
        """Legge tutti i widget e aggiorna self._dati."""
        d = self._dati

        # Identità
        d["nome"]       = self._campo_nome.text().strip()
        d["classe"]     = self._combo_classe.currentText()
        d["razza"]      = self._combo_razza.currentText()
        d["livello"]    = self._spin_livello.value()
        d["background"] = self._area_background.toPlainText()

        # Statistiche
        for stat in STATISTICHE_NOMI:
            d["statistiche"][stat] = self._spin_stat[stat].value()

        # Combattimento
        d["pf_massimi"]       = self._spin_pf_max.value()
        d["punti_ferita"]     = self._spin_pf_attuali.value()
        d["classe_armatura"]  = self._spin_ca.value()
        d["velocita"]         = self._spin_velocita.value()
        d["bonus_competenza"] = self._spin_bonus_comp.value()

        # Slot incantesimi
        for livello in range(1, 10):
            d["slot_incantesimi"][str(livello)] = [
                self._spin_slot_totali[livello].value(),
                self._spin_slot_usati[livello].value(),
            ]

        # Abilità
        d["abilita"] = [n for n, chk in self._check_abilita.items()
                        if chk.isChecked()]
        testo_comp = self._area_competenze.toPlainText()
        d["competenze"] = [c.strip() for c in testo_comp.split(",")
                           if c.strip()]

    def _salva(self):
        """Raccoglie i dati, valida e salva nel DB."""
        self._raccogli_dati()

        if not self._dati["nome"]:
            QMessageBox.warning(self, "Campo obbligatorio",
                                "Il nome del personaggio è obbligatorio.")
            self._tabs.setCurrentIndex(0)
            self._campo_nome.setFocus()
            return

        utente = utente_corrente()
        if not utente:
            QMessageBox.critical(self, "Errore", "Nessun utente loggato.")
            return

        if self.personaggio_id is None:
            # Creazione nuovo personaggio
            self.personaggio_id = crea_personaggio(
                utente_id    = utente["id"],
                nome         = self._dati["nome"],
                classe       = self._dati["classe"],
                statistiche  = self._dati,
            )
        else:
            # Aggiornamento personaggio esistente
            scheda = carica_personaggio(self.personaggio_id)
            salva_personaggio(
                personaggio_id = self.personaggio_id,
                statistiche    = self._dati,
                inventario     = self._dati["inventario"],
                note           = scheda.get("note", "") if scheda else "",
            )

        self.scheda_salvata.emit(self._dati)
        QMessageBox.information(self, "Salvato",
                                f"Scheda di {self._dati['nome']} salvata.")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  DIALOGHI AUSILIARI
# ─────────────────────────────────────────────────────────────────────────────

class _SceltaIncantesimoBase(QDialog):
    """Finestra per scegliere un incantesimo dalla lista base."""

    def __init__(self, incantesimi: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scegli incantesimo")
        self.setMinimumSize(500, 400)
        self.incantesimo_scelto = None
        self._incantesimi = incantesimi

        layout = QVBoxLayout(self)
        self._lista = QListWidget()
        for inc in incantesimi:
            comp = "/".join(inc.get("componenti", []))
            item = QListWidgetItem(
                f"[{inc['livello']}°] {inc['nome']}  — {inc['danno']}  {inc['gittata']}  [{comp}]")
            item.setData(Qt.ItemDataRole.UserRole, inc)
            self._lista.addItem(item)
        self._lista.itemDoubleClicked.connect(self._scegli)
        layout.addWidget(self._lista)

        self._area_desc = QLabel("")
        self._area_desc.setWordWrap(True)
        self._area_desc.setStyleSheet("color: #aaaacc; font-size: 11px; padding: 4px;")
        layout.addWidget(self._area_desc)
        self._lista.currentItemChanged.connect(self._mostra_desc)

        riga = QHBoxLayout()
        riga.addStretch()
        btn = QPushButton("Aggiungi alla scheda")
        btn.clicked.connect(self._scegli)
        riga.addWidget(btn)
        layout.addLayout(riga)

    def _mostra_desc(self, item):
        if item:
            inc = item.data(Qt.ItemDataRole.UserRole)
            self._area_desc.setText(inc.get("descrizione", ""))

    def _scegli(self):
        item = self._lista.currentItem()
        if item:
            self.incantesimo_scelto = item.data(Qt.ItemDataRole.UserRole)
            self.accept()


class _FormIncantesimoCustom(QDialog):
    """Form per creare un incantesimo personalizzato."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incantesimo personalizzato")
        self.setMinimumWidth(400)
        self.incantesimo = {}

        layout = QFormLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        self._nome      = QLineEdit()
        self._livello   = QSpinBox()
        self._livello.setRange(0, 9)
        self._danno     = QLineEdit()
        self._danno.setPlaceholderText("es. 2d6, 1d8+3, —")
        self._gittata   = QLineEdit()
        self._gittata.setPlaceholderText("es. 18m, Tocco, Sé stesso")
        self._area      = QLineEdit()
        self._area.setPlaceholderText("es. sfera 6m, cono 9m, —")
        self._desc      = QTextEdit()
        self._desc.setMaximumHeight(80)

        self._chk_v = QCheckBox("V (verbale)")
        self._chk_s = QCheckBox("S (somatico)")
        self._chk_m = QCheckBox("M (materiale)")
        riga_comp = QHBoxLayout()
        riga_comp.addWidget(self._chk_v)
        riga_comp.addWidget(self._chk_s)
        riga_comp.addWidget(self._chk_m)

        layout.addRow("Nome*:",       self._nome)
        layout.addRow("Livello:",     self._livello)
        layout.addRow("Danno:",       self._danno)
        layout.addRow("Gittata:",     self._gittata)
        layout.addRow("Area:",        self._area)
        layout.addRow("Componenti:",  riga_comp)
        layout.addRow("Descrizione:", self._desc)

        btn = QPushButton("Aggiungi")
        btn.clicked.connect(self._conferma)
        layout.addRow(btn)

    def _conferma(self):
        if not self._nome.text().strip():
            QMessageBox.warning(self, "Campo mancante", "Il nome è obbligatorio.")
            return
        componenti = []
        if self._chk_v.isChecked(): componenti.append("V")
        if self._chk_s.isChecked(): componenti.append("S")
        if self._chk_m.isChecked(): componenti.append("M")
        self.incantesimo = {
            "nome":        self._nome.text().strip(),
            "livello":     self._livello.value(),
            "danno":       self._danno.text().strip() or "—",
            "gittata":     self._gittata.text().strip() or "—",
            "area":        self._area.text().strip() or "—",
            "componenti":  componenti,
            "descrizione": self._desc.toPlainText(),
        }
        self.accept()


class _FormOggetto(QDialog):
    """Form per aggiungere o modificare un oggetto nell'inventario."""

    def __init__(self, parent=None, oggetto: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Oggetto inventario")
        self.setMinimumWidth(360)
        self.oggetto = {}

        layout = QFormLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        self._nome       = QLineEdit()
        self._quantita   = QSpinBox()
        self._quantita.setRange(1, 999)
        self._descrizione = QLineEdit()
        self._descrizione.setPlaceholderText("Descrizione opzionale")

        if oggetto:
            self._nome.setText(oggetto.get("nome", ""))
            self._quantita.setValue(oggetto.get("quantita", 1))
            self._descrizione.setText(oggetto.get("descrizione", ""))

        layout.addRow("Nome*:",       self._nome)
        layout.addRow("Quantità:",    self._quantita)
        layout.addRow("Descrizione:", self._descrizione)

        btn = QPushButton("Salva")
        btn.clicked.connect(self._conferma)
        layout.addRow(btn)

    def _conferma(self):
        if not self._nome.text().strip():
            QMessageBox.warning(self, "Campo mancante", "Il nome è obbligatorio.")
            return
        self.oggetto = {
            "nome":        self._nome.text().strip(),
            "quantita":    self._quantita.value(),
            "descrizione": self._descrizione.text().strip(),
        }
        self.accept()
