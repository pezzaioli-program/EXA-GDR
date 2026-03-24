  """
mappa/map.py — Editor mappa esagonale con chunk system
=======================================================
Orientamento: pointy-top  |  Coordinate: assiali (q, r)

Funzionalità:
  - Mappa potenzialmente infinita (chunk 32×32, solo visibili in memoria)
  - Zoom con rotellina  |  Pan con Ctrl+trascina o tasto centrale
  - Menu tasto destro con accesso a sottolivelli
  - Sottolivelli con pavimenti e oggetti interni
  - Navigazione breadcrumb (World > Castello > Piano terra)
  - Pulsante salva + S da tastiera
"""

import sys
import os
import math

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pygame

from lingua.gestore import t, lingua_corrente
from npc.generatore import genera_npc, genera_nemico

from config import (
    FINESTRA_LARGHEZZA   as LARGHEZZA_FINESTRA,
    FINESTRA_ALTEZZA     as ALTEZZA_FINESTRA,
    HEX_DIMENSIONE       as DIMENSIONE_HEX,
    PANNELLO_LARGHEZZA   as LARGHEZZA_PANNELLO,
    TERRENI, PAVIMENTI, OGGETTI, OGGETTI_INTERNI,
    COLORE_BORDO_HEX     as COLORE_BORDO,
    COLORE_SELEZIONE_HEX as COLORE_SELEZIONE,
    COLORE_TESTO, COLORE_SFONDO as SFONDO,
    COLORE_PANNELLO, COLORE_VOCE_ATTIVA,
    COLORE_ANTEPRIMA_OK, COLORE_ANTEPRIMA_NO,
)

# ─────────────────────────────────────────────────────────────────────────────
#  CLASSE ESAGONO
# ─────────────────────────────────────────────────────────────────────────────

class Esagono:
    def __init__(self, q: int, r: int, terreno: str = "vuoto"):
        self.q = q
        self.r = r
        self.terreno  = terreno
        self.evento   = None
        self.visibile = True
        self.sottolivello_id = None   # id del sottolivello collegato
        self.oggetti = {"struttura": None, "viabilita": None, "mobile": []}

    def calcola_centro(self, dim: float, ox: int, oy: int):
        x = dim * (math.sqrt(3) * self.q + math.sqrt(3) / 2 * self.r)
        y = dim * (3 / 2 * self.r)
        return (x + ox, y + oy)

    def calcola_vertici(self, dim: float, ox: int, oy: int):
        cx, cy = self.calcola_centro(dim, ox, oy)
        return [
            (cx + dim * math.cos(math.radians(60 * i + 30)),
             cy + dim * math.sin(math.radians(60 * i + 30)))
            for i in range(6)
        ]

    def disegna(self, surface, dim, ox, oy, evidenziato=False,
                modalita_master=True, palette=None):
        if palette is None:
            palette = TERRENI
        vertici = self.calcola_vertici(dim, ox, oy)
        cx, cy  = self.calcola_centro(dim, ox, oy)

        if not modalita_master and not self.visibile:
            pygame.draw.polygon(surface, (15, 15, 15), vertici)
            pygame.draw.polygon(surface, COLORE_BORDO, vertici, 1)
            return

        colore = palette.get(self.terreno, palette.get("vuoto", (50, 50, 50)))
        pygame.draw.polygon(surface, colore, vertici)
        pygame.draw.polygon(surface,
                            COLORE_SELEZIONE if evidenziato else COLORE_BORDO,
                            vertici, 2)

        # Indicatore sottolivello
        if self.sottolivello_id and modalita_master:
            r_dot = max(3, int(dim * 0.15))
            pygame.draw.circle(surface, (100, 200, 255),
                               (int(cx) + int(dim * 0.35),
                                int(cy) - int(dim * 0.35)), r_dot)

        font = pygame.font.SysFont("Arial", max(8, int(dim * 0.38)), bold=True)

        # Struttura
        struttura = self.oggetti.get("struttura")
        if struttura:
            defn = struttura["def"]
            if struttura["origine"] == (self.q, self.r):
                raggio = int(dim * 0.42)
                pygame.draw.circle(surface, defn["colore"], (int(cx), int(cy)), raggio)
                pygame.draw.circle(surface, COLORE_BORDO,  (int(cx), int(cy)), raggio, 2)
                t = font.render(defn["icona"][:2], True, COLORE_TESTO)
                surface.blit(t, (int(cx) - t.get_width()//2,
                                  int(cy) - t.get_height()//2))
            else:
                pygame.draw.circle(surface, defn["colore"],
                                   (int(cx), int(cy)), int(dim * 0.18))

        # Viabilità
        via = self.oggetti.get("viabilita")
        if via:
            defn = via["def"]
            pygame.draw.circle(surface, defn["colore"],
                               (int(cx), int(cy)), int(dim * 0.22))
            if via["origine"] == (self.q, self.r):
                t = font.render(defn["icona"][:2], True, COLORE_TESTO)
                surface.blit(t, (int(cx) - t.get_width()//2,
                                  int(cy) - t.get_height()//2))

        # Evento
        if self.evento and modalita_master:
            fe = pygame.font.SysFont("Arial", max(6, int(dim * 0.28)))
            t  = fe.render("!", True, (255, 80, 80))
            surface.blit(t, (int(cx) + int(dim * 0.3),
                              int(cy) - int(dim * 0.5)))

    def __repr__(self):
        return f"Esagono({self.q},{self.r},'{self.terreno}')"


# ─────────────────────────────────────────────────────────────────────────────
#  CLASSE GRIGLIA (usata per sottolivelli a dimensioni fisse)
# ─────────────────────────────────────────────────────────────────────────────

class Griglia:
    def __init__(self, colonne, righe, dimensione, offset_x=60, offset_y=60):
        self.colonne    = colonne
        self.righe      = righe
        self.dimensione = dimensione
        self.offset_x   = offset_x
        self.offset_y   = offset_y
        self.celle: dict[tuple, Esagono] = {}
        self._costruisci()

    def _costruisci(self):
        for r in range(self.righe):
            for q in range(self.colonne):
                self.celle[(q, r)] = Esagono(q, r)

    def pixel_a_hex(self, px, py):
        x = px - self.offset_x
        y = py - self.offset_y
        q = (math.sqrt(3)/3 * x - 1/3 * y) / self.dimensione
        r = (2/3 * y) / self.dimensione
        return self._hex_round(q, r)

    def pixel_a_hex_zoom(self, px, py, dim_zoom):
        x = px - self.offset_x
        y = py - self.offset_y
        q = (math.sqrt(3)/3 * x - 1/3 * y) / dim_zoom
        r = (2/3 * y) / dim_zoom
        return self._hex_round(q, r)

    def _hex_round(self, q, r):
        s = -q - r
        rq, rr, rs = round(q), round(r), round(s)
        if abs(rq-q) > abs(rr-r) and abs(rq-q) > abs(rs-s):
            rq = -rr - rs
        elif abs(rr-r) > abs(rs-s):
            rr = -rq - rs
        return (rq, rr)

    def disegna(self, surface, hex_ev=None, master=True, palette=None):
        for (q, r), e in self.celle.items():
            e.disegna(surface, self.dimensione, self.offset_x, self.offset_y,
                      hex_ev == (q, r), master, palette)

    def disegna_zoom(self, surface, hex_ev=None, master=True,
                     dim_zoom=None, palette=None):
        d = dim_zoom or self.dimensione
        lw, lh = surface.get_size()

        # Calcola il range di celle visibili nella viewport
        # per non disegnare celle fuori schermo (ottimizzazione principale)
        margine = 2   # celle extra oltre il bordo visibile
        q_min = int((-(self.offset_x) / (d * math.sqrt(3))) - margine)
        r_min = int((-(self.offset_y) / (d * 1.5)) - margine)
        q_max = int(((lw - self.offset_x) / (d * math.sqrt(3))) + margine)
        r_max = int(((lh - self.offset_y) / (d * 1.5)) + margine)

        for (q, r), e in self.celle.items():
            # Salta celle fuori dalla viewport
            if q < q_min or q > q_max or r < r_min or r > r_max:
                continue
            e.disegna(surface, d, self.offset_x, self.offset_y,
                      hex_ev == (q, r), master, palette)

    def imposta_terreno(self, q, r, terreno):
        if (q, r) in self.celle:
            self.celle[(q, r)].terreno = terreno

    @staticmethod
    def ruota_offset(dq, dr):
        return (-dr, dq + dr)

    def calcola_celle_occupate(self, q0, r0, defn, rot):
        celle = []
        for (dq, dr) in defn["forma"]:
            for _ in range(rot % 6):
                dq, dr = self.ruota_offset(dq, dr)
            celle.append((q0 + dq, r0 + dr))
        return celle

    def puoi_piazzare(self, q0, r0, defn, rot):
        layer = defn["layer"]
        if layer == "mobile":
            return True
        for (q, r) in self.calcola_celle_occupate(q0, r0, defn, rot):
            if (q, r) not in self.celle:
                return False
            if self.celle[(q, r)].oggetti[layer] is not None:
                return False
        return True

    def piazza_oggetto(self, q0, r0, defn, rot):
        if not self.puoi_piazzare(q0, r0, defn, rot):
            return False
        layer = defn["layer"]
        celle = self.calcola_celle_occupate(q0, r0, defn, rot)
        ist   = {"def": defn, "origine": (q0, r0), "rotazione": rot}
        for (q, r) in celle:
            if layer == "mobile":
                self.celle[(q, r)].oggetti["mobile"].append(ist)
            else:
                self.celle[(q, r)].oggetti[layer] = ist
        return True

    def rimuovi_oggetto(self, q, r, layer):
        if (q, r) not in self.celle:
            return
        ist = self.celle[(q, r)].oggetti.get(layer)
        if not ist:
            return
        q0, r0 = ist["origine"]
        rot    = ist["rotazione"]
        celle  = self.calcola_celle_occupate(q0, r0, ist["def"], rot)
        for (cq, cr) in celle:
            if (cq, cr) in self.celle:
                if layer == "mobile":
                    self.celle[(cq, cr)].oggetti["mobile"] = [
                        o for o in self.celle[(cq, cr)].oggetti["mobile"]
                        if o is not ist]
                else:
                    self.celle[(cq, cr)].oggetti[layer] = None

    def __repr__(self):
        return f"Griglia({self.colonne}×{self.righe})"


# ─────────────────────────────────────────────────────────────────────────────
#  PANNELLO LATERALE
# ─────────────────────────────────────────────────────────────────────────────

class PannelloLaterale:
    ALTEZZA_VOCE   = 34
    ALTEZZA_HEADER = 30
    MARGINE        = 8
    RAGGIO         = 9

    def __init__(self, larghezza: int, altezza: int, e_interno: bool = False):
        self.larghezza   = larghezza
        self.altezza     = altezza
        self.e_interno   = e_interno
        self.modalita    = "pavimento" if e_interno else "terreno"
        self.terreno_selezionato   = "pietra" if e_interno else "pianura"
        self.oggetto_selezionato   = list(OGGETTI_INTERNI)[0] if e_interno else "casa"
        self.rotazione             = 0
        self.font_titolo = None
        self.font_voce   = None
        self._rect_terreni  = {}
        self._rect_oggetti  = {}
        self._rect_tab_ter  = None
        self._rect_tab_obj  = None
        self._rect_tab_npc  = None
        self._rect_tab_nem  = None
        self._rect_rot_su   = None
        self._rect_rot_giu  = None
        self._scroll_oggetti = 0
        # Liste NPC e Nemici piazzabili sulla mappa corrente
        self.lista_npc:    list[dict] = []
        self.lista_nemici: list[dict] = []
        self._rect_npc:    list[pygame.Rect] = []
        self._rect_nemici: list[pygame.Rect] = []
        self._scroll_npc   = 0
        self._scroll_nem   = 0
        self._npc_selezionato  = -1   # indice in lista_npc
        self._nem_selezionato  = -1   # indice in lista_nemici

    def inizializza_font(self):
        self.font_titolo = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_voce   = pygame.font.SysFont("Arial", 11)
        self._aggiorna_layout()

    @property
    def _palette(self):
        return PAVIMENTI if self.e_interno else TERRENI

    @property
    def _oggetti_correnti(self):
        return OGGETTI_INTERNI if self.e_interno else OGGETTI

    @property
    def _label_tab_ter(self):
        return "Pavimenti" if self.e_interno else "Terreni"

    def scorri(self, delta):
        if self.modalita not in ("terreno", "pavimento"):
            area_h    = self.altezza - self.ALTEZZA_HEADER - 10 - 70
            contenuto = len(self._oggetti_correnti) * self.ALTEZZA_VOCE
            max_sc    = max(0, contenuto - area_h)
            self._scroll_oggetti = max(0, min(
                self._scroll_oggetti - delta * 20, max_sc))

    def _y_lista(self):
        return 6 + self.ALTEZZA_HEADER + 4

    def _aggiorna_layout(self):
        # 4 tab: terreni/pavimenti | oggetti | npc | nemici
        w4 = self.larghezza // 4
        self._rect_tab_ter = pygame.Rect(0,    6, w4, self.ALTEZZA_HEADER)
        self._rect_tab_obj = pygame.Rect(w4,   6, w4, self.ALTEZZA_HEADER)
        self._rect_tab_npc = pygame.Rect(w4*2, 6, w4, self.ALTEZZA_HEADER)
        self._rect_tab_nem = pygame.Rect(w4*3, 6, w4, self.ALTEZZA_HEADER)
        # Compatibilità: w2 usato altrove
        w2 = self.larghezza // 2
        y_lista = self._y_lista()

        self._rect_terreni.clear()
        y = y_lista
        for nome in self._palette:
            self._rect_terreni[nome] = pygame.Rect(
                0, y, self.larghezza, self.ALTEZZA_VOCE)
            y += self.ALTEZZA_VOCE

        self._rect_oggetti.clear()
        y = y_lista - self._scroll_oggetti
        for oid in self._oggetti_correnti:
            self._rect_oggetti[oid] = pygame.Rect(
                0, y, self.larghezza, self.ALTEZZA_VOCE)
            y += self.ALTEZZA_VOCE

        y_rot = self.altezza - 60
        btn_w = (self.larghezza - self.MARGINE * 3) // 2
        self._rect_rot_giu = pygame.Rect(self.MARGINE, y_rot, btn_w, 24)
        self._rect_rot_su  = pygame.Rect(self.MARGINE*2+btn_w, y_rot, btn_w, 24)

    def disegna(self, surface):
        self._aggiorna_layout()
        pygame.draw.rect(surface, COLORE_PANNELLO,
                         (0, 0, self.larghezza, self.altezza))
        pygame.draw.line(surface, COLORE_BORDO,
                         (self.larghezza, 0), (self.larghezza, self.altezza), 2)

        y = 6
        tabs = [
            (self._rect_tab_ter, self._label_tab_ter, "terreno"),
            (self._rect_tab_obj, t("oggetti"),         "oggetto"),
            (self._rect_tab_npc, t("npc_tab"),         "npc"),
            (self._rect_tab_nem, t("nemici_tab"),      "nemico"),
        ]
        is_ter = self.modalita in ("terreno","pavimento")
        mod_map = {"terreno":"terreno","pavimento":"terreno",
                   "oggetto":"oggetto","npc":"npc","nemico":"nemico"}
        mod_norm = mod_map.get(self.modalita, "terreno")

        for rect, label, mod in tabs:
            attivo = mod_norm == mod
            pygame.draw.rect(surface, COLORE_VOCE_ATTIVA if attivo else COLORE_PANNELLO, rect)
            pygame.draw.rect(surface, COLORE_BORDO, rect, 1)
            tl = self.font_titolo.render(label[:4], True, COLORE_TESTO)
            surface.blit(tl, (rect.centerx - tl.get_width()//2, y + 8))

        if self.modalita in ("terreno","pavimento"):
            self._disegna_lista_terreni(surface)
        elif self.modalita == "oggetto":
            self._disegna_lista_oggetti(surface)
        elif self.modalita == "npc":
            self._disegna_lista_personaggi(surface, self.lista_npc,
                                           self._rect_npc, self._scroll_npc,
                                           self._npc_selezionato, "npc")
        else:
            self._disegna_lista_personaggi(surface, self.lista_nemici,
                                           self._rect_nemici, self._scroll_nem,
                                           self._nem_selezionato, "nemico")

    def _clip(self):
        y0  = self._y_lista()
        h   = self.altezza - y0 - 70
        return pygame.Rect(0, y0, self.larghezza, max(1, h))

    def _disegna_voce(self, surface, rect, colore, etichetta, sel, clip):
        if rect.bottom < clip.top or rect.top > clip.bottom:
            return
        if sel:
            pygame.draw.rect(surface, COLORE_VOCE_ATTIVA, rect.clip(clip))
        cx = self.MARGINE + self.RAGGIO
        cy = rect.y + self.ALTEZZA_VOCE // 2
        if clip.top <= cy <= clip.bottom:
            pygame.draw.circle(surface, colore, (cx, cy), self.RAGGIO)
            pygame.draw.circle(surface, COLORE_BORDO, (cx, cy), self.RAGGIO, 1)
            t = self.font_voce.render(etichetta, True, COLORE_TESTO)
            ty = cy - t.get_height() // 2
            if clip.top < ty and ty + t.get_height() < clip.bottom:
                surface.blit(t, (cx + self.RAGGIO + 5, ty))

    def _disegna_lista_terreni(self, surface):
        clip = self._clip()
        for nome, colore in self._palette.items():
            self._disegna_voce(surface, self._rect_terreni[nome], colore,
                               nome.replace("_", " ").capitalize(),
                               nome == self.terreno_selezionato, clip)

    def _disegna_lista_oggetti(self, surface):
        clip = self._clip()
        for oid, defn in self._oggetti_correnti.items():
            self._disegna_voce(surface, self._rect_oggetti[oid], defn["colore"],
                               defn["nome"], oid == self.oggetto_selezionato, clip)

        area_h    = clip.height
        contenuto = len(self._oggetti_correnti) * self.ALTEZZA_VOCE
        if contenuto > area_h:
            if self._scroll_oggetti > 0:
                s = self.font_voce.render("▲ scroll", True, (180,180,180))
                surface.blit(s, (self.MARGINE, clip.top + 2))
            if self._scroll_oggetti < contenuto - area_h:
                s = self.font_voce.render("▼ scroll", True, (180,180,180))
                surface.blit(s, (self.MARGINE, clip.bottom - 14))

        # Pulsanti rotazione
        tr = self.font_titolo.render(
            f"Rot: {self.rotazione*60}°", True, COLORE_TESTO)
        surface.blit(tr, (self.MARGINE, self._rect_rot_giu.y - 18))
        pygame.draw.rect(surface, COLORE_VOCE_ATTIVA, self._rect_rot_giu, border_radius=4)
        pygame.draw.rect(surface, COLORE_VOCE_ATTIVA, self._rect_rot_su,  border_radius=4)
        su  = self.font_voce.render("-60°", True, COLORE_TESTO)
        giu = self.font_voce.render("+60°", True, COLORE_TESTO)
        surface.blit(su,  (self._rect_rot_giu.centerx - su.get_width()//2,
                           self._rect_rot_giu.centery - su.get_height()//2))
        surface.blit(giu, (self._rect_rot_su.centerx  - giu.get_width()//2,
                           self._rect_rot_su.centery  - giu.get_height()//2))

    def _disegna_lista_personaggi(self, surface, lista, rects, scroll, sel_idx, tipo):
        """Disegna lista NPC o Nemici con pulsante Genera."""
        clip = self._clip()
        # Aggiorna rects
        y = self._y_lista() - scroll
        del rects[:]
        for i, pg in enumerate(lista):
            r = pygame.Rect(0, y, self.larghezza, self.ALTEZZA_VOCE)
            rects.append(r)
            if r.bottom < clip.top or r.top > clip.bottom:
                y += self.ALTEZZA_VOCE
                continue
            colore = tuple(pg.get("colore", (150,150,150)))
            self._disegna_voce(surface, r, colore, pg["nome"],
                               i == sel_idx, clip)
            y += self.ALTEZZA_VOCE

        # Messaggio lista vuota
        if not lista:
            chiave = "nessun_npc" if tipo == "npc" else "nessun_nemico"
            tl = self.font_voce.render(t(chiave), True, (120,120,140))
            surface.blit(tl, (self.MARGINE, clip.top + 8))

        # Due pulsanti in fondo: Genera casuale e Crea manuale
        y_btn = self.altezza - 80
        btn_gen = pygame.Rect(self.MARGINE, y_btn,
                              self.larghezza - self.MARGINE*2, 28)
        pygame.draw.rect(surface, (70, 100, 70), btn_gen, border_radius=4)
        chiave_btn = "genera_npc" if tipo == "npc" else "genera_nemico"
        tg = self.font_voce.render(t(chiave_btn), True, COLORE_TESTO)
        surface.blit(tg, (btn_gen.centerx - tg.get_width()//2,
                           btn_gen.centery - tg.get_height()//2))

        y_btn2 = self.altezza - 46
        btn_crea = pygame.Rect(self.MARGINE, y_btn2,
                               self.larghezza - self.MARGINE*2, 28)
        pygame.draw.rect(surface, (60, 60, 100), btn_crea, border_radius=4)
        lbl_crea = "➕ Crea NPC" if tipo == "npc" else "➕ Crea Nemico"
        tc = self.font_voce.render(lbl_crea, True, COLORE_TESTO)
        surface.blit(tc, (btn_crea.centerx - tc.get_width()//2,
                           btn_crea.centery - tc.get_height()//2))

        if tipo == "npc":
            self._rect_btn_genera_npc = btn_gen
            self._rect_btn_crea_npc   = btn_crea
        else:
            self._rect_btn_genera_nem = btn_gen
            self._rect_btn_crea_nem   = btn_crea

        chiave_btn = "genera_npc" if tipo == "npc" else "genera_nemico"
        tg = self.font_voce.render(t(chiave_btn), True, COLORE_TESTO)
        surface.blit(tg, (btn_gen.centerx - tg.get_width()//2,
                           btn_gen.centery - tg.get_height()//2))
        # Salva rect pulsante per il click
        if tipo == "npc":
            self._rect_btn_genera_npc = btn_gen
        else:
            self._rect_btn_genera_nem = btn_gen

    def gestisci_click(self, mx, my):
        if mx > self.larghezza:
            return False
        self._aggiorna_layout()

        # Tab
        if self._rect_tab_ter.collidepoint(mx, my):
            self.modalita = "pavimento" if self.e_interno else "terreno"
            self._scroll_oggetti = 0
            return True
        if self._rect_tab_obj.collidepoint(mx, my):
            self.modalita = "oggetto"
            return True
        if self._rect_tab_npc and self._rect_tab_npc.collidepoint(mx, my):
            self.modalita = "npc"
            return True
        if self._rect_tab_nem and self._rect_tab_nem.collidepoint(mx, my):
            self.modalita = "nemico"
            return True

        is_ter = self.modalita in ("terreno", "pavimento")
        y0 = self._y_lista()

        if is_ter:
            for nome, rect in self._rect_terreni.items():
                if rect.collidepoint(mx, my):
                    self.terreno_selezionato = nome
                    return True

        elif self.modalita == "oggetto":
            for oid, rect in self._rect_oggetti.items():
                if rect.collidepoint(mx, my) and y0 <= my <= self.altezza - 70:
                    self.oggetto_selezionato = oid
                    return True

        elif self.modalita == "npc":
            btn = getattr(self, "_rect_btn_genera_npc", None)
            if btn and btn.collidepoint(mx, my):
                nuovo = genera_npc(lingua_corrente())
                self.lista_npc.append(nuovo)
                self._npc_selezionato = len(self.lista_npc) - 1
                return "apri_scheda_npc"
            for i, rect in enumerate(self._rect_npc):
                if rect.collidepoint(mx, my) and y0 <= my <= self.altezza - 55:
                    self._npc_selezionato = i
                    return True

            btn_crea = getattr(self, "_rect_btn_crea_npc", None)
            if btn_crea and btn_crea.collidepoint(mx, my):
                # Scheda NPC vuota da compilare
                vuoto = {
                    "tipo": "npc", "nome": "Nuovo NPC", "razza": "Umano",
                    "classe": "Mercante", "pf": 10, "pf_max": 10, "ca": 10,
                    "statistiche": {"for":10,"des":10,"cos":10,"int":10,"sag":10,"car":10},
                    "colore": (150, 150, 200),
                }
                self.lista_npc.append(vuoto)
                self._npc_selezionato = len(self.lista_npc) - 1
                return "apri_scheda_npc"
      
        elif self.modalita == "nemico":
            btn = getattr(self, "_rect_btn_genera_nem", None)
            if btn and btn.collidepoint(mx, my):
                nuovo = genera_nemico(lingua_corrente())
                self.lista_nemici.append(nuovo)
                self._nem_selezionato = len(self.lista_nemici) - 1
                return "apri_scheda_nem"
            for i, rect in enumerate(self._rect_nemici):
                if rect.collidepoint(mx, my) and y0 <= my <= self.altezza - 55:
                    self._nem_selezionato = i
                    return True

            btn_crea = getattr(self, "_rect_btn_crea_nem", None)
            if btn_crea and btn_crea.collidepoint(mx, my):
                vuoto = {
                    "tipo": "nemico", "nome": "Nuovo Nemico", "razza": "Goblin",
                     "classe": "Goblin", "difficolta": "medio",
                    "pf": 15, "pf_max": 15, "ca": 12,
                    "statistiche": {"for":10,"des":10,"cos":10,"int":8,"sag":8,"car":6},
                    "colore": (200, 80, 80),
                }
                self.lista_nemici.append(vuoto)
                self._nem_selezionato = len(self.lista_nemici) - 1
                return "apri_scheda_nem"
              
        if self._rect_rot_giu and self._rect_rot_giu.collidepoint(mx, my):
            self.rotazione = (self.rotazione - 1) % 6
            return True
        if self._rect_rot_su and self._rect_rot_su.collidepoint(mx, my):
            self.rotazione = (self.rotazione + 1) % 6
            return True
        return True


# ─────────────────────────────────────────────────────────────────────────────
#  EDITOR PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def demo(griglia_esistente=None, mappa_id=None):
    """
    Avvia l'editor mappa.

    Controlli:
      Rotellina mappa   — zoom
      Ctrl+trascina /
      Tasto centrale    — pan (muovi vista)
      Click sin (ter)   — pittura terreno trascinando
      Click sin (obj)   — piazza oggetto (trascina per 1 cella)
      Tasto destro      — menu contestuale
      Rotellina pannello— scroll lista oggetti
      M                 — toggle Master/Player
      S                 — salva
      Backspace         — torna al livello superiore (se in sottolivello)
      ESC               — chiudi
    """
    pygame.init()
    lw = max(1400, LARGHEZZA_FINESTRA)
    lh = max(900,  ALTEZZA_FINESTRA)
    schermo = pygame.display.set_mode((lw, lh), pygame.RESIZABLE)
    clock   = pygame.time.Clock()

    # ── Stack di navigazione: ogni elemento = (griglia, mappa_id, titolo, palette) ──
    # Il primo elemento è sempre il livello world
    if griglia_esistente is None:
        from mappa.chunk import GestoreChunk, CHUNK_SIZE
        usa_chunk = mappa_id is not None
    else:
        usa_chunk = False

    # Per ora usiamo sempre Griglia normale (chunk nella versione futura)
    if griglia_esistente:
        griglia_world = griglia_esistente
        griglia_world.offset_x = LARGHEZZA_PANNELLO + 20
        griglia_world.offset_y = 60
    else:
        griglia_world = Griglia(30, 20, DIMENSIONE_HEX,
                                offset_x=LARGHEZZA_PANNELLO + 20, offset_y=60)

    # Stack navigazione: (griglia, mappa_id_o_sottolivello_id,
    #                     titolo_breadcrumb, palette, e_interno)
    stack = [(griglia_world, mappa_id, "World", TERRENI, False)]

    def livello_corrente():
        return stack[-1]

    # ── Stato editor ──────────────────────────────────────────────────────────
    zoom        = 1.0
    ZOOM_MIN    = 0.15
    ZOOM_MAX    = 4.0
    ZOOM_STEP   = 0.12
    pan_attivo  = False
    pan_ultimo  = (0, 0)
    tasto_prem  = False
    master      = True
    salvato     = True

    from mappa.menu_contestuale import MenuContestuale
    menu = MenuContestuale()

    def titolo_aggiornato():
        griglia, mid, titolo, palette, interno = livello_corrente()
        breadcrumb = " > ".join(s[2] for s in stack)
        mod = "" if salvato else " *"
        return f"GDR Hex — {breadcrumb}{mod}"

    def aggiorna_titolo():
        pygame.display.set_caption(titolo_aggiornato())

    aggiorna_titolo()

    def pannello_corrente():
        _, _, _, _, interno = livello_corrente()
        p = PannelloLaterale(LARGHEZZA_PANNELLO, lh, interno)
        p.inizializza_font()
        return p

    pannello = pannello_corrente()

    def salva():
        nonlocal salvato
        griglia, mid, titolo, palette, interno = livello_corrente()
        if mid is None:
            return
        if interno:
            from mappa.sottolivello import salva_dati_sottolivello
            from mappa.esporta import griglia_a_dizionario
            salva_dati_sottolivello(mid, griglia_a_dizionario(griglia))
        else:
            from mappa.esporta import salva_griglia_nel_db
            salva_griglia_nel_db(mid, griglia)
        salvato = True
        aggiorna_titolo()

    def segna_mod():
        nonlocal salvato
        if salvato:
            salvato = False
            aggiorna_titolo()

    def entra_sottolivello(cella):
        """Entra nel sottolivello della cella corrente."""
        if not cella.sottolivello_id:
            return
        from mappa.sottolivello import carica_sottolivello
        from mappa.esporta import dizionario_a_griglia
        dati = carica_sottolivello(cella.sottolivello_id)
        if not dati:
            return
        import json as _json
        dati_json = _json.loads(dati["dati_json"]) if dati["dati_json"] != '{}' else None
        if dati_json and dati_json.get("celle"):
            gr = dizionario_a_griglia(dati_json)
        else:
            gr = Griglia(dati["colonne"], dati["righe"], DIMENSIONE_HEX,
                         offset_x=LARGHEZZA_PANNELLO + 20, offset_y=60)
        gr.offset_x = LARGHEZZA_PANNELLO + 20
        gr.offset_y = 60
        titolo = f"{dati['oggetto_id'].capitalize()} ({cella.q},{cella.r})"
        stack.append((gr, cella.sottolivello_id, titolo, PAVIMENTI, True))
        nonlocal pannello, zoom
        pannello = pannello_corrente()
        zoom = 1.0
        aggiorna_titolo()

    def crea_sottolivello_per(cella):
        """Crea un nuovo sottolivello per la cella e ci entra."""
        struttura = cella.oggetti.get("struttura")
        if not struttura:
            return
        obj_id = struttura["def"]["id"]
        griglia, mid, *_ = livello_corrente()
        if mid is None:
            return
        from mappa.sottolivello import crea_sottolivello
        sl_id = crea_sottolivello(mid, obj_id, cella.q, cella.r)
        cella.sottolivello_id = sl_id
        segna_mod()
        entra_sottolivello(cella)

    def torna_su():
        nonlocal pannello, zoom
        if len(stack) <= 1:
            return
        salva()
        stack.pop()
        pannello = pannello_corrente()
        zoom = 1.0
        aggiorna_titolo()

    running = True
    while running:
        lw, lh = schermo.get_size()
        pannello.altezza = lh
        schermo.fill(SFONDO)

        mx, my = pygame.mouse.get_pos()
        ctrl   = pygame.key.get_mods() & pygame.KMOD_CTRL

        griglia, mid, _, palette, interno = livello_corrente()
        dim_zoom = griglia.dimensione * zoom
        hq, hr   = griglia.pixel_a_hex_zoom(mx, my, dim_zoom)
        hex_curr = (hq, hr) if (hq, hr) in griglia.celle else None
        is_ter   = pannello.modalita in ("terreno", "pavimento")

        # Pan
        if pan_attivo:
            dx = mx - pan_ultimo[0]
            dy = my - pan_ultimo[1]
            griglia.offset_x += dx
            griglia.offset_y += dy
            pan_ultimo = (mx, my)

        # Pittura terreno trascinando
        if (tasto_prem and hex_curr and mx > LARGHEZZA_PANNELLO
                and is_ter and not menu.visibile):
            griglia.celle[hex_curr].terreno = pannello.terreno_selezionato
            segna_mod()

        # Trascinamento oggetti 1 cella
        if (tasto_prem and hex_curr and mx > LARGHEZZA_PANNELLO
                and not is_ter and not menu.visibile):
            tutti_obj = OGGETTI_INTERNI if interno else OGGETTI
            defn = tutti_obj.get(pannello.oggetto_selezionato)
            if defn and len(defn["forma"]) == 1:
                if griglia.puoi_piazzare(hq, hr, defn, pannello.rotazione):
                    griglia.piazza_oggetto(hq, hr, defn, pannello.rotazione)
                    segna_mod()

        # Anteprima oggetto
        celle_ant = []
        if (hex_curr and not is_ter and mx > LARGHEZZA_PANNELLO
                and not pan_attivo and not menu.visibile):
            tutti_obj = OGGETTI_INTERNI if interno else OGGETTI
            defn = tutti_obj.get(pannello.oggetto_selezionato)
            if defn:
                celle_ant = griglia.calcola_celle_occupate(
                    hq, hr, defn, pannello.rotazione)

        # Disegno griglia
        griglia.disegna_zoom(schermo, hex_curr, master, dim_zoom, palette)

        # Anteprima verde/rossa
        for (aq, ar) in celle_ant:
            if (aq, ar) in griglia.celle:
                tutti_obj = OGGETTI_INTERNI if interno else OGGETTI
                defn = tutti_obj.get(pannello.oggetto_selezionato)
                if defn:
                    ok  = griglia.puoi_piazzare(hq, hr, defn, pannello.rotazione)
                    col = (*COLORE_ANTEPRIMA_OK, 100) if ok else (*COLORE_ANTEPRIMA_NO, 100)
                    vrt = griglia.celle[(aq, ar)].calcola_vertici(
                        dim_zoom, griglia.offset_x, griglia.offset_y)
                    tmp = pygame.Surface((lw, lh), pygame.SRCALPHA)
                    pygame.draw.polygon(tmp, col, vrt)
                    schermo.blit(tmp, (0, 0))

        pannello.disegna(schermo)

        # ── Barra in alto ─────────────────────────────────────────────────────
        barra_h = 40
        pygame.draw.rect(schermo, (35, 35, 48),
                         (LARGHEZZA_PANNELLO, 0, lw - LARGHEZZA_PANNELLO, barra_h))
        pygame.draw.line(schermo, COLORE_BORDO,
                         (LARGHEZZA_PANNELLO, barra_h), (lw, barra_h), 1)

        font_hud = pygame.font.SysFont("Arial", 13)
        font_btn = pygame.font.SysFont("Arial", 12, bold=True)

        # Pulsante SALVA
        btn_salva = pygame.Rect(lw - 130, 6, 120, 28)
        c_btn = (50, 120, 50) if salvato else (130, 75, 20)
        pygame.draw.rect(schermo, c_btn, btn_salva, border_radius=5)
        pygame.draw.rect(schermo, (160, 160, 160), btn_salva, 1, border_radius=5)
        lbl = "✓ Salvata" if salvato else "💾 Salva (S)"
        ts  = font_btn.render(lbl, True, COLORE_TESTO)
        schermo.blit(ts, (btn_salva.centerx - ts.get_width()//2,
                           btn_salva.centery - ts.get_height()//2))

        # Pulsante TORNA SU (se in sottolivello)
        btn_torna = None
        if len(stack) > 1:
            btn_torna = pygame.Rect(lw - 270, 6, 130, 28)
            pygame.draw.rect(schermo, (60, 60, 100), btn_torna, border_radius=5)
            pygame.draw.rect(schermo, (160,160,160), btn_torna, 1, border_radius=5)
            tt = font_btn.render("← Torna su (⌫)", True, COLORE_TESTO)
            schermo.blit(tt, (btn_torna.centerx - tt.get_width()//2,
                               btn_torna.centery - tt.get_height()//2))

        # Info breadcrumb + zoom
        breadcrumb = " > ".join(s[2] for s in stack)
        info = font_hud.render(
            f"{breadcrumb}   |   Zoom {zoom:.1f}x   "
            f"Ctrl+trascina: pan   Rotellina: zoom",
            True, COLORE_TESTO)
        schermo.blit(info, (LARGHEZZA_PANNELLO + 10, 12))

        # HUD in basso
        if is_ter:
            azione = f"{'Pavimento' if interno else 'Terreno'}: {pannello.terreno_selezionato}"
        else:
            tutti_obj = OGGETTI_INTERNI if interno else OGGETTI
            defn = tutti_obj.get(pannello.oggetto_selezionato)
            if defn and hex_curr:
                ok = griglia.puoi_piazzare(hq, hr, defn, pannello.rotazione)
                azione = (f"Oggetto: {defn['nome']}  rot:{pannello.rotazione*60}°  "
                          f"{'✓ OK' if ok else '✗ bloccato'}")
            else:
                azione = f"Oggetto: {pannello.oggetto_selezionato}"
        hud = font_hud.render(
            f"{azione}   | Dx: menu   M: master   ESC: chiudi",
            True, COLORE_TESTO)
        schermo.blit(hud, (LARGHEZZA_PANNELLO + 10, lh - 22))

        # Menu contestuale
        menu.aggiorna_hover(mx, my)
        menu.disegna(schermo)

        pygame.display.flip()
        clock.tick(30)

        # ── Gestione eventi ───────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_m:
                    master = not master
                elif event.key == pygame.K_s:
                    salva()
                elif event.key == pygame.K_BACKSPACE:
                    torna_su()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Click sul pulsante SALVA
                if event.button == 1 and btn_salva.collidepoint(mx, my):
                    salva()
                    continue

                # Click sul pulsante TORNA SU
                if event.button == 1 and btn_torna and btn_torna.collidepoint(mx, my):
                    torna_su()
                    continue

                # Menu contestuale aperto — gestisci click
                if menu.visibile:
                    azione_menu = menu.gestisci_click(mx, my)
                    if azione_menu and azione_menu != "__consumato__":
                        # Usa la cella salvata al momento dell'apertura del menu
                        cella_m = getattr(menu, "_cella_salvata", None)
                        hqm     = getattr(menu, "_hq_salvato", 0)
                        hrm     = getattr(menu, "_hr_salvato", 0)
                        if cella_m is not None:
                            if azione_menu == "rimuovi":
                                if cella_m.oggetti["struttura"]:
                                    griglia.rimuovi_oggetto(hqm, hrm, "struttura")
                                elif cella_m.oggetti["viabilita"]:
                                    griglia.rimuovi_oggetto(hqm, hrm, "viabilita")
                                segna_mod()
                            elif azione_menu == "rimuovi_terreno":
                                cella_m.terreno = "vuoto_interno" if interno else "vuoto"
                                segna_mod()
                            elif azione_menu == "entra":
                                entra_sottolivello(cella_m)
                            elif azione_menu == "crea_sottolivello":
                                crea_sottolivello_per(cella_m)
                    continue

                if event.button == 1:
                    if ctrl and mx > LARGHEZZA_PANNELLO:
                        pan_attivo = True
                        pan_ultimo = (mx, my)
                    else:
                        click_pan = pannello.gestisci_click(mx, my)

                        # Apri scheda NPC appena generato
                        if click_pan == "apri_scheda_npc":
                            import pygame as _pg
                            _pg.display.iconify()  # minimizza temporaneamente
                            from npc.scheda_npc import SchedaNPC
                            from PyQt6.QtWidgets import QApplication
                            app_qt = QApplication.instance()
                            if app_qt and pannello.lista_npc:
                                idx = pannello._npc_selezionato
                                dlg = SchedaNPC(pannello.lista_npc[idx])
                                def aggiorna_npc(d, i=idx):
                                    pannello.lista_npc[i] = d
                                dlg.scheda_aggiornata.connect(aggiorna_npc)
                                dlg.exec()
                            _pg.display.set_mode((lw, lh), pygame.RESIZABLE)

                        elif click_pan == "apri_scheda_nem":
                            import pygame as _pg
                            _pg.display.iconify()
                            from npc.scheda_npc import SchedaNPC
                            from PyQt6.QtWidgets import QApplication
                            app_qt = QApplication.instance()
                            if app_qt and pannello.lista_nemici:
                                idx = pannello._nem_selezionato
                                dlg = SchedaNPC(pannello.lista_nemici[idx])
                                def aggiorna_nem(d, i=idx):
                                    pannello.lista_nemici[i] = d
                                dlg.scheda_aggiornata.connect(aggiorna_nem)
                                dlg.exec()
                            _pg.display.set_mode((lw, lh), pygame.RESIZABLE)

                        elif not click_pan and mx > LARGHEZZA_PANNELLO:
                            if is_ter:
                                tasto_prem = True
                            elif pannello.modalita == "oggetto" and hex_curr:
                                tutti_obj = OGGETTI_INTERNI if interno else OGGETTI
                                defn = tutti_obj.get(pannello.oggetto_selezionato)
                                if defn:
                                    ok = griglia.piazza_oggetto(
                                        hq, hr, defn, pannello.rotazione)
                                    if ok:
                                        segna_mod()
                                        tasto_prem = True
                            elif pannello.modalita in ("npc","nemico") and hex_curr:
                                # Piazza il personaggio selezionato come token mobile
                                lista = (pannello.lista_npc
                                         if pannello.modalita == "npc"
                                         else pannello.lista_nemici)
                                idx   = (pannello._npc_selezionato
                                         if pannello.modalita == "npc"
                                         else pannello._nem_selezionato)
                                if 0 <= idx < len(lista):
                                    pg   = lista[idx]
                                    cella = griglia.celle[hex_curr]
                                    cella.oggetti["mobile"].append({
                                        "tipo":      pg["tipo"],
                                        "nome":      pg["nome"],
                                        "colore":    tuple(pg.get("colore",(200,100,100))),
                                        "scheda":    pg,
                                    })
                                    segna_mod()

                elif event.button == 2 and mx > LARGHEZZA_PANNELLO:
                    pan_attivo = True
                    pan_ultimo = (mx, my)

                elif event.button == 3:
                    # Menu contestuale — salva la cella al momento dell'apertura
                    if mx > LARGHEZZA_PANNELLO:
                        hq2, hr2 = griglia.pixel_a_hex_zoom(mx, my, dim_zoom)
                        cella_menu = griglia.celle.get((hq2, hr2))
                        ha_sl = bool(cella_menu.sottolivello_id) if cella_menu else False
                        menu.apri(mx, my, cella_menu, ha_sl, lw, lh)
                        menu._cella_salvata   = cella_menu
                        menu._hq_salvato      = hq2
                        menu._hr_salvato      = hr2

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    tasto_prem = False
                    pan_attivo = False
                elif event.button == 2:
                    pan_attivo = False

            elif event.type == pygame.MOUSEWHEEL:
                if mx < LARGHEZZA_PANNELLO:
                    pannello.scorri(event.y)
                elif not menu.visibile:
                    vecchio = zoom
                    zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom + event.y * ZOOM_STEP))
                    f = zoom / vecchio
                    griglia.offset_x = int(mx - (mx - griglia.offset_x) * f)
                    griglia.offset_y = int(my - (my - griglia.offset_y) * f)

            elif event.type == pygame.VIDEORESIZE:
                pannello.altezza = event.h

    # Salva tutto prima di chiudere
    salva()
    pygame.quit()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            mappa_id = int(sys.argv[1])
            from mappa.esporta import carica_griglia_dal_db
            griglia_caricata = carica_griglia_dal_db(mappa_id)
            demo(griglia_esistente=griglia_caricata, mappa_id=mappa_id)
        except Exception as e:
            print(f"[ERRORE] {e}")
            import traceback; traceback.print_exc()
            demo()
    else:
        demo()
