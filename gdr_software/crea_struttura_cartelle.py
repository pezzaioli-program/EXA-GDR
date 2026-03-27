"""
crea_struttura_cartelle.py
==========================
Script di setup da eseguire UNA SOLA VOLTA.
Crea tutte le cartelle necessarie per i tileset e un README
che spiega al grafico dove mettere i file.

Esegui dalla radice del progetto:
    python crea_struttura_cartelle.py
"""

import os

CARTELLE = [
    "asset/terreni/tileset_base",
    "asset/terreni/tileset_advanced",
    "asset/terreni/tileset_ice",
    "asset/terreni/tileset_fire",
    "asset/terreni/tileset_dungeon",
]

README_CONTENUTO = """ISTRUZIONI PER IL GRAFICO
==========================

Ogni cartella contiene UN SOLO FILE chiamato  tileset.png

STRUTTURA RICHIESTA DEL FILE tileset.png:
  - Dimensioni totali: 384 × 512 pixel
  - Tile: 128 × 128 pixel ciascuno
  - Griglia: 3 colonne × 4 righe = 12 tile

POSIZIONE DI OGNI TERRENO (UGUALE PER TUTTI I TILESET):

    Colonna →    0           1           2
    Riga ↓
    0          pianura     deserto     terra_scura
    1          fango       terra       vegetazione
    2          montagna    minerali    foresta
    3          vuoto       lava        acqua

REGOLE TECNICHE:
  - Sfondo trasparente = MAGENTA puro (R:255, G:0, B:255)
  - Formato: PNG (non JPG, non BMP)
  - Nome file OBBLIGATORIO: tileset.png (tutto minuscolo)
  - Non aggiungere bordi o outline agli esagoni
    (i bordi li disegna il programma)

DESCRIZIONE DEI TILESET:
  tileset_base/      → Terreni classici fantasy (già presenti)
  tileset_advanced/  → Alta risoluzione, più dettagli
  tileset_ice/       → Paesaggi innevati e ghiacciati
  tileset_fire/      → Terre vulcaniche e infernali
  tileset_dungeon/   → Pietre e mattoni per dungeon
"""

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    
    for cartella in CARTELLE:
        percorso = os.path.join(root, cartella)
        os.makedirs(percorso, exist_ok=True)
        print(f"✓ Creata: {cartella}/")

        # Crea un file placeholder per indicare al grafico dove lavorare
        placeholder = os.path.join(percorso, "QUI_METTI_tileset.png.txt")
        if not os.path.exists(placeholder):
            with open(placeholder, "w", encoding="utf-8") as f:
                f.write(f"Metti in questa cartella il file: tileset.png\n\n")
                f.write(README_CONTENUTO)
            print(f"  → Creato placeholder con istruzioni")

    # README generale nella cartella terreni
    readme_path = os.path.join(root, "asset", "terreni", "README_GRAFICO.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(README_CONTENUTO)
    print(f"\n✓ Creato README_GRAFICO.txt in asset/terreni/")
    print("\nStruttura creata. Ora consegna le cartelle al grafico.")
    print("Quando ha finito, ogni cartella deve contenere: tileset.png")

if __name__ == "__main__":
    main()
