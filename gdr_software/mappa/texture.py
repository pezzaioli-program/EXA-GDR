"""
mappa/texture.py — Gestore texture tileset per terreni esagonali
================================================================
Legge da un file PNG unico (tileset) e ritaglia le texture
in forma di esagono per ogni tipo di terreno.

STRUTTURA TILESET ATTESA (3 colonne × 4 righe, tile 128×128):
    [0,0] pianura   [0,1] deserto   [0,2] terra_scura
    [1,0] fango     [1,1] terra     [1,2] vegetazione
    [2,0] montagna  [2,1] minerali  [2,2] foresta
    [3,0] vuoto     [3,1] lava      [3,2] acqua

Ogni tileset acquistato dallo shop usa lo stesso schema posizionale
ma con grafica diversa. La cartella del tileset contiene UN SOLO
file chiamato "tileset.png".

CACHE:
    - _cache_tileset  : {cartella: pygame.Surface}  ← file caricato
    - _cache_texture  : {(terreno, dim_int, cartella): Surface ritagliata}
"""

import pygame
import math
import os

# ── Configurazione tileset ────────────────────────────────────────────────────

# Nome del file all'interno di ogni cartella tileset
NOME_FILE_TILESET = "tileset.png"

# Dimensioni di ogni tile nel tileset (pixel)
TILE_W = 128
TILE_H = 128

# Colore sfondo trasparente nel tileset
MAGENTA = (255, 0, 255)

# Mappa: nome_terreno → (riga, colonna) nel tileset
# Deve essere uguale per TUTTI i tileset (stessa posizione, grafica diversa)
MAPPA_TILE_POSIZIONI = {
    "pianura":      (0, 0),
    "deserto":      (0, 1),
    "terra_scura":  (0, 2),
    "fango":        (1, 0),
    "terra":        (1, 1),
    "vegetazione":  (1, 2),
    "montagna":     (2, 0),
    "minerali":     (2, 1),
    "foresta":      (2, 2),
    "vuoto":        (3, 0),
    "lava":         (3, 1),
    "acqua":        (3, 2),
}

# ── Cache ─────────────────────────────────────────────────────────────────────

# Tileset completi caricati: {percorso_cartella: pygame.Surface | None}
_cache_tileset: dict[str, object] = {}

# Texture esagonali ritagliate e scalate:
# {(nome_terreno, dim_int, percorso_cartella): pygame.Surface | None}
_cache_texture: dict[tuple, object] = {}


# ── Caricamento tileset ───────────────────────────────────────────────────────

def _carica_tileset(cartella: str) -> "pygame.Surface | None":
    """
    Carica il file tileset.png dalla cartella indicata.
    Usa la cache: carica dal disco solo la prima volta.
    """
    if cartella in _cache_tileset:
        return _cache_tileset[cartella]

    percorso = os.path.join(cartella, NOME_FILE_TILESET)
    if not os.path.exists(percorso):
        print(f"[TEXTURE] Tileset non trovato: {percorso}")
        _cache_tileset[cartella] = None
        return None

    try:
        surf = pygame.image.load(percorso).convert()
        surf.set_colorkey(MAGENTA)
        _cache_tileset[cartella] = surf
        return surf
    except Exception as e:
        print(f"[TEXTURE] Errore caricamento tileset {percorso}: {e}")
        _cache_tileset[cartella] = None
        return None


def _estrai_tile(tileset: "pygame.Surface", riga: int, col: int) -> "pygame.Surface":
    """Ritaglia un tile dalla griglia del tileset."""
    x = col * TILE_W
    y = riga * TILE_H
    tile = pygame.Surface((TILE_W, TILE_H))
    tile.blit(tileset, (0, 0), (x, y, TILE_W, TILE_H))
    tile.set_colorkey(MAGENTA)
    return tile


# ── Maschera esagono ──────────────────────────────────────────────────────────

def _crea_superficie_hex(tile: "pygame.Surface",
                         dimensione: float) -> "pygame.Surface":
    """
    Scala il tile alla dimensione dell'esagono e lo ritaglia
    con una maschera a forma di esagono (pointy-top).

    Restituisce una Surface SRCALPHA pronta per blit.
    """
    larghezza = int(math.sqrt(3) * dimensione) + 4
    altezza   = int(2 * dimensione) + 4
    cx = larghezza // 2
    cy = altezza   // 2

    # Scala il tile alle dimensioni dell'esagono
    tile_scalato = pygame.transform.scale(tile, (larghezza, altezza))

    # Superficie risultato con trasparenza
    risultato = pygame.Surface((larghezza, altezza), pygame.SRCALPHA)
    risultato.fill((0, 0, 0, 0))

    # Calcola vertici esagono pointy-top
    vertici = []
    for i in range(6):
        angolo = math.radians(60 * i + 30)
        vertici.append((
            cx + dimensione * math.cos(angolo),
            cy + dimensione * math.sin(angolo),
        ))

    # Maschera: esagono bianco su nero trasparente
    maschera = pygame.Surface((larghezza, altezza), pygame.SRCALPHA)
    maschera.fill((0, 0, 0, 0))
    pygame.draw.polygon(maschera, (255, 255, 255, 255), vertici)

    # Applica maschera pixel per pixel
    # (lento su griglie grandi → usare numpy se disponibile)
    try:
        import numpy as np
        arr_tile = pygame.surfarray.pixels3d(tile_scalato)
        arr_mask = pygame.surfarray.pixels2d(maschera)
        arr_out  = pygame.surfarray.pixels3d(risultato)
        arr_alpha = pygame.surfarray.pixels_alpha(risultato)

        # Dove la maschera è bianca (!=0), copia il pixel del tile
        mask_bool = arr_mask.T != 0
        arr_out[mask_bool]   = arr_tile[mask_bool]
        arr_alpha[mask_bool] = 255

    except ImportError:
        # Fallback senza numpy (più lento)
        for y in range(altezza):
            for x in range(larghezza):
                if x < larghezza and y < altezza:
                    alpha = maschera.get_at((x, y))[3]
                    if alpha > 0:
                        colore = tile_scalato.get_at((x, y))
                        risultato.set_at((x, y), colore)

    return risultato


# ── API pubblica ──────────────────────────────────────────────────────────────

def ottieni_texture_hex(nome_terreno: str,
                        cartella_tileset: str,
                        dimensione: float) -> "pygame.Surface | None":
    """
    Restituisce la texture a forma di esagono per il terreno dato,
    scalata alla dimensione corrente (tiene conto dello zoom).

    Parametri:
        nome_terreno     — chiave del terreno (es. "pianura", "acqua")
        cartella_tileset — percorso assoluto della cartella del tileset attivo
                           (es. "...asset/terreni/tileset_base")
        dimensione       — raggio dell'esagono in pixel (include lo zoom)

    Restituisce None se il tileset non esiste o il terreno non è mappato.
    In quel caso il codice di disegno userà il colore piatto come fallback.
    """
    if nome_terreno not in MAPPA_TILE_POSIZIONI:
        return None

    dim_int = int(round(dimensione))
    chiave  = (nome_terreno, dim_int, cartella_tileset)

    if chiave in _cache_texture:
        return _cache_texture[chiave]

    tileset = _carica_tileset(cartella_tileset)
    if tileset is None:
        _cache_texture[chiave] = None
        return None

    riga, col = MAPPA_TILE_POSIZIONI[nome_terreno]
    tile      = _estrai_tile(tileset, riga, col)
    texture   = _crea_superficie_hex(tile, dimensione)

    _cache_texture[chiave] = texture
    return texture


def svuota_cache_scalate():
    """
    Svuota la cache delle texture scalate (non i tileset caricati).
    Da chiamare quando lo zoom cambia di molto per liberare memoria.
    """
    _cache_texture.clear()


def cambia_tileset(nuova_cartella: str):
    """
    Cambia il tileset attivo svuotando la cache delle texture.
    I tileset già caricati rimangono in _cache_tileset.
    """
    _cache_texture.clear()


def svuota_tutto():
    """Svuota entrambe le cache. Chiamare alla chiusura del programma."""
    _cache_tileset.clear()
    _cache_texture.clear()
