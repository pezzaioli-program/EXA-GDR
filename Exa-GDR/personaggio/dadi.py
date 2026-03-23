"""
personaggio/dadi.py — Sistema dadi con supporto skin
=====================================================
Gestisce tutto ciò che riguarda i dadi:
  - Lancio con animazione visiva (pygame)
  - Skin per ogni tipo di dado (PNG o placeholder colorato)
  - Salvataggio/caricamento della skin attiva per utente
  - Widget PyQt che incorpora la visualizzazione pygame

Separato da combattimento.py perché:
  combattimento.py sa QUANDO e COME usare i dadi (regole di gioco)
  dadi.py          sa COME mostrarli e quali skin applicare (presentazione)

La funzione lancia_dado() di combattimento.py è la logica pura.
Questo file aggiunge la visualizzazione sopra quella logica.
"""

import pygame
import math
import random
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDialog,
    QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QImage

from config import (
    CARTELLA_ACQUISTATI, COLORE_SFONDO, COLORE_TESTO,
    COLORE_ACCENTO
)
from sessione.combattimento import lancia_dado, modificatore_statistica
from database.db import esegui, leggi_uno, leggi_tutti


# ─────────────────────────────────────────────────────────────────────────────
#  COSTANTI
# ─────────────────────────────────────────────────────────────────────────────

TIPI_DADO = [4, 6, 8, 10, 12, 20, 100]

# Colore placeholder per ogni tipo di dado (usato se non c'è skin PNG)
COLORI_DADO = {
    4:   (180,  80,  80),   # rosso    — d4
    6:   ( 80, 140, 200),   # blu      — d6
    8:   ( 80, 180,  80),   # verde    — d8
    10:  (200, 140,  60),   # arancio  — d10
    12:  (140,  80, 200),   # viola    — d12
    20:  (200, 200,  60),   # giallo   — d20
    100: (160, 160, 160),   # grigio   — d100
}

# Durata animazione in millisecondi
DURATA_ANIMAZIONE_MS = 800
FPS_ANIMAZIONE       = 30


# ─────────────────────────────────────────────────────────────────────────────
#  GESTIONE SKIN — database
# ─────────────────────────────────────────────────────────────────────────────

def inizializza_tabella_skin_dadi():
    """
    Crea la tabella skin_dadi se non esiste.
    Chiamata da database/db.py in inizializza_db().

    Struttura: un record per utente con le skin attive per ogni dado
    salvate come JSON — stesso pattern di statistiche_json nel personaggio.
    """
    esegui("""
        CREATE TABLE IF NOT EXISTS skin_dadi (
            utente_id   INTEGER PRIMARY KEY,
            skin_json   TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (utente_id) REFERENCES utenti(id)
        )
    """)


def carica_skin_attive(utente_id: int) -> dict:
    """
    Carica le skin attive dell'utente dal database.
    Restituisce un dizionario {facce: skin_id | None}.

    Se l'utente non ha ancora skin configurate, restituisce tutto None.
    """
    import json
    riga = leggi_uno(
        "SELECT skin_json FROM skin_dadi WHERE utente_id = ?",
        (utente_id,)
    )
    if riga is None:
        return {str(f): None for f in TIPI_DADO}

    skin = json.loads(riga["skin_json"])
    # Assicuriamoci che tutti i tipi di dado siano presenti
    for facce in TIPI_DADO:
        if str(facce) not in skin:
            skin[str(facce)] = None
    return skin


def salva_skin_attive(utente_id: int, skin: dict):
    """
    Salva le skin attive nel database.
    Usa INSERT OR REPLACE per gestire sia inserimento che aggiornamento.

    INSERT OR REPLACE: se esiste già un record con questa chiave primaria,
    lo sostituisce. Se non esiste, lo inserisce. È più semplice di fare
    prima un SELECT e poi decidere tra INSERT e UPDATE.
    """
    import json
    esegui(
        "INSERT OR REPLACE INTO skin_dadi (utente_id, skin_json) VALUES (?, ?)",
        (utente_id, json.dumps(skin))
    )


def equipaggia_skin(utente_id: int, facce: int, skin_id: str | None):
    """
    Equipaggia (o rimuove) una skin su un dado specifico.

    facce:   il tipo di dado (4, 6, 8...)
    skin_id: l'id della skin acquistata, o None per rimuovere
    """
    skin = carica_skin_attive(utente_id)
    skin[str(facce)] = skin_id
    salva_skin_attive(utente_id, skin)


def percorso_skin(skin_id: str, facce: int) -> str | None:
    """
    Restituisce il percorso del PNG per una skin.
    Cerca prima negli acquisti, poi nella cartella asset/dadi/.

    Restituisce None se il file non esiste — in quel caso
    il dado userà il placeholder colorato.
    """
    if skin_id is None:
        return None

    # Percorso nella cartella acquistati
    percorso_acq = os.path.join(CARTELLA_ACQUISTATI, f"{skin_id}_d{facce}.png")
    if os.path.exists(percorso_acq):
        return percorso_acq

    # Percorso nella cartella asset/dadi/
    from config import CARTELLA_ASSET
    percorso_base = os.path.join(CARTELLA_ASSET, "dadi", f"{skin_id}_d{facce}.png")
    if os.path.exists(percorso_base):
        return percorso_base

    return None   # PNG non trovato → userà il placeholder


# ─────────────────────────────────────────────────────────────────────────────
#  ANIMAZIONE DADO — pygame
# ─────────────────────────────────────────────────────────────────────────────

class AnimazioneDado:
    """
    Gestisce l'animazione di un dado che "rotola" prima di fermarsi.

    Come funziona l'animazione:
    - Per DURATA_ANIMAZIONE_MS millisecondi mostriamo numeri casuali
      che cambiano rapidamente (effetto "rotolamento")
    - Alla fine mostriamo il risultato finale
    - Se c'è un PNG skin, lo mostriamo ruotando l'immagine
    - Altrimenti disegniamo una forma geometrica colorata

    Attributi:
        facce         — tipo di dado
        risultato     — numero finale (già calcolato, non cambia)
        skin_path     — percorso PNG o None
        in_corso      — True finché l'animazione non è finita
        valore_mostrato — numero attualmente visibile (cambia durante l'animazione)
        angolo_rotazione — per ruotare il PNG durante l'animazione
    """

    def __init__(self, facce: int, risultato: int, skin_path: str | None):
        self.facce           = facce
        self.risultato       = risultato
        self.skin_path       = skin_path
        self.in_corso        = True
        self.valore_mostrato = random.randint(1, facce)
        self.angolo_rotazione = 0.0
        self._elapsed_ms     = 0
        self._png_surface    = None

        # Carica il PNG se disponibile
        if skin_path and os.path.exists(skin_path):
            try:
                self._png_surface = pygame.image.load(skin_path).convert_alpha()
            except Exception:
                self._png_surface = None

    def aggiorna(self, delta_ms: int):
        """
        Aggiorna lo stato dell'animazione.
        delta_ms: millisecondi passati dall'ultimo frame.

        Durante l'animazione:
        - I primi 70%: mostra numeri casuali (rotolamento)
        - Ultimi 30%: mostra il risultato finale (dado che si ferma)
        """
        if not self.in_corso:
            return

        self._elapsed_ms += delta_ms
        progresso = self._elapsed_ms / DURATA_ANIMAZIONE_MS  # 0.0 → 1.0

        if progresso >= 1.0:
            self.in_corso        = False
            self.valore_mostrato = self.risultato
            self.angolo_rotazione = 0.0
        elif progresso < 0.7:
            # Fase rotolamento: cambia numero ogni ~80ms
            if self._elapsed_ms % 80 < delta_ms:
                self.valore_mostrato = random.randint(1, self.facce)
            # Rotazione accelerata
            self.angolo_rotazione += 15 * (1 - progresso)
        else:
            # Fase rallentamento: mantieni risultato, rallenta rotazione
            self.valore_mostrato  = self.risultato
            self.angolo_rotazione *= 0.85   # decelerazione esponenziale

    def disegna(self, surface: pygame.Surface, cx: int, cy: int, raggio: int):
        """
        Disegna il dado sulla surface al centro (cx, cy) con il raggio dato.

        Se c'è un PNG: ruota e ridimensiona il PNG
        Se non c'è: disegna una forma geometrica colorata
        """
        if self._png_surface:
            self._disegna_png(surface, cx, cy, raggio)
        else:
            self._disegna_placeholder(surface, cx, cy, raggio)

        # Numero sopra il dado
        font_size = max(14, raggio // 2)
        try:
            font = pygame.font.SysFont("Arial", font_size, bold=True)
        except Exception:
            font = pygame.font.Font(None, font_size)

        testo = font.render(str(self.valore_mostrato), True, (255, 255, 255))
        rect  = testo.get_rect(center=(cx, cy))
        surface.blit(testo, rect)

    def _disegna_png(self, surface, cx, cy, raggio):
        """Ridimensiona e ruota il PNG skin."""
        dim   = raggio * 2
        img   = pygame.transform.scale(self._png_surface, (dim, dim))
        img   = pygame.transform.rotate(img, self.angolo_rotazione)
        rect  = img.get_rect(center=(cx, cy))
        surface.blit(img, rect)

    def _disegna_placeholder(self, surface, cx, cy, raggio):
        """
        Disegna una forma geometrica colorata in base al tipo di dado.

        d4  → triangolo (3 lati)
        d6  → quadrato  (4 lati)
        d8  → rombo     (come due triangoli)
        d10 → pentagono (5 lati)
        d12 → esagono   (6 lati)
        d20 → 20 lati ≈ cerchio
        d100→ cerchio
        """
        colore = COLORI_DADO.get(self.facce, (150, 150, 150))
        angolo_rad = math.radians(self.angolo_rotazione)

        lati = {4: 3, 6: 4, 8: 4, 10: 5, 12: 6, 20: 8, 100: 32}.get(self.facce, 6)

        vertici = []
        for i in range(lati):
            theta = angolo_rad + 2 * math.pi * i / lati - math.pi / 2
            vx = cx + raggio * math.cos(theta)
            vy = cy + raggio * math.sin(theta)
            vertici.append((vx, vy))

        pygame.draw.polygon(surface, colore, vertici)
        pygame.draw.polygon(surface, (255, 255, 255), vertici, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  WIDGET DADO — PyQt + pygame
# ─────────────────────────────────────────────────────────────────────────────

class WidgetDado(QWidget):
    """
    Widget PyQt che mostra un dado con animazione pygame.

    Emette lancio_completato(risultato, totale, dettagli) quando
    l'animazione finisce — la vista_player.py lo ascolta per
    aggiungere il risultato al log.

    Come funziona il bridge PyQt↔pygame:
    Un QTimer chiama _aggiorna() ogni ~33ms (30fps).
    pygame disegna su una Surface, la Surface viene convertita
    in QPixmap e mostrata in un QLabel interno.
    """

    lancio_completato = pyqtSignal(int, int, str)
    # (risultato dado, totale con bonus, stringa descrittiva)

    def __init__(self, utente_id: int, parent=None):
        super().__init__(parent)
        self.utente_id   = utente_id
        self._skin_attive = carica_skin_attive(utente_id)
        self._animazione: AnimazioneDado | None = None
        self._surface:    pygame.Surface | None = None
        self._ultimo_tick: int = 0

        if not pygame.get_init():
            pygame.init()

        self.setMinimumSize(120, 120)
        self.setMaximumSize(200, 200)

        # Label che mostra il rendering pygame
        self._lbl_canvas = QLabel(self)
        self._lbl_canvas.setGeometry(0, 0, self.width(), self.height())
        self._lbl_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._surface = pygame.Surface((self.width(), self.height()))
        self._disegna_dado_fermo(20, 1)   # stato iniziale: d20 con 1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._aggiorna)

    def lancia(self, facce: int, num_dadi: int = 1,
               bonus_stat: str | None = None,
               statistiche: dict | None = None):
        """
        Avvia il lancio di num_dadi dadi da facce lati.

        facce:       tipo di dado (4, 6, 8...)
        num_dadi:    quanti dadi lanciare
        bonus_stat:  nome della statistica per il bonus (es. "forza")
        statistiche: dizionario statistiche del personaggio
        """
        tiri   = [lancia_dado(facce) for _ in range(num_dadi)]
        somma  = sum(tiri)
        bonus  = 0

        if bonus_stat and statistiche:
            valore = statistiche.get(bonus_stat, 10)
            bonus  = modificatore_statistica(valore)

        totale = somma + bonus

        # Costruiamo la stringa descrittiva per il log
        dettaglio = "+".join(str(t) for t in tiri)
        if bonus != 0:
            segno   = "+" if bonus >= 0 else ""
            desc    = f"{num_dadi}d{facce}: {dettaglio}{segno}{bonus} = {totale}"
        else:
            desc    = f"{num_dadi}d{facce}: {dettaglio} = {totale}"

        # Avvia l'animazione per il primo dado (rappresentativo)
        skin_id  = self._skin_attive.get(str(facce))
        skin_path = percorso_skin(skin_id, facce)
        self._animazione = AnimazioneDado(facce, tiri[0], skin_path)
        self._risultato_finale = totale
        self._descrizione      = desc
        self._ultimo_tick      = pygame.time.get_ticks()

        self._timer.start(1000 // FPS_ANIMAZIONE)

    def _aggiorna(self):
        """Chiamata ogni frame: aggiorna animazione e ridisegna."""
        if not self._animazione:
            return

        ora       = pygame.time.get_ticks()
        delta_ms  = ora - self._ultimo_tick
        self._ultimo_tick = ora

        self._animazione.aggiorna(delta_ms)

        # Ridisegna
        w, h = self.width(), self.height()
        if self._surface.get_size() != (w, h):
            self._surface = pygame.Surface((w, h))

        self._surface.fill(COLORE_SFONDO)
        cx = w // 2
        cy = h // 2
        raggio = min(w, h) // 2 - 10
        self._animazione.disegna(self._surface, cx, cy, raggio)
        self._trasferisci_a_pyqt()

        # Animazione finita
        if not self._animazione.in_corso:
            self._timer.stop()
            self.lancio_completato.emit(
                self._animazione.risultato,
                self._risultato_finale,
                self._descrizione
            )

    def _disegna_dado_fermo(self, facce: int, valore: int):
        """Disegna il dado fermo nello stato iniziale."""
        if not self._surface:
            return
        w, h = self._surface.get_size()
        self._surface.fill(COLORE_SFONDO)
        cx, cy = w // 2, h // 2
        raggio = min(w, h) // 2 - 10
        # Crea un'animazione "ferma" solo per il disegno
        anim = AnimazioneDado(facce, valore, None)
        anim.in_corso = False
        anim.valore_mostrato = valore
        anim.disegna(self._surface, cx, cy, raggio)
        self._trasferisci_a_pyqt()

    def _trasferisci_a_pyqt(self):
        """Copia la surface pygame nel QLabel."""
        if not self._surface:
            return
        w, h = self._surface.get_size()
        dati = pygame.image.tostring(self._surface, "RGB")
        qimg = QImage(dati, w, h, w * 3, QImage.Format.Format_RGB888)
        self._lbl_canvas.setPixmap(QPixmap.fromImage(qimg))
        self._lbl_canvas.resize(w, h)

    def resizeEvent(self, event):
        """Ridimensiona la surface quando il widget cambia dimensione."""
        super().resizeEvent(event)
        if pygame.get_init():
            self._surface = pygame.Surface((self.width(), self.height()))
            self._lbl_canvas.setGeometry(0, 0, self.width(), self.height())

    def chiudi(self):
        """Ferma il timer — chiamare prima di distruggere il widget."""
        self._timer.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  PANNELLO DADI COMPLETO — widget usato in vista_player.py
# ─────────────────────────────────────────────────────────────────────────────

class PannelloDadi(QWidget):
    """
    Pannello completo con:
    - Visualizzazione animata del dado (WidgetDado)
    - Selezione tipo dado, numero dadi, statistica bonus
    - Pulsante lancia
    - Etichetta risultato con totale

    Signal lancio_effettuato: emesso con la descrizione del lancio
    per aggiungerla al log della sessione.
    """

    lancio_effettuato = pyqtSignal(str)

    def __init__(self, utente_id: int, statistiche: dict = None, parent=None):
        super().__init__(parent)
        self.utente_id   = utente_id
        self.statistiche = statistiche or {}
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Dado animato ──────────────────────────────────────────────────────
        self._widget_dado = WidgetDado(self.utente_id)
        self._widget_dado.lancio_completato.connect(self._al_completamento)
        layout.addWidget(self._widget_dado)

        # ── Controlli ─────────────────────────────────────────────────────────
        controlli = QVBoxLayout()
        controlli.setSpacing(6)

        # Selezione dado
        riga_dado = QHBoxLayout()
        riga_dado.addWidget(QLabel("Dado:"))
        self._combo_dado = QComboBox()
        for facce in TIPI_DADO:
            self._combo_dado.addItem(f"d{facce}", facce)
        self._combo_dado.setCurrentIndex(5)   # d20 di default
        riga_dado.addWidget(self._combo_dado)
        controlli.addLayout(riga_dado)

        # Numero dadi
        riga_num = QHBoxLayout()
        riga_num.addWidget(QLabel("Numero:"))
        self._spin_num = QSpinBox()
        self._spin_num.setRange(1, 20)
        self._spin_num.setValue(1)
        self._spin_num.setPrefix("×")
        riga_num.addWidget(self._spin_num)
        controlli.addLayout(riga_num)

        # Statistica bonus
        controlli.addWidget(QLabel("Bonus statistica:"))
        self._combo_stat = QComboBox()
        self._combo_stat.addItem("Nessuno", None)
        from sessione.combattimento import modificatore_statistica
        for stat in ["forza", "destrezza", "costituzione",
                     "intelligenza", "saggezza", "carisma"]:
            val = self.statistiche.get(stat, 10)
            mod = modificatore_statistica(val)
            segno = "+" if mod >= 0 else ""
            self._combo_stat.addItem(f"{stat.capitalize()} ({segno}{mod})", stat)
        controlli.addWidget(self._combo_stat)

        # Pulsante lancia
        btn_lancia = QPushButton("🎲  Lancia!")
        btn_lancia.setMinimumHeight(36)
        btn_lancia.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        btn_lancia.clicked.connect(self._lancia)
        controlli.addWidget(btn_lancia)

        # Pulsante skin
        btn_skin = QPushButton("🎨 Skin dadi")
        btn_skin.clicked.connect(self._apri_skin)
        controlli.addWidget(btn_skin)

        # Risultato
        self._lbl_risultato = QLabel("—")
        self._lbl_risultato.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self._lbl_risultato.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_risultato.setStyleSheet("color: #ffdd44;")
        controlli.addWidget(self._lbl_risultato)

        controlli.addStretch()
        layout.addLayout(controlli)

    def _lancia(self):
        facce    = self._combo_dado.currentData()
        num      = self._spin_num.value()
        stat     = self._combo_stat.currentData()
        self._widget_dado.lancia(facce, num, stat, self.statistiche)

    def _al_completamento(self, risultato: int, totale: int, descrizione: str):
        """Aggiorna il display del risultato e notifica la sessione."""
        self._lbl_risultato.setText(str(totale))
        self.lancio_effettuato.emit(f"🎲 {descrizione}")

    def _apri_skin(self):
        """Apre la finestra di gestione skin dadi."""
        dialog = FinestraSkinDadi(self.utente_id, self)
        dialog.exec()
        # Ricarica le skin dopo eventuali modifiche
        self._widget_dado._skin_attive = carica_skin_attive(self.utente_id)

    def chiudi(self):
        """Ferma i timer interni — chiamare prima di distruggere."""
        self._widget_dado.chiudi()


# ─────────────────────────────────────────────────────────────────────────────
#  FINESTRA GESTIONE SKIN
# ─────────────────────────────────────────────────────────────────────────────

class FinestraSkinDadi(QDialog):
    """
    Finestra per gestire le skin dei dadi.

    Mostra per ogni tipo di dado:
    - La skin attualmente equipaggiata
    - Le skin acquistate disponibili
    - Pulsante per equipaggiare o rimuovere

    Le skin acquistate vengono lette dalla tabella acquisti
    con tipo_asset = "skin_dado".
    """

    def __init__(self, utente_id: int, parent=None):
        super().__init__(parent)
        self.utente_id   = utente_id
        self._skin_attive = carica_skin_attive(utente_id)
        self.setWindowTitle("Gestione skin dadi")
        self.setMinimumSize(480, 400)
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel(
            "Seleziona la skin per ogni tipo di dado.\n"
            "Le skin si acquistano nello Shop."))

        # Lista skin per dado
        self._combo_skin: dict[int, QComboBox] = {}
        from database.modelli import acquisti_utente
        acquisti = [a for a in acquisti_utente(self.utente_id)
                    if a["tipo_asset"] == "skin_dado"]

        for facce in TIPI_DADO:
            riga = QHBoxLayout()
            riga.addWidget(QLabel(f"d{facce}:"))

            combo = QComboBox()
            combo.addItem("Nessuna skin (default)", None)

            # Aggiunge solo le skin acquistate compatibili con questo dado
            for acq in acquisti:
                asset_id = acq["asset_id"]
                # Convenzione: skin_fuoco_d20, skin_arcana_d6, ecc.
                # Se l'asset_id non specifica il dado, è compatibile con tutti
                if f"_d{facce}" in asset_id or "_d" not in asset_id:
                    nome_display = asset_id.replace(f"_d{facce}", "").replace("_", " ").title()
                    combo.addItem(nome_display, asset_id)

            # Seleziona la skin attiva
            skin_corrente = self._skin_attive.get(str(facce))
            if skin_corrente:
                idx = combo.findData(skin_corrente)
                if idx >= 0:
                    combo.setCurrentIndex(idx)

            self._combo_skin[facce] = combo
            riga.addWidget(combo, stretch=1)
            layout.addLayout(riga)

        layout.addStretch()

        # Pulsanti
        riga_btn = QHBoxLayout()
        riga_btn.addStretch()
        btn_annulla = QPushButton("Annulla")
        btn_annulla.clicked.connect(self.reject)
        riga_btn.addWidget(btn_annulla)
        btn_salva = QPushButton("💾 Salva")
        btn_salva.clicked.connect(self._salva)
        riga_btn.addWidget(btn_salva)
        layout.addLayout(riga_btn)

    def _salva(self):
        """Salva le skin selezionate nel database."""
        nuove_skin = {}
        for facce, combo in self._combo_skin.items():
            nuove_skin[str(facce)] = combo.currentData()
        salva_skin_attive(self.utente_id, nuove_skin)
        QMessageBox.information(self, "Salvato", "Skin dadi aggiornate.")
        self.accept()
