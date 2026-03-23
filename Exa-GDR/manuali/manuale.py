"""
manuali/manuale.py — Struttura base dei manuali di gioco
"""

# Manuale base incluso nel software
MANUALE_BASE = {
    "id":      "manuale_base",
    "nome":    "Manuale Base GDR",
    "version": "1.0",

    "statistiche": [
        "forza", "destrezza", "costituzione",
        "intelligenza", "saggezza", "carisma"
    ],

    "formula_modificatore": "(statistica - 10) // 2",

    "combattimento": {
        "iniziativa":    "d20 + modificatore_destrezza",
        "attacco":       "d20 + modificatore_forza >= CA bersaglio",
        "danno_base":    "d6 + modificatore_forza",
        "morte":         "PF <= 0",
    },

    "livelli_slot_incantesimi": {
        1:  {1: 2},
        2:  {1: 3},
        3:  {1: 4, 2: 2},
        4:  {1: 4, 2: 3},
        5:  {1: 4, 2: 3, 3: 2},
        6:  {1: 4, 2: 3, 3: 3},
        7:  {1: 4, 2: 3, 3: 3, 4: 1},
        8:  {1: 4, 2: 3, 3: 3, 4: 2},
        9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
        10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    },

    "bonus_competenza_per_livello": {
        **{lv: 2 for lv in range(1,  5)},
        **{lv: 3 for lv in range(5,  9)},
        **{lv: 4 for lv in range(9, 13)},
        **{lv: 5 for lv in range(13, 17)},
        **{lv: 6 for lv in range(17, 21)},
    },
}


def slot_per_livello(livello_personaggio: int) -> dict:
    return MANUALE_BASE["livelli_slot_incantesimi"].get(livello_personaggio, {})


def bonus_competenza(livello_personaggio: int) -> int:
    return MANUALE_BASE["bonus_competenza_per_livello"].get(livello_personaggio, 2)
