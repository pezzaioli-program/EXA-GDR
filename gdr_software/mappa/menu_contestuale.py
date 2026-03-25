"""
mappa/menu_contestuale.py — Menu tasto destro nell'editor
==========================================================
Appare quando il DM fa click destro su un esagono.
Opzioni diverse in base al contenuto della cella.
"""

import pygame


class MenuContestuale:
    """
    Menu a tendina che appare al click destro.

    Voci variano in base al contenuto:
    - Cella vuota:    Rimuovi terreno
    - Cella con obj:  Modifica oggetto | Cambia skin | Entra | Rimuovi
    """

    LARGHEZZA  = 200
    ALTEZZA_V  = 32
    MARGINE    = 10
    COLORE_BG  = (45, 45, 58)
    COLORE_V   = (60, 60, 76)
    COLORE_HOV = (80, 80, 110)
    COLORE_SEP = (70, 70, 85)
    COLORE_TXT = (220, 220, 220)
    COLORE_TXT_DIS = (100, 100, 120)

    def __init__(self):
        self.visibile   = False
        self.x          = 0
        self.y          = 0
        self._voci:     list[dict] = []
        self._font      = None
        self._rects:    list[pygame.Rect] = []
        self._hover_idx = -1

    def inizializza_font(self):
        self._font = pygame.font.SysFont("Arial", 13)

    def apri(self, mx: int, my: int, cella, ha_sottolivello: bool,
             larghezza_win: int, altezza_win: int):
        """
        Costruisce le voci in base al contenuto della cella e apre il menu.
        """
        self._voci = []
        self.visibile = True

        struttura = cella.oggetti.get("struttura") if cella else None
        viabilita = cella.oggetti.get("viabilita") if cella else None
        oggetto   = struttura or viabilita

        if oggetto:
            nome = oggetto["def"]["nome"]
            self._voci.append({"label": f"🔲 {nome}", "azione": None,
                                "disabilitato": True})
            self._voci.append({"label": "─────────────", "azione": None,
                                "separatore": True})
            self._voci.append({"label": "✏️  Modifica oggetto",
                                "azione": "modifica"})
            self._voci.append({"label": "🎨  Cambia skin",
                                "azione": "skin"})
            if ha_sottolivello:
                self._voci.append({"label": "🚪  Entra nel sottolivello",
                                   "azione": "entra"})
            else:
                layer = oggetto["def"].get("layer", "")
                obj_id = oggetto["def"]["id"]
                from mappa.sottolivello import OGGETTI_CON_SOTTOLIVELLO
                if obj_id in OGGETTI_CON_SOTTOLIVELLO:
                    self._voci.append({"label": "🏗️  Crea sottolivello",
                                       "azione": "crea_sottolivello"})
            self._voci.append({"label": "─────────────", "azione": None,
                                "separatore": True})
            self._voci.append({"label": "🗑️  Rimuovi oggetto",
                                "azione": "rimuovi"})
        else:
            self._voci.append({"label": "🗑️  Rimuovi terreno",
                                "azione": "rimuovi_terreno"})

        # Aggiusta posizione per non uscire dalla finestra
        altezza_menu = len(self._voci) * self.ALTEZZA_V
        self.x = min(mx, larghezza_win - self.LARGHEZZA - 4)
        self.y = min(my, altezza_win  - altezza_menu - 4)

        self._costruisci_rects()

    def _costruisci_rects(self):
        self._rects = []
        for i in range(len(self._voci)):
            self._rects.append(
                pygame.Rect(self.x, self.y + i * self.ALTEZZA_V,
                            self.LARGHEZZA, self.ALTEZZA_V))

    def chiudi(self):
        self.visibile = False
        self._hover_idx = -1

    def aggiorna_hover(self, mx: int, my: int):
        self._hover_idx = -1
        for i, rect in enumerate(self._rects):
            if rect.collidepoint(mx, my):
                v = self._voci[i]
                if not v.get("separatore") and not v.get("disabilitato"):
                    self._hover_idx = i
                break

    def gestisci_click(self, mx: int, my: int) -> str | None:
        """
        Restituisce la stringa azione se viene cliccata una voce,
        altrimenti None (click fuori dal menu → chiudi).
        """
        if not self.visibile:
            return None

        for i, rect in enumerate(self._rects):
            if rect.collidepoint(mx, my):
                v = self._voci[i]
                if not v.get("separatore") and not v.get("disabilitato"):
                    self.chiudi()
                    return v["azione"]
                return "__consumato__"

        self.chiudi()
        return None

    def disegna(self, surface: pygame.Surface):
        if not self.visibile or not self._font:
            return

        # Ombra
        ombra = pygame.Surface((self.LARGHEZZA + 4, len(self._voci) * self.ALTEZZA_V + 4),
                                pygame.SRCALPHA)
        ombra.fill((0, 0, 0, 80))
        surface.blit(ombra, (self.x + 3, self.y + 3))

        for i, (voce, rect) in enumerate(zip(self._voci, self._rects)):
            if voce.get("separatore"):
                pygame.draw.line(surface, self.COLORE_SEP,
                                 (rect.x + self.MARGINE, rect.centery),
                                 (rect.right - self.MARGINE, rect.centery), 1)
                continue

            # Sfondo voce
            colore_bg = self.COLORE_HOV if i == self._hover_idx else self.COLORE_BG
            pygame.draw.rect(surface, colore_bg, rect)

            # Testo
            dis = voce.get("disabilitato", False)
            col_txt = self.COLORE_TXT_DIS if dis else self.COLORE_TXT
            testo = self._font.render(voce["label"], True, col_txt)
            surface.blit(testo, (rect.x + self.MARGINE,
                                  rect.centery - testo.get_height() // 2))

        # Bordo esterno
        pygame.draw.rect(surface, self.COLORE_SEP,
                         pygame.Rect(self.x, self.y, self.LARGHEZZA,
                                     len(self._voci) * self.ALTEZZA_V), 1)
